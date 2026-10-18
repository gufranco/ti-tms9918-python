from __future__ import annotations

import hashlib
import importlib.machinery
import json
import platform
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, override

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Callable, Sequence


def installed_version(where: Path | None = None) -> str:
    found = re.search(
        r"""VERSION\s*[:=][^"']*["']([^"']+)["']""",
        (where or Path(__file__).resolve().parent / "version.py").read_text(),
    )
    return found.group(1) if found else "unknown"


VERSION = installed_version()

ROOT = Path(__file__).resolve().parent.parent


def reachable(root: Path = ROOT, path: list[str] | None = None) -> bool:
    where = sys.path if path is None else path
    if str(root) in where:
        return False
    where.insert(0, str(root))
    return True


reachable()

CORPUS = ROOT / "conformance" / "corpus.json"

DOCUMENTS = ROOT / "conformance" / "documents.json"

HELD_DOCUMENTS = ROOT / "docs"

HARNESS_MODULE = "z80"

PROCESSOR = ROOT / "zilog-z80-python"


def look_in(where: Path) -> Callable[[str], Any]:
    return lambda name: importlib.machinery.PathFinder.find_spec(name, [str(where)])


IN_SUBMODULE = look_in(PROCESSOR)


OLDEST_PYTHON = (3, 12)

LINE = 342

MASTER_HZ = 10_738_635

PRINTED_BOUND_MICROSECONDS = 8.0

CHECKS = (
    "python",
    "package",
    "building",
    "framing",
    "accessing",
    "rendering",
    "manual",
    "corpus",
    "harness",
    "library",
)


class Finding:
    __slots__ = ("advice", "detail", "name", "ok")

    def __init__(self, name: str, ok: bool, detail: str, advice: str | None = None) -> None:
        self.name = name
        self.ok = ok
        self.detail = detail
        self.advice = advice

    @property
    def line(self) -> str:
        return f"  {'ok  ' if self.ok else '   !'}  {self.name}: {self.detail}"

    @property
    def report(self) -> str:
        if self.ok or not self.advice:
            return self.line
        return f"{self.line}\n         {self.advice}"

    @override
    def __repr__(self) -> str:
        return f"<Finding {self.name} {'ok' if self.ok else 'not ok'}>"


def _threw(name: str, error: BaseException, advice: str | None = None) -> Finding:
    return Finding(name, False, f"{type(error).__name__}: {error}", advice)


def check_python() -> Finding:
    running = sys.version_info[:2]
    return Finding(
        "python",
        running >= OLDEST_PYTHON,
        f"{platform.python_version()}",
        f"this package needs {OLDEST_PYTHON[0]}.{OLDEST_PYTHON[1]} or newer",
    )


def _load() -> Any:
    import tms9918

    return tms9918


def check_package(load: Callable[[], Any] = _load) -> Finding:
    try:
        loaded = load()
    except Exception as error:
        return _threw("package", error, "the package did not import from this directory")
    return Finding("package", True, f"tms9918 {loaded.__version__} imported from {ROOT}")


def _ready(model: str) -> Any:
    import tms9918
    from tms9918.memory import Vram

    part = tms9918.Chip(model, Vram(fill=0))
    part.reset()
    part.read_status()
    return part


def _program(part: Any, values: dict[int, int]) -> None:
    for register, value in values.items():
        part.write_control(value)
        part.write_control(0x80 | register)


def check_building(load: Callable[[], Any] = _load) -> Finding:
    try:
        names = sorted(load().MODELS)
        built = [_ready(name).model for name in names]
    except Exception as error:
        return _threw("building", error)
    return Finding(
        "building",
        built == names and bool(names),
        f"built {', '.join(built)}",
        "a model in the catalogue did not build as itself",
    )


def _frame_period(part: Any, limit: int) -> int:
    part.read_status()
    for count in range(1, limit + 1):
        part.clock()
        if part.status & 0x80:
            return count
    return limit + 1


def check_framing(ready: Callable[[str], Any] = _ready) -> Finding:
    try:
        part = ready("tms9929a")
        expected = LINE * part.part.lines
        _frame_period(part, expected * 2)
        period = _frame_period(part, expected * 2)
    except Exception as error:
        return _threw("framing", error)
    return Finding(
        "framing",
        period == expected,
        f"a TMS9929A frame took {period} dots, {expected} expected",
        "the frame flag did not rise once every 342 dots by 313 lines",
    )


def check_accessing(ready: Callable[[str], Any] = _ready) -> Finding:
    try:
        part = ready("tms9918a")
        _program(part, {1: 0x40})
        part.write_control(0x00)
        part.write_control(0x40)
        part.write_data(0xA5)
        waited = 0
        while part.memory.read8(0) != 0xA5 and waited < MASTER_HZ // 1000:
            part.tick()
            waited += 1
    except Exception as error:
        return _threw("accessing", error)
    microseconds = waited * 1e6 / MASTER_HZ
    return Finding(
        "accessing",
        microseconds <= PRINTED_BOUND_MICROSECONDS,
        f"a write landed after {microseconds:.2f} microseconds",
        "a write waited past the 8 microseconds the manual allows",
    )


def _shown(part: Any, count: int) -> list[int]:
    seen: list[int] = []
    for _ in range(count):
        part.clock()
        seen.append(part.colour)
    return seen


def check_rendering(ready: Callable[[str], Any] = _ready) -> Finding:
    try:
        part = ready("tms9928a")
        _program(part, {1: 0x40, 2: 0x06, 3: 0x80, 4: 0x00, 7: 0x04})
        part.memory.write8(0x1800, 0x01)
        part.memory.write8(0x0008, 0x80)
        part.memory.write8(0x2000, 0xF0)
        while (part.line, part.dot) != (0, 0):
            part.clock()
        shown = _shown(part, 2)
    except Exception as error:
        return _threw("rendering", error)
    return Finding(
        "rendering",
        shown == [15, 4],
        f"the first two dots of a Graphics I screen showed colours {shown}",
        "a cell set to white over a dark blue backdrop did not reach the screen as such",
    )


def check_manual(manifest: Path = DOCUMENTS, held: Path = HELD_DOCUMENTS) -> Finding:
    try:
        entry = json.loads(manifest.read_text())["documents"][0]
        where = held / str(entry["file"])
        if not where.is_file():
            return Finding(
                "manual",
                True,
                f"not here: {where}; the quote check will report checking none",
                None,
            )
        agrees = hashlib.sha256(where.read_bytes()).hexdigest() == entry["sha256"]
    except Exception as error:
        return _threw("manual", error)
    return Finding(
        "manual",
        agrees,
        f"{where.name} is the pinned scan" if agrees else f"{where.name} is a different file",
        "fetch it again with python3 -m conformance.documents",
    )


def check_corpus(path: Path | str = CORPUS) -> Finding:
    where = Path(path)
    if not where.is_file():
        return Finding("corpus", False, f"not here: {where}", "run the census to build one")
    try:
        held = json.loads(where.read_text())
        examined = int(held["images"])
    except Exception as error:
        return _threw("corpus", error, f"{where} did not parse")
    return Finding(
        "corpus",
        examined > 0,
        f"{examined} images behind it",
        "a census that examined no image writes an empty corpus, so check what it walked",
    )


def check_harness(find: Callable[[str], Any] = IN_SUBMODULE) -> Finding:
    try:
        found = find(HARNESS_MODULE)
    except Exception as error:
        return _threw("harness", error)
    if found is None:
        return Finding(
            "harness",
            True,
            "zilog-z80-python is not checked out; only the census needs it, so the "
            "package and the suite run without it",
        )
    return Finding("harness", True, f"zilog-z80-python found at {found.origin}")


def check_library() -> Finding:
    return Finding(
        "library",
        True,
        "the census takes the library to walk as an argument, so there is nothing to be set wrongly",
    )


def examine(corpus: Path | str = CORPUS) -> list[Finding]:
    return [
        check_python(),
        check_package(),
        check_building(),
        check_framing(),
        check_accessing(),
        check_rendering(),
        check_manual(),
        check_corpus(corpus),
        check_harness(),
        check_library(),
    ]


def report(found: Sequence[Finding]) -> list[str]:
    from tms9918 import environment

    unwell = [one for one in found if not one.ok]
    lines = [
        f"tms9918 {VERSION} on {platform.python_version()}, {platform.system()}",
        "",
    ]
    lines.append("  the machine")
    lines.extend(environment.lines(ROOT))
    lines.append("")
    lines.append("  this package")
    lines.extend(one.report for one in found)
    lines.append("")
    if unwell:
        lines.append(f"  {len(unwell)} of {len(found)} checks did not pass")
    else:
        lines.append(f"  {len(found)} checks, nothing to report")
    return lines


def main(
    argv: Sequence[str] = (),
    examine: Callable[..., list[Finding]] = examine,
    say: Callable[[str], None] = print,
) -> int:
    found = examine()
    for line in report(found):
        say(line)
    return 1 if any(not one.ok for one in found) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

import hashlib
import json
import os
import sys
import zipfile
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Any

from conformance import harness

RECORD = Path(__file__).resolve().parent / "testroms.json"

PLACES = "TEST_CARTRIDGES"

KEPT = Path(__file__).resolve().parent.parent / "external"

COLUMNS = 32

ROWS = 24

NAME_TABLE_STEP = 0x400

NAME_TABLE_BITS = 0x0F

NOTHING_TO_RUN = 2

USAGE_ERROR = 3

INDENT = 2

USAGE = "usage: python3 -m conformance.testroms [--write] [image, folder or zip ...]"


def record(where: Path | str | None = None) -> dict[str, Any]:
    held = json.loads(Path(where or RECORD).read_text())
    assert isinstance(held, dict), "the record does not hold an object"
    return held


def entry(name: str, where: Path | str | None = None) -> dict[str, Any]:
    found = [one for one in record(where)["cartridges"] if one["id"] == name]
    assert found, f"{name} is not in the record"
    return dict(found[0])


def candidates(place: Path) -> Iterator[bytes]:
    if place.is_dir():
        for path in sorted(place.rglob("*")):
            yield from candidates(path)
    elif zipfile.is_zipfile(place):
        with zipfile.ZipFile(place) as archive:
            for member in archive.namelist():
                yield archive.read(member)
    elif place.is_file():
        yield place.read_bytes()


def images(places: Sequence[Path], wanted: set[str]) -> dict[str, bytes]:
    found: dict[str, bytes] = {}
    for place in places:
        for data in candidates(place):
            digest = hashlib.sha256(data).hexdigest()
            if digest in wanted:
                found[digest] = data
    return found


def screen(board: harness.Board) -> list[str]:
    vdp = board.vdp
    base = (vdp.registers[2] & NAME_TABLE_BITS) * NAME_TABLE_STEP
    return [
        "".join(chr(vdp.memory.read8(base + row * COLUMNS + column)) for column in range(COLUMNS))
        for row in range(ROWS)
    ]


def reported(row: str) -> bool:
    text = row.strip()
    printable = all(" " <= character <= "~" for character in row)
    return printable and any(character.isalpha() for character in text) and len(set(text)) > 1


def ran(image: bytes, frames: int, every: int) -> dict[str, Any]:
    board = harness.Board(image)
    seen: list[str] = []
    for _ in range(frames // every):
        board.run_frames(every)
        shown = [row.strip() for row in screen(board) if reported(row)]
        seen = list(dict.fromkeys([*seen, *shown]))
    return {"verdict": seen, "lost": board.seen.lost}


def expected(image: bytes, where: dict[str, list[int]]) -> dict[str, list[int]]:
    return {name: [image[at] for at in places] for name, places in where.items()}


def measured(image: bytes, one: dict[str, Any]) -> dict[str, Any]:
    found = ran(image, one["frames"], one["every"])
    return {**found, "expected": expected(image, one.get("expectedAt", {}))}


def options(argv: Sequence[str]) -> tuple[bool, list[Path]] | None:
    write = "--write" in argv
    rest = [one for one in argv if one != "--write"]
    if any(one.startswith("--") for one in rest):
        return None
    return write, [Path(one) for one in rest]


def places_from(given: list[Path], kept: Path) -> list[Path]:
    if given:
        return given
    named = os.environ.get(PLACES, "")
    return [Path(one) for one in named.split(os.pathsep) if one] or [kept]


def judged(one: dict[str, Any], found: dict[str, Any]) -> bool:
    same = all(found[key] == one.get(key) for key in found)
    print(f"{'ran' if same else 'DIFFERS'} {one['id']}: {len(found['verdict'])} lines")
    for line in found["verdict"]:
        print(f"  {line}")
    print(f"  lost accesses: {found['lost']}, expected from the image: {found['expected']}")
    return same


def main(argv: Sequence[str], where: Path | str | None = None, kept: Path = KEPT) -> int:
    parsed = options(argv)
    if parsed is None:
        print(USAGE)
        return USAGE_ERROR
    write, given = parsed
    held = record(where)
    wanted = [one for one in held["cartridges"] if one["outcome"] == "run"]
    found = images(places_from(given, kept), {one["sha256"] for one in wanted})
    if not found:
        print(f"SKIPPED none of the {len(wanted)} pinned images is on this machine")
        return NOTHING_TO_RUN
    good = True
    for one in wanted:
        if one["sha256"] not in found:
            print(f"SKIPPED {one['id']}: not on this machine")
            continue
        result = measured(found[one["sha256"]], one)
        good = judged(one, result) and good
        one.update(result)
    if write:
        Path(where or RECORD).write_text(json.dumps(held, indent=INDENT) + "\n")
    return 0 if good else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

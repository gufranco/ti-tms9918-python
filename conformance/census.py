import collections
import hashlib
import json
import sys
import zipfile
from collections.abc import Iterator, Mapping
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

from conformance import harness

SUFFIXES = (".sg", ".sc", ".sf", ".sms")

GATED_SETS = ("Japan", "Korea", "Taiwan", "Other Regions")

GATED_SUFFIX = ".sg"

NOT_GAMES = ("[BIOS]", "(Beta", "(Proto")

FRAMES = 600

JOBS = 10

DISPLAYS = "every retail image turns the display on within the frame bound"

LOST = "accesses asked for before the last one was served"

RAISES_NOTHING = "the model raises on no image"

PROPERTIES = (RAISES_NOTHING, DISPLAYS)

CORPUS = Path(__file__).resolve().parent / "corpus.json"

CORPUS_INDENT = 2

USAGE = "usage: python3 -m conformance.census <path> [path ...] [--frames N] [--jobs N]"

Image = tuple[str, str, bytes]


def _members(where: Path) -> Iterator[Image]:
    with zipfile.ZipFile(where) as bundle:
        for entry in bundle.infolist():
            if not entry.is_dir() and Path(entry.filename).suffix.lower() in SUFFIXES:
                yield where.name, Path(entry.filename).name, bundle.read(entry)


def images_in(where: Path) -> Iterator[Image]:
    if where.is_dir():
        for path in sorted(where.rglob("*")):
            if path.is_file() and path.suffix.lower() == ".zip":
                yield from _members(path)
            elif path.is_file() and path.suffix.lower() in SUFFIXES:
                yield where.name, path.name, path.read_bytes()
        return
    if where.suffix.lower() == ".zip":
        yield from _members(where)
        return
    if where.suffix.lower() in SUFFIXES:
        yield where.parent.name, where.name, where.read_bytes()


def gated(collection: str, name: str) -> bool:
    retail = any(one in collection for one in GATED_SETS)
    shipped = not any(tag in name for tag in NOT_GAMES)
    return retail and shipped and name.lower().endswith(GATED_SUFFIX)


def _seen(board: harness.Board, raised: str | None) -> dict[str, Any]:
    seen = board.seen
    return {
        "modes": sorted(seen.modes),
        "registers": sorted({(register, value) for register, value in seen.registers}),
        "sprites": sorted(seen.sprites),
        "lost": seen.lost,
        "raised": raised,
    }


def examine(job: tuple[bytes, int], build: type[harness.Board] = harness.Board) -> dict[str, Any]:
    rom, frames = job
    board = build(rom)
    try:
        board.run_frames(frames)
    except Exception as error:
        return _seen(board, f"{type(error).__name__}: {error} at frame {board.frames}")
    return _seen(board, None)


Distinct = tuple[bool, bytes, str]


def _distinct(paths: list[Path]) -> tuple[int, list[Distinct]]:
    listings = 0
    seen: dict[str, Distinct] = {}
    for where in paths:
        for collection, name, rom in images_in(where):
            listings += 1
            digest = hashlib.sha256(rom).hexdigest()
            held = seen.get(digest)
            seen[digest] = (bool(held and held[0]) or gated(collection, name), rom, name)
    return listings, [seen[digest] for digest in sorted(seen)]


def _results(images: list[Distinct], frames: int, jobs: int) -> list[dict[str, Any]]:
    work = [(rom, frames) for _, rom, _ in images]
    if jobs <= 1:
        return [examine(one) for one in work]
    with ProcessPoolExecutor(max_workers=jobs) as pool:
        return list(pool.map(examine, work))


def _tally(images: list[Distinct], results: list[dict[str, Any]]) -> dict[str, Any]:
    modes: collections.Counter[str] = collections.Counter()
    sprites: collections.Counter[str] = collections.Counter()
    registers: dict[str, collections.Counter[str]] = collections.defaultdict(collections.Counter)
    broken = dict.fromkeys(PROPERTIES, 0)
    lost = {"retail": 0, "other": 0}
    silent = 0
    for (retail, _, _), found in zip(images, results, strict=True):
        modes.update(found["modes"])
        sprites.update(found["sprites"])
        for register, value in found["registers"]:
            registers[str(register)][f"0x{value:02X}"] += 1
        lost["retail" if retail else "other"] += found["lost"]
        silent += not found["modes"]
        broken[DISPLAYS] += retail and not found["modes"]
        broken[RAISES_NOTHING] += found["raised"] is not None
    return {
        "properties": broken,
        "modes": dict(sorted(modes.items())),
        "sprites": dict(sorted(sprites.items())),
        "registers": {key: dict(sorted(held.items())) for key, held in sorted(registers.items())},
        "lost": lost,
        "silent": silent,
    }


def _culprits(images: list[Distinct], results: list[dict[str, Any]]) -> dict[str, list[str]]:
    named: dict[str, list[str]] = {name: [] for name in (*PROPERTIES, LOST)}
    for (retail, _, image), found in zip(images, results, strict=True):
        if found["raised"] is not None:
            named[RAISES_NOTHING].append(f"{image}: {found['raised']}")
        if retail and not found["modes"]:
            named[DISPLAYS].append(image)
        if found["lost"]:
            named[LOST].append(f"{image}: {found['lost']}")
    return named


def take(paths: list[Path], frames: int = FRAMES, jobs: int = JOBS) -> Mapping[str, Any]:
    listings, images = _distinct(paths)
    results = _results(images, frames, jobs)
    return {
        "listings": listings,
        "images": len(images),
        "gated": sum(1 for retail, _, _ in images if retail),
        "frames": frames,
        **_tally(images, results),
        "culprits": _culprits(images, results),
    }


def _options(argv: list[str]) -> tuple[list[Path], int, int] | None:
    paths: list[Path] = []
    frames, jobs = FRAMES, JOBS
    rest = list(argv)
    while rest:
        item = rest.pop(0)
        if item in ("--frames", "--jobs"):
            if not rest:
                return None
            value = int(rest.pop(0))
            frames, jobs = (value, jobs) if item == "--frames" else (frames, value)
        else:
            paths.append(Path(item))
    return (paths, frames, jobs) if paths else None


def report(taken: Mapping[str, Any]) -> list[str]:
    culprits = taken["culprits"]
    lines = [
        f"{taken['listings']} listings, {taken['images']} distinct images, "
        f"{taken['gated']} retail, {taken['frames']} frames each"
    ]
    for name, count in taken["properties"].items():
        lines.append(f"  {'ok  ' if not count else '   !'}  {name}: {count} broken")
        lines.extend(f"         {one}" for one in culprits[name])
    lines.append(f"  observed  {LOST}: {len(culprits[LOST])} images")
    lines.extend(f"         {one}" for one in culprits[LOST])
    return lines


def main(argv: list[str], into: Path = CORPUS) -> int:
    chosen = _options(argv)
    if chosen is None:
        print(USAGE)
        return 2
    paths, frames, jobs = chosen
    for one in paths:
        if not one.exists():
            print(f"absent: {one}")
    taken = take([one for one in paths if one.exists()], frames, jobs)
    for line in report(taken):
        print(line)
    if taken["images"]:
        kept = {key: value for key, value in taken.items() if key != "culprits"}
        into.write_text(json.dumps(kept, indent=CORPUS_INDENT) + "\n")
    failed = any(taken["properties"].values()) or not taken["images"]
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

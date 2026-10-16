import json
import sys
from pathlib import Path
from typing import Any

CORPUS = Path(__file__).resolve().parent / "corpus.json"


def broken(held: dict[str, Any]) -> list[str]:
    return [name for name, count in held["properties"].items() if count]


def inconsistent(held: dict[str, Any]) -> list[str]:
    images = held["images"]
    problems = [
        f"mode {mode} on {count} of {images} images"
        for mode, count in held["modes"].items()
        if count > images
    ]
    problems += [
        f"register {register} value {value} on {count} of {images} images"
        for register, values in held["registers"].items()
        for value, count in values.items()
        if count > images
    ]
    if held["gated"] > images:
        problems.append(f"{held['gated']} retail of {images} images")
    if held["silent"] > images:
        problems.append(f"{held['silent']} silent of {images} images")
    return problems


def main(where: Path = CORPUS) -> int:
    held = json.loads(where.read_text())
    print(f"{held['images']} images, {held['gated']} retail, {held['frames']} frames each")
    for name, count in held["properties"].items():
        print(f"  {'ok  ' if not count else '   !'}  {name}: {count} broken")
    problems = inconsistent(held)
    for problem in problems:
        print(f"     !  {problem}")
    return 1 if broken(held) or problems else 0


if __name__ == "__main__":
    sys.exit(main())

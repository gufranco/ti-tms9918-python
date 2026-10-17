import json
from pathlib import Path
from typing import Any

import tms9918
from tms9918 import core
from tms9918.memory import Vram

RECORD = Path(__file__).resolve().parent / "hardware.json"

HELD: dict[str, Any] = json.loads(RECORD.read_text())

FACTS: dict[str, Any] = HELD["facts"]

UNSTATED: dict[str, Any] = HELD["notStated"]

MASTER_HZ = 10_738_635

SEED = 7


def value(name: str) -> Any:
    return FACTS[name]["value"]


def quotes(name: str) -> list[str]:
    held: list[str] = FACTS[name]["quotes"]
    return held


def chip(model: str = "tms9918a") -> core.Chip:
    built = tms9918.Chip(model, Vram(fill=0), seed=SEED)
    built.reset()
    built.read_status()
    return built


def program(part: core.Chip, values: dict[int, int]) -> core.Chip:
    for register, held in values.items():
        part.write_control(held)
        part.write_control(0x80 | register)
    return part


def dots_until(part: core.Chip, line: int, dot: int) -> core.Chip:
    while (part.line, part.dot) != (line, dot):
        part.clock()
    return part


def colour_at(part: core.Chip, line: int, dot: int) -> int | None:
    dots_until(part, line, dot).clock()
    return part.colour

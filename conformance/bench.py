import copy
import itertools
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import tms9918

RECORD = Path(__file__).resolve().parent / "hardware.json"

HELD: dict[str, Any] = json.loads(RECORD.read_text())

FACTS: dict[str, Any] = HELD["facts"]

UNSTATED: dict[str, Any] = HELD["notStated"]

MASTER_HZ = 10_738_635

SEED = 7

WATCHED = 0x3000

TICKS_PER_LINE = 684

WAIT_LIMIT = 1 << 10

SAMPLED_DOT = 100


def value(name: str) -> Any:
    return FACTS[name]["value"]


def quotes(name: str) -> list[str]:
    held: list[str] = FACTS[name]["quotes"]
    return held


def chip(model: str = "tms9918a", memory: Any = None) -> Any:
    built: Any = tms9918.Chip(model, tms9918.Vram(fill=0) if memory is None else memory, seed=SEED)
    built.reset()
    built.read_status()
    return built


def program(part: Any, values: dict[int, int]) -> Any:
    for register, held in values.items():
        part.write_control(held)
        part.write_control(0x80 | register)
    return part


def dots_until(part: Any, line: int, dot: int) -> Any:
    while (part.line, part.dot) != (line, dot):
        part.clock()
    return part


def colour_at(part: Any, line: int, dot: int) -> int | None:
    dots_until(part, line, dot).clock()
    held: int | None = part.colour
    return held


class Watch:
    __slots__ = ("hits", "reads", "store", "written")

    def __init__(self) -> None:
        self.store = tms9918.Vram(fill=0)
        self.hits = 0
        self.reads = 0
        self.written: list[int] = []

    def read8(self, address: int) -> int:
        self.hits += address == WATCHED
        self.reads += 1
        return self.store.read8(address)

    def write8(self, address: int, held: int) -> None:
        self.hits += address == WATCHED
        self.written = [*self.written, address]
        self.store.write8(address, held)


def watched(registers: dict[int, int], model: str = "tms9918a") -> Any:
    tables = dict.fromkeys(range(8), 0)
    part = program(chip(model, Watch()), {**tables, **registers})
    part.write_control(WATCHED & 0xFF)
    part.write_control(0x40 | WATCHED >> 8)
    return part


def ticks_to_serve(part: Any) -> int:
    for waited in range(WAIT_LIMIT):
        part.tick()
        if part.memory.hits:
            return waited
    return WAIT_LIMIT


def read_setup(part: Any) -> None:
    part.write_control(WATCHED & 0xFF)
    part.write_control(WATCHED >> 8)


def data_write(part: Any) -> None:
    part.write_data(0x5A)


def waits(registers: dict[int, int], line: int, ask: Callable[[Any], None]) -> list[int]:
    part = dots_until(watched(registers), line, 0)
    found: list[int] = []
    for _ in range(TICKS_PER_LINE):
        trial = copy.deepcopy(part)
        ask(trial)
        found = [*found, ticks_to_serve(trial)]
        part.tick()
    return found


def windows(registers: dict[int, int], line: int) -> list[int]:
    found = waits(registers, line, data_write)
    return sorted({(asked + waited) % TICKS_PER_LINE for asked, waited in enumerate(found)})


def runs(regions: list[str]) -> list[int]:
    start = regions.index("active")
    turned = regions[start:] + regions[:start]
    return [len(list(run)) for _, run in itertools.groupby(turned)]


def row(registers: dict[int, int], line: int) -> list[str]:
    part = dots_until(program(chip(), registers), line, 0)
    found: list[str] = []
    for _ in range(TICKS_PER_LINE // 2):
        part.clock()
        found = [*found, part.region]
    return found


def column(model: str) -> list[str]:
    part = chip(model)
    found: list[str] = []
    for line in range(part.part.lines):
        dots_until(part, line, SAMPLED_DOT).clock()
        found = [*found, part.region]
    return found

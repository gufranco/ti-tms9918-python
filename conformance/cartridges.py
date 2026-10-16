import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

BOARDS = Path(__file__).resolve().parent / "boards.json"

PLAIN = "plain"

CONSOLE_RAM = 0x0400

CONSOLE_MASK = CONSOLE_RAM - 1

RAM_START = 0xC000

ADDRESS_END = 0x10000


@dataclass(frozen=True, slots=True)
class Window:
    start: int
    end: int
    mask: int
    base: int


CONSOLE = Window(RAM_START, ADDRESS_END, CONSOLE_MASK, 0)


@dataclass(frozen=True, slots=True)
class Layout:
    size: int
    windows: tuple[Window, ...]

    def locate(self, address: int) -> int | None:
        for window in self.windows:
            if window.start <= address < window.end:
                return window.base + (address & window.mask)
        return None


LAYOUTS: dict[str, Layout] = {
    PLAIN: Layout(CONSOLE_RAM, (CONSOLE,)),
    "othello": Layout(0x0C00, (Window(0x8000, 0xA000, 0x07FF, CONSOLE_RAM), CONSOLE)),
    "castle": Layout(0x2400, (Window(0x8000, 0xA000, 0x1FFF, CONSOLE_RAM), CONSOLE)),
    "level3": Layout(0x4400, (Window(0x8000, RAM_START, 0x3FFF, CONSOLE_RAM), CONSOLE)),
    "dahjee_typea": Layout(
        0x2400,
        (
            Window(0x2000, 0x4000, 0x1FFF, 0),
            Window(RAM_START, ADDRESS_END, CONSOLE_MASK, 0x2000),
        ),
    ),
    "dahjee_typeb": Layout(0x2000, (Window(RAM_START, ADDRESS_END, 0x1FFF, 0),)),
}


def layout_for(rom: bytes, where: Path = BOARDS) -> Layout:
    digest = hashlib.sha1(rom, usedforsecurity=False).hexdigest()
    listed = {entry["sha1"]: entry["board"] for entry in json.loads(where.read_text())["boards"]}
    return LAYOUTS[listed.get(digest, PLAIN)]

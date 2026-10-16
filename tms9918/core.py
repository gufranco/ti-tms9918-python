import random
from typing import Any

from tms9918 import geometry, patterns, slots, sprites
from tms9918.memory import ADDRESS_MASK, UNSET_SEED

CPUCLK = 1

GROMCLK = 2

CPUCLK_DIVIDER = 3

GROMCLK_DIVIDER = 24

EXTERNAL = 16

BLACK = 1

READ = "read"

WRITE = "write"

FRAME = 0x80

FIFTH = 0x40

COINCIDENCE = 0x20

FIFTH_NUMBER = 0x1F

EXTERNAL_VIDEO = 0x01

BLANK = 0x40

INTERRUPT_ENABLE = 0x20

MAGNIFY = 0x01

REGISTER_WRITE = 0x80

WRITE_SETUP = 0x40

EVALUATE_AT = 256

REGISTER_COUNT = 8

UNSHOWN: tuple[int, ...] = ()


class Chip:
    __slots__ = (
        "address",
        "asked",
        "buffer",
        "cell",
        "colour",
        "column",
        "cycles",
        "divider",
        "dot",
        "drawn",
        "half",
        "kinds",
        "latch",
        "line",
        "memory",
        "mode",
        "model",
        "part",
        "pending",
        "region",
        "registers",
        "status",
    )

    def __init__(self, part: Any, memory: Any, seed: int = UNSET_SEED) -> None:
        scrambled = random.Random(seed)
        self.part = part
        self.model: str = part.name
        self.memory = memory
        self.kinds = geometry.lines_of(part)
        self.registers = bytearray(scrambled.randbytes(REGISTER_COUNT))
        self.status = scrambled.randrange(256)
        self.latch = bool(scrambled.getrandbits(1))
        self.address = scrambled.randrange(ADDRESS_MASK + 1)
        self.buffer = scrambled.randrange(256)
        self.line = scrambled.randrange(part.lines)
        self.dot = scrambled.randrange(geometry.DOTS)
        self.half = scrambled.randrange(2)
        self.divider = scrambled.randrange(GROMCLK_DIVIDER)
        self.pending: tuple[str, int, int] | None = None
        self.asked = 0
        self.cycles = 0
        self.region = geometry.BLANKING
        self.colour: int | None = None
        self.drawn: sprites.Drawn | None = None
        self.column = -1
        self.cell = UNSHOWN
        self.mode = self._decoded()

    def reset(self) -> "Chip":
        self.registers[0] = 0
        self.registers[1] = 0
        self.status &= FIFTH_NUMBER
        self.line = (
            geometry.ACTIVE_LINES
            + self.part.bottom_border
            + geometry.BOTTOM_BLANKING
            + geometry.VERTICAL_SYNC
        )
        self.dot = 0
        self.half = 0
        self.divider = 0
        self.mode = self._decoded()
        return self

    @property
    def interrupt(self) -> bool:
        return bool(self.status & FRAME and self.registers[1] & INTERRUPT_ENABLE)

    def write_control(self, value: int) -> None:
        if not self.latch:
            self.address = (self.address & 0x3F00) | value
            self.latch = True
            return
        self.latch = False
        low = self.address & 0xFF
        self.address = (value & 0x3F) << 8 | low
        if value & REGISTER_WRITE:
            self._load(value & (REGISTER_COUNT - 1), low)
        elif not value & WRITE_SETUP:
            self._ask(READ, 0)

    def write_data(self, value: int) -> None:
        self.latch = False
        self.buffer = value & 0xFF
        self._ask(WRITE, value & 0xFF)

    def read_data(self) -> int:
        self.latch = False
        held = self.buffer
        self._ask(READ, 0)
        return held

    def read_status(self) -> int:
        self.latch = False
        held = self.status
        self.status &= FIFTH_NUMBER
        return held

    def clock(self) -> int:
        return self.tick() | self.tick()

    def run_dots(self, count: int) -> None:
        for _ in range(count):
            self.clock()

    def tick(self) -> int:
        position = self.dot * 2 + self.half
        if not self.half:
            self._show()
        self._serve(position)
        self.cycles += 1
        edges = self._pins()
        self._advance()
        return edges

    def _decoded(self) -> str:
        return patterns.mode_of(self.registers[0], self.registers[1])

    def _load(self, register: int, value: int) -> None:
        self.registers[register] = value
        mode = self._decoded()
        if mode != self.mode:
            self.column = -1
        self.mode = mode

    def _ask(self, kind: str, value: int) -> None:
        self.pending = (kind, self.address, value)
        self.asked = self.cycles
        self.address = (self.address + 1) & ADDRESS_MASK

    def _table(self, position: int) -> frozenset[int]:
        shown = self.registers[1] & BLANK
        grid = slots.grid_line(self.line, position, self.part.lines)
        if not shown or not slots.display_grid(grid):
            return slots.SERVED["off"]
        if patterns.is_text(self.mode):
            return slots.SERVED["text"]
        return slots.SERVED["multicolor" if "multicolor" in self.mode else "graphics"]

    def _serve(self, position: int) -> None:
        if self.pending is None or self.cycles - self.asked < slots.LEAD:
            return
        if position not in self._table(position):
            return
        kind, address, value = self.pending
        self.pending = None
        if kind == WRITE:
            self.memory.write8(address, value)
        else:
            self.buffer = self.memory.read8(address)

    def _pins(self) -> int:
        self.divider = (self.divider + 1) % GROMCLK_DIVIDER
        if not self.part.clock_pins:
            return 0
        cpu = CPUCLK if self.divider % CPUCLK_DIVIDER == 0 else 0
        return cpu | (GROMCLK if self.divider == 0 else 0)

    def _advance(self) -> None:
        self.half ^= 1
        if self.half:
            return
        self.dot += 1
        if self.dot == EVALUATE_AT:
            self._evaluate()
        if self.dot < geometry.DOTS:
            return
        self.dot = 0
        self.line = (self.line + 1) % self.part.lines
        self.column = -1
        if self.line == geometry.ACTIVE_LINES:
            self.status |= FRAME

    def _next_active(self) -> int | None:
        following = (self.line + 1) % self.part.lines
        return following if following < geometry.ACTIVE_LINES else None

    def _evaluate(self) -> None:
        following = self._next_active()
        self.drawn = None
        if following is None or not self.registers[1] & BLANK:
            return
        if patterns.is_text(self.mode):
            return
        found = sprites.evaluate(self.memory.read8, self.registers, following)
        self._report(found)
        self.drawn = sprites.draw(found.shown, bool(self.registers[1] & MAGNIFY))

    def _report(self, found: sprites.Evaluated) -> None:
        if self.status & FIFTH:
            return
        number = found.last if found.fifth is None else found.fifth
        self.status = (self.status & ~FIFTH_NUMBER) | number
        if found.fifth is not None and not self.status & FRAME:
            self.status |= FIFTH

    def _backdrop(self) -> int:
        held = self.registers[7] & 0x0F
        if held:
            return held
        return EXTERNAL if self.registers[0] & EXTERNAL_VIDEO else BLACK

    def _show(self) -> None:
        text = patterns.is_text(self.mode)
        row = geometry.TEXT_ROW if text else geometry.PATTERN_ROW
        self.region = geometry.region(self.kinds[self.line], row[self.dot])
        if self.region == geometry.ACTIVE:
            self.colour = self._active(text)
        elif self.region == geometry.BORDER:
            self.colour = self._backdrop()
        else:
            self.colour = None

    def _active(self, text: bool) -> int:
        if not self.registers[1] & BLANK:
            return self._backdrop()
        start = geometry.TEXT_OFFSET if text else 0
        width = patterns.width(self.mode)
        column, within = divmod(self.dot - start, width)
        if column != self.column:
            self.column = column
            self.cell = patterns.cell(
                self.memory.read8, self.registers, self.mode, self.line, column
            )
        return self._layered(self.cell[within])

    def _layered(self, pattern: int) -> int:
        drawn = self.drawn
        if drawn is not None:
            if drawn.collision == self.dot:
                self.status |= COINCIDENCE
            sprite = drawn.colours[self.dot]
            if sprite is not None:
                return sprite
        return pattern or self._backdrop()

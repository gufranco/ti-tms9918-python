import collections
import sys
from pathlib import Path
from typing import Any

import tms9918
from conformance import cartridges
from tms9918 import core, patterns
from tms9918.memory import scramble

ROOT = Path(__file__).resolve().parent.parent

PROCESSOR = ROOT / "zilog-z80-python"

OPEN_BUS = 0xFF

TICKS_PER_CYCLE = 3

PORT_SELECT = 0xC0

VDP_PORTS = 0x80

SOUND_PORTS = 0x40

CONTROL = 0x01

SEED = 0x5631


def why_not(where: Path = PROCESSOR) -> str | None:
    if (where / "z80" / "__init__.py").is_file():
        return None
    return (
        f"the census drives zilog-z80-python from {where}, which is not checked out."
        " Run git submodule update --init --recursive"
    )


def _processor() -> Any:
    if str(PROCESSOR) not in sys.path:
        sys.path.append(str(PROCESSOR))
    import z80

    return z80


class Seen:
    __slots__ = ("lost", "modes", "registers", "sound", "sprites", "status_reads")

    def __init__(self) -> None:
        self.registers: collections.Counter[tuple[int, int]] = collections.Counter()
        self.modes: collections.Counter[str] = collections.Counter()
        self.sprites: collections.Counter[str] = collections.Counter()
        self.sound = 0
        self.status_reads = 0
        self.lost = 0


class Ports:
    __slots__ = ("board",)

    def __init__(self, board: "Board") -> None:
        self.board = board

    def read(self, address: int) -> int:
        return self.board.read_port(address)

    def write(self, address: int, value: int) -> None:
        self.board.write_port(address, value)


class Board:
    __slots__ = ("cpu", "frames", "last_line", "layout", "ram", "rom", "seen", "vdp")

    def __init__(
        self, rom: bytes, model: str = "tms9918a", layout: cartridges.Layout | None = None
    ) -> None:
        z80 = _processor()
        self.rom = rom
        self.layout = cartridges.layout_for(rom) if layout is None else layout
        self.ram = scramble(self.layout.size, SEED)
        self.vdp: core.Chip = tms9918.Chip(model, seed=SEED)
        self.vdp.reset()
        self.seen = Seen()
        self.frames = 0
        self.last_line = self.vdp.line
        self.cpu = z80.Cpu("z80", self, ports=Ports(self), seed=SEED)
        self.cpu.on_cycle = self.cycle
        self.cpu.reset()

    def read8(self, address: int) -> int:
        placed = self.layout.locate(address)
        if placed is not None:
            return self.ram[placed]
        return self.rom[address] if address < len(self.rom) else OPEN_BUS

    def write8(self, address: int, value: int) -> None:
        placed = self.layout.locate(address)
        if placed is not None:
            self.ram[placed] = value & 0xFF

    def read_port(self, address: int) -> int:
        if address & PORT_SELECT != VDP_PORTS:
            return OPEN_BUS
        if address & CONTROL:
            self.seen.status_reads += 1
            return self.vdp.read_status()
        self._count_loss()
        return self.vdp.read_data()

    def write_port(self, address: int, value: int) -> None:
        selected = address & PORT_SELECT
        if selected == SOUND_PORTS:
            self.seen.sound += 1
        if selected != VDP_PORTS:
            return
        if not address & CONTROL:
            self._count_loss()
            self.vdp.write_data(value)
            return
        self._control(value)

    def _control(self, value: int) -> None:
        second = self.vdp.latch
        low = self.vdp.address & 0xFF
        if second and value & core.REGISTER_WRITE:
            self.seen.registers[(value & 0x7F, low)] += 1
        elif second and not value & core.WRITE_SETUP:
            self._count_loss()
        self.vdp.write_control(value)

    def _count_loss(self) -> None:
        if self.vdp.pending is not None:
            self.seen.lost += 1

    def cycle(self) -> None:
        vdp = self.vdp
        for _ in range(TICKS_PER_CYCLE):
            vdp.tick()
        self.cpu.irq_line = vdp.interrupt
        if vdp.line != self.last_line:
            self.last_line = vdp.line
            if vdp.line == tms9918.geometry.ACTIVE_LINES:
                self._frame()

    def _frame(self) -> None:
        self.frames += 1
        if self.vdp.registers[1] & core.BLANK:
            self.seen.modes[self.vdp.mode] += 1
            self._sprites()

    def _sprites(self) -> None:
        held = self.vdp.registers
        if patterns.is_text(self.vdp.mode):
            return
        size = "16" if held[1] & 0x02 else "8"
        magnified = "x2" if held[1] & 0x01 else "x1"
        self.seen.sprites[f"size {size} {magnified}"] += 1

    def run_frames(self, count: int) -> None:
        target = self.frames + count
        while self.frames < target:
            self.cpu.step()

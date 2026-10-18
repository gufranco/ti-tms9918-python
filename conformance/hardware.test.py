import itertools
import sys
import unittest
from collections.abc import Callable
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import tms9918  # noqa: E402
from conformance.bench import (  # noqa: E402
    MASTER_HZ,
    UNSTATED,
    chip,
    column,
    data_write,
    dots_until,
    program,
    read_setup,
    row,
    runs,
    value,
    waits,
    watched,
    windows,
)

TICKS_PER_MEMORY_CYCLE = 4

FRAME = 0x80

EDGE_TICKS = 240

ACTIVE_LINES = 192

DOTS = 342

PAL_LINES = 313

PICTURE_LINE = 100

BORDER_LINE = 200

TRACED_TICKS = 48

TEXT = 0x10

WRITE_COMMANDS = range(0x80)


def largest_active_gap(found: list[int], active: range) -> int:
    inside = [one for one in found if one in active]
    return max(later - earlier for earlier, later in itertools.pairwise(inside))


def worst_wait(registers: dict[int, int], line: int, ask: Callable[[Any], None]) -> float:
    return max(waits(registers, line, ask)) * 1e6 / MASTER_HZ


def frame_flag_after(clear: Callable[[Any], object]) -> int:
    part = dots_until(chip(), ACTIVE_LINES, 1)
    clear(part)
    held: int = part.status & FRAME
    return held


def traced(part: Any) -> list[tuple[int, int, int]]:
    return [(part.line, part.dot, part.tick()) for _ in range(TRACED_TICKS)]


def edges(model: str) -> tuple[int, int, int]:
    part = chip(model)
    found = [part.tick() for _ in range(EDGE_TICKS)]
    before = part.cycles
    part.clock()
    return (
        part.cycles - before,
        sum(1 for one in found if one & tms9918.CPUCLK),
        sum(1 for one in found if one & tms9918.GROMCLK),
    )


def spacing(found: list[int], pin: int) -> int:
    pulses = [tick for tick, one in enumerate(found) if one & pin]
    return pulses[1] - pulses[0]


def dividers() -> dict[str, Any]:
    part = chip("tms9918a")
    before = part.cycles
    part.clock()
    dot = part.cycles - before
    found = [part.tick() for _ in range(EDGE_TICKS)]
    pinned = [name for name in tms9918.MODELS if any(edges(name)[1:])]
    return {
        "dot": dot,
        "cpuclk": spacing(found, tms9918.CPUCLK),
        "gromclk": spacing(found, tms9918.GROMCLK),
        "pinsOn": pinned,
    }


def lines_per_frame(model: str) -> int:
    part = dots_until(chip(model), ACTIVE_LINES, 0)
    part.read_status()
    dots = 0
    while not part.status & FRAME and dots < DOTS * PAL_LINES:
        part.clock()
        dots += 1
    return (dots + 1) // DOTS


def reads_after(second: int) -> bool:
    part = watched({1: 0x00})
    part.write_control(0x00)
    part.write_control(second)
    part.run_dots(64)
    return bool(part.memory.reads)


def emitted(first: int, second: int) -> list[int]:
    part = watched({1: 0x00})
    part.write_control(first)
    part.write_control(second)
    part.write_data(0x5A)
    part.run_dots(64)
    written: list[int] = part.memory.written
    return written


def prefetched(stored: int) -> int:
    part = chip()
    part.memory.write8(0x1234, stored)
    part.write_control(0x34)
    part.write_control(0x12)
    part.run_dots(64)
    held: int = part.read_data()
    return held


def borders(model: str) -> list[int]:
    found = runs(column(model))
    return [found[-1], found[1]]


class PortTest(unittest.TestCase):
    def test_the_address_register_is_fourteen_bits(self) -> None:
        # Arrange
        printed = value("addressRegister")["bits"]

        # Act
        held = emitted(0xFF, value("writeSetup") | 0x3F)

        # Assert
        self.assertEqual(held, [(1 << printed) - 1])

    def test_the_write_setup_bit_is_the_one_the_manual_names(self) -> None:
        # Arrange
        printed = value("writeSetup")

        # Act
        held = [second for second in WRITE_COMMANDS if not reads_after(second)]

        # Assert
        self.assertEqual(held, [second for second in WRITE_COMMANDS if second & printed])

    def test_reset_clears_exactly_the_registers_the_manual_names(self) -> None:
        # Arrange
        part: Any = tms9918.Chip("tms9918a", tms9918.Vram(fill=0), seed=7)
        part.read_status()
        program(part, {register: register + 1 for register in range(8)})

        # Act
        part.reset()

        # Assert
        cleared = [index for index, held in enumerate(part.registers) if held == 0]
        self.assertEqual(cleared, value("reset")["clearsRegisters"])


class PrintedPortTest(unittest.TestCase):
    def test_the_address_autoincrements_and_wraps_at_the_printed_width(self) -> None:
        # Arrange
        printed = value("addressRegister")
        top = (1 << printed["bits"]) - 1
        part = chip()
        part.write_control(top & 0xFF)
        part.write_control(value("writeSetup") | top >> 8)

        # Act
        for byte in (0x11, 0x22, 0x33):
            part.write_data(byte)
            part.run_dots(64)

        # Assert
        self.assertEqual(
            (part.memory.read8(top), part.memory.read8(0), part.memory.read8(1)),
            (0x11, 0x22, 0x33),
            printed["autoincrements"],
        )

    def test_only_a_setup_without_the_printed_write_bits_asks_for_a_read(self) -> None:
        # Arrange
        printed = value("writeSetup")
        seconds = (0x00, printed)

        # Act
        asked = {second: reads_after(second) for second in seconds}

        # Assert
        self.assertEqual(asked, {0x00: True, printed: False})

    def test_a_read_setup_leaves_the_named_byte_ready_for_the_first_read(self) -> None:
        # Arrange
        stored = (0x5A, 0xA5)

        # Act
        read = tuple(prefetched(one) for one in stored)

        # Assert
        self.assertEqual(read == stored, value("readSetupPrefetch"))

    def test_reading_the_status_clears_the_interrupt(self) -> None:
        # Arrange
        part = dots_until(program(chip(), {1: 0x20}), ACTIVE_LINES, 1)
        before = part.interrupt

        # Act
        part.read_status()

        # Assert
        self.assertEqual((before, part.interrupt), (True, False), value("interruptCleared"))

    def test_reset_sets_the_counters_to_one_known_state_whatever_they_held(self) -> None:
        # Arrange
        parts = [tms9918.Chip("tms9918a", tms9918.Vram(fill=0), seed=seed) for seed in (1, 2)]

        # Act
        held = [traced(part.reset()) for part in parts]

        # Assert
        self.assertEqual(held[0], held[1], value("reset")["setsCounters"])

    def test_the_frame_flag_rises_as_the_last_active_line_ends(self) -> None:
        # Arrange
        part = dots_until(chip(), ACTIVE_LINES - 1, DOTS - 1)
        before = part.status & FRAME

        # Act
        part.clock()

        # Assert
        self.assertEqual((before, part.status & FRAME), (0, FRAME), value("frameFlag"))

    def test_a_status_read_and_a_reset_each_clear_the_frame_flag(self) -> None:
        # Arrange
        ways: dict[str, Callable[[Any], object]] = {
            "read": lambda part: part.read_status(),
            "reset": lambda part: part.reset(),
        }

        # Act
        held = {name: frame_flag_after(way) for name, way in ways.items()}

        # Assert
        self.assertEqual(held, dict.fromkeys(ways, 0), value("frameFlagCleared"))


class TimingTest(unittest.TestCase):
    def test_the_line_counts_are_table_3_3(self) -> None:
        # Arrange
        printed = value("lineTable")

        # Act
        held = {
            "pattern": runs(row({}, 0)),
            "text": runs(row({1: TEXT}, 0)),
            "vertical": runs(column("tms9918a")),
        }

        # Assert
        self.assertEqual(held, printed)

    def test_each_part_runs_the_lines_printed(self) -> None:
        # Arrange
        printed = value("frameLines")

        # Act
        held = {name: model.lines for name, model in tms9918.MODELS.items()}

        # Assert
        self.assertEqual(held, printed)

    def test_each_part_raises_the_frame_flag_once_per_printed_number_of_lines(self) -> None:
        # Arrange
        printed = value("frameLines")

        # Act
        held = {name: lines_per_frame(name) for name in printed}

        # Assert
        self.assertEqual(held, printed)

    def test_the_dividers_and_the_parts_with_clock_pins_are_the_ones_printed(
        self,
    ) -> None:
        # Arrange
        printed = value("dividers")

        # Act
        held = dividers()

        # Assert
        self.assertEqual(held, printed)

    def test_each_part_divides_the_master_clock_as_printed(self) -> None:
        # Arrange
        printed = value("dividers")
        pinned = {
            name: (
                EDGE_TICKS // printed["cpuclk"] if name in printed["pinsOn"] else 0,
                EDGE_TICKS // printed["gromclk"] if name in printed["pinsOn"] else 0,
            )
            for name in tms9918.MODELS
        }

        # Act
        held = {name: edges(name) for name in tms9918.MODELS}

        # Assert
        self.assertEqual(held, {name: (printed["dot"], *counts) for name, counts in pinned.items()})

    def test_the_windows_come_as_often_as_printed_in_each_mode(self) -> None:
        # Arrange
        printed = {
            "graphics": value("graphicsWindows"),
            "text": value("textWindows"),
            "multicolor": value("multicolorWindows"),
        }
        active = {
            "graphics": range(0, 512),
            "text": range(12, 492),
            "multicolor": range(0, 512),
        }
        modes = {"graphics": 0x40, "text": 0x50, "multicolor": 0x48}

        # Act
        held = {
            mode: largest_active_gap(windows({1: modes[mode]}, PICTURE_LINE), active[mode])
            // TICKS_PER_MEMORY_CYCLE
            for mode in printed
        }

        # Assert
        self.assertEqual(held, printed)

    def test_the_memory_cycle_is_four_master_ticks(self) -> None:
        # Arrange
        printed = value("memoryCycle")

        # Act
        held = TICKS_PER_MEMORY_CYCLE * 1e9 / MASTER_HZ

        # Assert
        self.assertAlmostEqual(held, printed, delta=1.0)

    def test_the_lead_is_the_one_the_record_names(self) -> None:
        # Arrange
        recorded = UNSTATED["accessLead"]["value"]

        # Act
        held = min(waits({1: 0x40}, PICTURE_LINE, data_write))

        # Assert
        self.assertEqual(held, recorded)

    def test_the_pal_borders_are_the_ones_the_record_names(self) -> None:
        # Arrange
        recorded = UNSTATED["palBorders"]["value"]

        # Act
        held = borders("tms9929a")

        # Assert
        self.assertEqual(held, recorded)


class PrintedAccessTest(unittest.TestCase):
    def test_no_data_access_waits_past_the_printed_time_in_any_mode(self) -> None:
        # Arrange
        printed = value("accessTime")["afterDataMicroseconds"]
        modes = {"graphics": 0x40, "text": 0x50, "multicolor": 0x48, "blanked": 0x00}

        # Act
        found = {
            name: worst_wait({1: bits}, PICTURE_LINE, data_write) for name, bits in modes.items()
        }

        # Assert
        self.assertEqual([name for name, wait in found.items() if wait > printed], [])

    def test_a_setup_with_the_display_blanked_is_served_in_the_printed_time(self) -> None:
        # Arrange
        printed = value("accessTime")["afterSetupMicroseconds"]

        # Act
        wait = worst_wait({1: 0x00}, PICTURE_LINE, read_setup)

        # Assert
        self.assertEqual(round(wait), printed)

    def test_a_blanked_access_waits_as_in_the_border_whatever_the_mode(self) -> None:
        # Arrange
        border = worst_wait({1: 0x40}, BORDER_LINE, data_write)
        modes = {"graphics": 0x00, "text": 0x10, "multicolor": 0x08}

        # Act
        found = {
            name: worst_wait({1: bits}, PICTURE_LINE, data_write) for name, bits in modes.items()
        }

        # Assert
        self.assertEqual(found, dict.fromkeys(modes, border), value("blankedAccess"))

    def test_sixteen_printed_memory_cycles_span_the_gap_between_graphics_windows(
        self,
    ) -> None:
        # Arrange
        printed = value("graphicsWindows") * value("memoryCycle")

        # Act
        found = largest_active_gap(windows({1: 0x40}, PICTURE_LINE), range(0, 512))
        gap = found * 1e9 / MASTER_HZ

        # Assert
        self.assertAlmostEqual(gap, printed, delta=value("graphicsWindows"))


if __name__ == "__main__":
    unittest.main()

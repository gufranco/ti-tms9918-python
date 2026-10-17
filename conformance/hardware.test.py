import copy
import itertools
import json
import sys
import unittest
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import tms9918  # noqa: E402
from conformance.bench import (  # noqa: E402
    FACTS,
    HELD,
    MASTER_HZ,
    UNSTATED,
    chip,
    dots_until,
    program,
    value,
)
from tms9918 import core, geometry, models, slots  # noqa: E402
from tms9918.memory import Vram  # noqa: E402

TICKS_PER_MEMORY_CYCLE = 4

WAIT_LIMIT = 1 << 10

FRAME = 0x80

EDGE_TICKS = 240


def largest_active_gap(table: tuple[int, ...], active: range) -> int:
    inside = [one for one in table if one in active]
    return max(later - earlier for earlier, later in itertools.pairwise(inside))


def ticks_to_serve(part: core.Chip) -> int:
    waited = 0
    while part.pending is not None and waited < WAIT_LIMIT:
        part.tick()
        waited += 1
    return waited


def worst_wait(registers: dict[int, int], line: int, ask: Callable[[core.Chip], None]) -> float:
    part = dots_until(program(chip(), registers), line, 0)
    longest = 0
    for _ in range(geometry.DOTS * 2):
        trial = copy.deepcopy(part)
        ask(trial)
        longest = max(longest, ticks_to_serve(trial))
        part.tick()
    return longest * 1e6 / MASTER_HZ


def read_setup(part: core.Chip) -> None:
    part.write_control(0x00)
    part.write_control(0x00)


def data_write(part: core.Chip) -> None:
    part.write_data(0x5A)


def frame_flag_after(clear: Callable[[core.Chip], object]) -> int:
    part = dots_until(chip(), geometry.ACTIVE_LINES, 1)
    clear(part)
    return part.status & FRAME


def counters(part: core.Chip) -> tuple[int, int, int, int]:
    return (part.line, part.dot, part.half, part.divider)


def edges(model: str) -> tuple[int, int, int]:
    part = chip(model)
    found = [part.tick() for _ in range(EDGE_TICKS)]
    before = part.cycles
    part.clock()
    return (
        part.cycles - before,
        sum(1 for one in found if one & core.CPUCLK),
        sum(1 for one in found if one & core.GROMCLK),
    )


def lines_per_frame(model: str) -> int:
    part = dots_until(chip(model), geometry.ACTIVE_LINES, 0)
    part.read_status()
    dots = 0
    while not part.status & FRAME and dots < geometry.DOTS * models.PAL_LINES:
        part.clock()
        dots += 1
    return (dots + 1) // geometry.DOTS


class DocumentTest(unittest.TestCase):
    def test_every_fact_names_a_document_the_record_declares(self) -> None:
        # Arrange
        declared = set(HELD["documents"])

        # Act
        unnamed = [name for name, fact in FACTS.items() if fact["document"] not in declared]

        # Assert
        self.assertEqual(unnamed, [])

    def test_every_fact_names_a_printed_page(self) -> None:
        # Arrange
        facts = FACTS

        # Act
        unpaged = [name for name, fact in facts.items() if "-" not in str(fact.get("page"))]

        # Assert
        self.assertEqual(unpaged, [])

    def test_every_entry_governs_parts_the_package_models(self) -> None:
        # Arrange
        entries = {**FACTS, **UNSTATED}

        # Act
        stray = [
            name
            for name, entry in entries.items()
            if not entry.get("governs") or not set(entry["governs"]) <= set(models.MODELS)
        ]

        # Assert
        self.assertEqual(stray, [])

    def test_the_record_and_the_document_list_name_the_same_file(self) -> None:
        # Arrange
        listed = json.loads((ROOT / "conformance" / "documents.json").read_text())

        # Act
        digests = {entry["sha256"] for entry in listed["documents"]}

        # Assert
        self.assertIn(HELD["documents"]["dataManual"]["sha256"], digests)

    def test_every_unstated_value_is_marked_and_says_how_to_settle_it(self) -> None:
        # Arrange
        entries = UNSTATED

        # Act
        loose = [
            name
            for name, entry in entries.items()
            if entry.get("verified") is not False
            or not entry.get("howToSettleIt")
            or not entry.get("source")
        ]

        # Assert
        self.assertEqual(loose, [])


class PortTest(unittest.TestCase):
    def test_the_address_register_is_fourteen_bits(self) -> None:
        # Arrange
        printed = value("addressRegister")["bits"]

        # Act
        held = Vram(fill=0).data

        # Assert
        self.assertEqual(len(held), 1 << printed)

    def test_the_write_setup_bit_is_the_one_the_manual_names(self) -> None:
        # Arrange
        printed = value("writeSetup")

        # Act
        held = core.WRITE_SETUP

        # Assert
        self.assertEqual(held, printed)

    def test_the_flags_and_enables_sit_where_the_manual_puts_them(self) -> None:
        # Arrange
        printed = (value("blank"), value("coincidence"), value("externalVideo"))

        # Act
        held = (core.BLANK, core.COINCIDENCE, core.EXTERNAL_VIDEO)

        # Assert
        self.assertEqual(held, printed)

    def test_reset_clears_exactly_the_registers_the_manual_names(self) -> None:
        # Arrange
        part = tms9918.Chip("tms9918a", Vram(fill=0), seed=7)
        part.registers[:] = bytes(range(1, 9))

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
        part.write_control(core.WRITE_SETUP | top >> 8)

        # Act
        for byte in (0x11, 0x22):
            part.write_data(byte)
            part.run_dots(64)

        # Assert
        self.assertEqual(
            (part.memory.read8(top), part.memory.read8(0), part.address),
            (0x11, 0x22, (top + 2) % (top + 1)),
            printed["autoincrements"],
        )

    def test_only_a_setup_without_the_printed_write_bits_asks_for_a_read(self) -> None:
        # Arrange
        printed = value("writeSetup")
        parts = {second: chip() for second in (0x00, printed)}

        # Act
        for second, part in parts.items():
            part.write_control(0x00)
            part.write_control(second)

        # Assert
        asked = {second: part.pending is not None for second, part in parts.items()}
        self.assertEqual(asked, {0x00: True, printed: False})

    def test_a_read_setup_leaves_the_named_byte_ready_for_the_first_read(self) -> None:
        # Arrange
        part = chip()
        stored = part.buffer ^ 0xFF
        part.memory.write8(0x1234, stored)
        part.write_control(0x34)
        part.write_control(0x12)
        part.run_dots(64)

        # Act
        read = part.read_data()

        # Assert
        self.assertEqual(read == stored, value("readSetupPrefetch"))

    def test_reading_the_status_clears_the_interrupt(self) -> None:
        # Arrange
        part = dots_until(program(chip(), {1: core.INTERRUPT_ENABLE}), geometry.ACTIVE_LINES, 1)
        before = part.interrupt

        # Act
        part.read_status()

        # Assert
        self.assertEqual((before, part.interrupt), (True, False), value("interruptCleared"))

    def test_reset_sets_the_counters_to_one_known_state_whatever_they_held(self) -> None:
        # Arrange
        parts = [tms9918.Chip("tms9918a", Vram(fill=0), seed=seed) for seed in (1, 2)]

        # Act
        held = [counters(part.reset()) for part in parts]

        # Assert
        self.assertEqual(held[0], held[1], value("reset")["setsCounters"])

    def test_the_frame_flag_rises_as_the_last_active_line_ends(self) -> None:
        # Arrange
        part = dots_until(chip(), geometry.ACTIVE_LINES - 1, geometry.DOTS - 1)
        before = part.status & FRAME

        # Act
        part.clock()

        # Assert
        self.assertEqual((before, part.status & FRAME), (0, FRAME), value("frameFlag"))

    def test_a_status_read_and_a_reset_each_clear_the_frame_flag(self) -> None:
        # Arrange
        ways = {"read": core.Chip.read_status, "reset": core.Chip.reset}

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
            "pattern": [count for _, count in geometry.PATTERN_COUNTS],
            "text": [count for _, count in geometry.TEXT_COUNTS],
            "vertical": [
                geometry.ACTIVE_LINES,
                models.NTSC_BOTTOM_BORDER,
                geometry.BOTTOM_BLANKING,
                geometry.VERTICAL_SYNC,
                geometry.TOP_BLANKING,
                models.NTSC_TOP_BORDER,
            ],
        }

        # Assert
        self.assertEqual(held, printed)

    def test_each_part_runs_the_lines_printed(self) -> None:
        # Arrange
        printed = value("frameLines")

        # Act
        held = {name: model.lines for name, model in models.MODELS.items()}

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
        held = {
            "dot": 2,
            "cpuclk": core.CPUCLK_DIVIDER,
            "gromclk": core.GROMCLK_DIVIDER,
            "pinsOn": [name for name, model in models.MODELS.items() if model.clock_pins],
        }

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
            for name in models.MODELS
        }

        # Act
        held = {name: edges(name) for name in models.MODELS}

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

        # Act
        held = {
            mode: largest_active_gap(slots.TABLES[mode], active[mode]) // TICKS_PER_MEMORY_CYCLE
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
        held = slots.LEAD

        # Assert
        self.assertEqual(held, recorded)

    def test_the_pal_borders_are_the_ones_the_record_names(self) -> None:
        # Arrange
        recorded = UNSTATED["palBorders"]["value"]

        # Act
        held = [models.PAL_TOP_BORDER, models.PAL_BOTTOM_BORDER]

        # Assert
        self.assertEqual(held, recorded)


class PrintedAccessTest(unittest.TestCase):
    def test_no_data_access_waits_past_the_printed_time_in_any_mode(self) -> None:
        # Arrange
        printed = value("accessTime")["afterDataMicroseconds"]
        modes = {"graphics": 0x40, "text": 0x50, "multicolor": 0x48, "blanked": 0x00}

        # Act
        waits = {name: worst_wait({1: bits}, 100, data_write) for name, bits in modes.items()}

        # Assert
        self.assertEqual([name for name, wait in waits.items() if wait > printed], [])

    def test_a_setup_with_the_display_blanked_is_served_in_the_printed_time(self) -> None:
        # Arrange
        printed = value("accessTime")["afterSetupMicroseconds"]

        # Act
        wait = worst_wait({1: 0x00}, 100, read_setup)

        # Assert
        self.assertEqual(round(wait), printed)

    def test_a_blanked_access_waits_as_in_the_border_whatever_the_mode(self) -> None:
        # Arrange
        border = worst_wait({1: 0x40}, 200, data_write)
        modes = {"graphics": 0x00, "text": 0x10, "multicolor": 0x08}

        # Act
        waits = {name: worst_wait({1: bits}, 100, data_write) for name, bits in modes.items()}

        # Assert
        self.assertEqual(waits, dict.fromkeys(modes, border), value("blankedAccess"))

    def test_sixteen_printed_memory_cycles_span_the_gap_between_graphics_windows(
        self,
    ) -> None:
        # Arrange
        printed = value("graphicsWindows") * value("memoryCycle")

        # Act
        gap = largest_active_gap(slots.TABLES["graphics"], range(0, 512)) * 1e9 / MASTER_HZ

        # Assert
        self.assertAlmostEqual(gap, printed, delta=value("graphicsWindows"))


if __name__ == "__main__":
    unittest.main()

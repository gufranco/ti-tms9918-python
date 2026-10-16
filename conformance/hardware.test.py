import itertools
import json
import sys
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import tms9918  # noqa: E402
from tms9918 import core, geometry, models, patterns, slots, sprites  # noqa: E402
from tms9918.memory import Vram  # noqa: E402

HELD: dict[str, Any] = json.loads((ROOT / "conformance" / "hardware.json").read_text())

FACTS: dict[str, Any] = HELD["facts"]

UNSTATED: dict[str, Any] = HELD["notStated"]

MASTER_HZ = 10_738_635

TICKS_PER_MEMORY_CYCLE = 4


def value(name: str) -> Any:
    return FACTS[name]["value"]


def addresses_read(held: bytearray, mode: str, line: int, column: int) -> list[int]:
    seen: list[int] = []

    def read(address: int) -> int:
        seen.append(address)
        return 0

    patterns.cell(read, held, mode, line, column)
    return seen


def largest_active_gap(table: tuple[int, ...], active: range) -> int:
    inside = [one for one in table if one in active]
    return max(later - earlier for earlier, later in itertools.pairwise(inside))


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


class TableTest(unittest.TestCase):
    def test_each_base_register_scales_by_the_factor_printed(self) -> None:
        # Arrange
        held = bytearray(8)
        held[2], held[3], held[4] = 1, 1, 1

        # Act
        name, pattern, colour = addresses_read(held, "graphics1", 0, 0)

        # Assert
        bases = value("tableBases")
        self.assertEqual((name, pattern, colour), (bases["2"], bases["4"], bases["3"]))

    def test_the_sprite_tables_scale_by_the_factors_printed(self) -> None:
        # Arrange
        held = bytearray(8)
        held[1], held[5], held[6] = 0x40, 1, 1
        seen: list[int] = []

        def read(address: int) -> int:
            seen.append(address)
            return 0xFF if not seen[:-1] else 0

        # Act
        sprites.evaluate(read, held, 0)

        # Assert
        bases = value("tableBases")
        self.assertEqual((seen[0], seen[4]), (bases["5"], bases["6"]))

    def test_text_has_the_grid_the_manual_prints(self) -> None:
        # Arrange
        printed = value("text")

        # Act
        held = {
            "columns": patterns.TEXT_COLUMNS,
            "rows": geometry.ACTIVE_LINES // 8,
            "width": patterns.TEXT_WIDTH,
        }

        # Assert
        self.assertEqual(held, printed)

    def test_the_second_row_of_multicolor_names_reads_bytes_three_and_four(
        self,
    ) -> None:
        # Arrange
        held = bytearray(8)

        # Act
        read = [addresses_read(held, "multicolor", line, 0)[1] for line in (8, 12)]

        # Assert
        self.assertEqual([one + 1 for one in read], value("multicolor")["secondNameRowBytes"])

    def test_the_mode_bits_select_the_modes_printed(self) -> None:
        # Arrange
        printed = {"graphics1": value("graphicsOne"), "graphics2": value("graphicsTwo")}

        # Act
        held = {
            name: patterns.mode_of(
                bits[2] * patterns.M3, bits[0] * patterns.M1 | bits[1] * patterns.M2
            )
            for name, bits in printed.items()
        }

        # Assert
        self.assertEqual(held, {name: name for name in printed})


class SpriteTest(unittest.TestCase):
    def test_the_sprite_constants_are_the_ones_printed(self) -> None:
        # Arrange
        printed = (value("fourPerLine"), value("terminator"), value("earlyClock"))

        # Act
        held = (sprites.SHOWN_PER_LINE, sprites.TERMINATOR, sprites.EARLY_SHIFT)

        # Assert
        self.assertEqual(held, printed)

    def test_a_position_of_minus_one_reaches_the_top_line(self) -> None:
        # Arrange
        printed = value("spriteTop")

        # Act
        top = sprites._top(printed & 0xFF)

        # Assert
        self.assertEqual(top, 0)


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


if __name__ == "__main__":
    unittest.main()

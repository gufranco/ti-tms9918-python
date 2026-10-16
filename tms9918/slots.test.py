import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import itertools  # noqa: E402
import unittest  # noqa: E402

from tms9918 import slots  # noqa: E402

MASTER_HZ = 10_738_635

MICROSECONDS_PER_TICK = 1e6 / MASTER_HZ

PATTERN_ACTIVE = range(0, 512)

TEXT_ACTIVE = range(12, 492)


def largest_gap_inside(table: tuple[int, ...], window: range) -> int:
    inside = [one for one in table if one in window]
    return max(later - earlier for earlier, later in itertools.pairwise(inside))


def worst_wait(table: tuple[int, ...]) -> int:
    served = set(table)
    longest = 0
    for asked in range(slots.TICKS):
        waited = slots.LEAD
        while (asked + waited) % slots.TICKS not in served:
            waited += 1
        longest = max(longest, waited)
    return longest


class ConversionTest(unittest.TestCase):
    def test_a_v99x8_position_becomes_a_master_tick_from_the_active_start(self) -> None:
        # Arrange
        position = 258

        # Act
        tick = slots.from_openmsx(position)

        # Assert
        self.assertEqual(tick, 0)

    def test_a_position_before_the_active_start_wraps_to_the_line_before(self) -> None:
        # Arrange
        position = 4

        # Act
        tick = slots.from_openmsx(position)

        # Assert
        self.assertEqual(tick, 684 - 127)

    def test_every_table_is_sorted_and_inside_one_line(self) -> None:
        # Arrange
        tables = slots.TABLES.values()

        # Act
        valid = [list(one) == sorted(one) and one[0] >= 0 and one[-1] < 684 for one in tables]

        # Assert
        self.assertEqual(valid, [True] * len(slots.TABLES))

    def test_the_tables_hold_the_counts_openmsx_lists(self) -> None:
        # Arrange
        tables = slots.TABLES

        # Act
        counts = {name: len(table) for name, table in tables.items()}

        # Assert
        self.assertEqual(counts, {"graphics": 19, "multicolor": 51, "text": 91, "off": 107})


class ManualBoundsTest(unittest.TestCase):
    def test_graphics_windows_come_every_16_memory_cycles_in_the_active_area(
        self,
    ) -> None:
        # Arrange
        table = slots.TABLES["graphics"]

        # Act
        gap = largest_gap_inside(table, PATTERN_ACTIVE)

        # Assert
        self.assertEqual(gap, 16 * 4)

    def test_which_is_the_595_microseconds_table_2_2_prints(self) -> None:
        # Arrange
        gap = largest_gap_inside(slots.TABLES["graphics"], PATTERN_ACTIVE)

        # Act
        microseconds = gap * MICROSECONDS_PER_TICK

        # Assert
        self.assertAlmostEqual(microseconds, 5.95, delta=0.01)

    def test_text_windows_come_once_in_three_memory_cycles(self) -> None:
        # Arrange
        table = slots.TABLES["text"]

        # Act
        gap = largest_gap_inside(table, TEXT_ACTIVE)

        # Assert
        self.assertEqual(gap, 3 * 4)

    def test_multicolor_windows_come_once_in_four_memory_cycles(self) -> None:
        # Arrange
        table = slots.TABLES["multicolor"]

        # Act
        gap = largest_gap_inside(table, PATTERN_ACTIVE)

        # Assert
        self.assertEqual(gap, 4 * 4)

    def test_no_access_in_any_mode_waits_past_the_8_microseconds_printed(self) -> None:
        # Arrange
        tables = slots.TABLES

        # Act
        waits = {name: worst_wait(table) * MICROSECONDS_PER_TICK for name, table in tables.items()}

        # Assert
        self.assertEqual([name for name, wait in waits.items() if wait > 8.0], [])

    def test_with_the_display_off_an_access_rounds_to_the_2_microseconds_printed(
        self,
    ) -> None:
        # Arrange
        table = slots.TABLES["off"]

        # Act
        microseconds = worst_wait(table) * MICROSECONDS_PER_TICK

        # Assert
        self.assertEqual(round(microseconds), 2)


def loses_at(spacing_in_cycles: int) -> bool:
    served = set(slots.TABLES["graphics"])
    for asked in range(slots.TICKS):
        waited = slots.LEAD
        while (asked + waited) % slots.TICKS not in served:
            waited += 1
        if waited > spacing_in_cycles * 3:
            return True
    return False


class MeasuredThresholdTest(unittest.TestCase):
    def test_writes_26_processor_cycles_apart_can_lose_one_as_on_an_msx(self) -> None:
        # Arrange
        spacing = 26

        # Act
        lost = loses_at(spacing)

        # Assert
        self.assertTrue(lost)

    def test_writes_27_processor_cycles_apart_never_lose_one(self) -> None:
        # Arrange
        spacing = 27

        # Act
        lost = loses_at(spacing)

        # Assert
        self.assertFalse(lost)


class SelectionTest(unittest.TestCase):
    def test_the_display_grid_off_means_the_off_table_whatever_the_mode(self) -> None:
        # Arrange
        modes = ("graphics", "multicolor", "text")

        # Act
        chosen = {slots.table_for(False, mode) for mode in modes}

        # Assert
        self.assertEqual(chosen, {slots.TABLES["off"]})

    def test_the_display_grid_on_means_the_mode_table(self) -> None:
        # Arrange
        modes = ("graphics", "multicolor", "text")

        # Act
        chosen = [slots.table_for(True, mode) for mode in modes]

        # Assert
        self.assertEqual(chosen, [slots.TABLES[mode] for mode in modes])


class GridTest(unittest.TestCase):
    def test_the_grid_turns_on_48_ticks_before_the_line_ahead_of_the_display(
        self,
    ) -> None:
        # Arrange
        lines = 262

        # Act
        before, after = (
            slots.grid_line(lines - 2, 635, lines),
            slots.grid_line(lines - 2, 636, lines),
        )

        # Assert
        self.assertEqual((before, after), (-2, -1))

    def test_and_counts_lines_from_the_first_active_one(self) -> None:
        # Arrange
        lines = 313

        # Act
        found = (slots.grid_line(0, 0, lines), slots.grid_line(191, 636, lines))

        # Assert
        self.assertEqual(found, (0, 192))

    def test_the_grid_line_decides_whether_the_display_grid_applies(self) -> None:
        # Arrange
        lines = (-2, -1, 191, 192)

        # Act
        applies = [slots.display_grid(line) for line in lines]

        # Assert
        self.assertEqual(applies, [False, True, True, False])


if __name__ == "__main__":
    unittest.main()

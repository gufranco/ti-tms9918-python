import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import copy  # noqa: E402
import functools  # noqa: E402
import itertools  # noqa: E402
import unittest  # noqa: E402
from typing import Any  # noqa: E402

import tms9918  # noqa: E402

MASTER_HZ = 10_738_635

MICROSECONDS_PER_TICK = 1e6 / MASTER_HZ

TICKS = 684

PATTERN_ACTIVE = range(0, 512)

TEXT_ACTIVE = range(12, 492)

WATCHED = 0x3000

WAIT_LIMIT = 1 << 10

PICTURE_LINE = 100

LATER_PICTURE_LINE = 150

LINES = 262

GRAPHICS = 0x40

MULTICOLOR = 0x48

TEXT = 0x50

OFF = 0x00

MODES = {"graphics": GRAPHICS, "multicolor": MULTICOLOR, "text": TEXT, "off": OFF}


class Watch:
    __slots__ = ("hits", "store")

    def __init__(self) -> None:
        self.store = tms9918.Vram(fill=0)
        self.hits = 0

    def read8(self, address: int) -> int:
        self.hits += address == WATCHED
        return self.store.read8(address)

    def write8(self, address: int, value: int) -> None:
        self.hits += address == WATCHED
        self.store.write8(address, value)


def ready(r1: int, line: int) -> Any:
    part: Any = tms9918.Chip("tms9918a", Watch()).reset()
    part.read_status()
    for register, value in {0: 0, 1: r1, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0}.items():
        part.write_control(value)
        part.write_control(0x80 | register)
    part.write_control(WATCHED & 0xFF)
    part.write_control(0x40 | WATCHED >> 8)
    while (part.line, part.dot) != (line, 0):
        part.clock()
    return part


def served(part: Any) -> bool:
    part.tick()
    return bool(part.memory.hits)


def ticks_to_window(part: Any) -> int:
    part.write_data(0x5A)
    return next(waited for waited in range(WAIT_LIMIT) if served(part))


@functools.cache
def waits(r1: int, line: int = PICTURE_LINE) -> dict[int, int]:
    part = ready(r1, line)
    found: dict[int, int] = {}
    for asked in range(TICKS):
        found[asked] = ticks_to_window(copy.deepcopy(part))
        part.tick()
    return found


def windows(r1: int, line: int = PICTURE_LINE) -> list[int]:
    return sorted({(asked + waited) % TICKS for asked, waited in waits(r1, line).items()})


def landing(line: int, asked: int) -> int:
    part = ready(GRAPHICS, line)
    for _ in range(asked):
        part.tick()
    return asked + ticks_to_window(part)


def largest_gap_inside(found: list[int], window: range) -> int:
    inside = [one for one in found if one in window]
    return max(later - earlier for earlier, later in itertools.pairwise(inside))


def worst_wait(r1: int) -> float:
    return max(waits(r1).values()) * MICROSECONDS_PER_TICK


def loses_at(spacing_in_cycles: int) -> bool:
    part = ready(GRAPHICS, PICTURE_LINE)
    for _ in range(TICKS):
        trial = copy.deepcopy(part)
        trial.write_data(0x11)
        for _ in range(spacing_in_cycles * 3):
            trial.tick()
        trial.write_data(0x22)
        trial.run_dots(TICKS)
        if trial.memory.store.read8(WATCHED) != 0x11:
            return True
        part.tick()
    return False


class PositionTest(unittest.TestCase):
    def test_the_first_graphics_window_in_the_picture_is_45_ticks_in(self) -> None:
        # Arrange
        mode = GRAPHICS

        # Act
        first = windows(mode)[0]

        # Assert
        self.assertEqual(first, 45)

    def test_every_mode_has_a_window_127_ticks_before_the_line_ends(self) -> None:
        # Arrange
        modes = MODES

        # Act
        held = {name: 684 - 127 in windows(r1) for name, r1 in modes.items()}

        # Assert
        self.assertEqual(held, dict.fromkeys(modes, True))

    def test_the_windows_fall_on_the_same_ticks_on_every_picture_line(self) -> None:
        # Arrange
        modes = MODES

        # Act
        moved = [
            name
            for name, r1 in modes.items()
            if windows(r1, PICTURE_LINE) != windows(r1, LATER_PICTURE_LINE)
        ]

        # Assert
        self.assertEqual(moved, [])

    def test_the_lines_hold_the_counts_openmsx_lists(self) -> None:
        # Arrange
        modes = MODES

        # Act
        counts = {name: len(windows(r1)) for name, r1 in modes.items()}

        # Assert
        self.assertEqual(counts, {"graphics": 19, "multicolor": 51, "text": 91, "off": 107})


class ManualBoundsTest(unittest.TestCase):
    def test_graphics_windows_come_every_16_memory_cycles_in_the_active_area(
        self,
    ) -> None:
        # Arrange
        found = windows(GRAPHICS)

        # Act
        gap = largest_gap_inside(found, PATTERN_ACTIVE)

        # Assert
        self.assertEqual(gap, 16 * 4)

    def test_which_is_the_595_microseconds_table_2_2_prints(self) -> None:
        # Arrange
        gap = largest_gap_inside(windows(GRAPHICS), PATTERN_ACTIVE)

        # Act
        microseconds = gap * MICROSECONDS_PER_TICK

        # Assert
        self.assertAlmostEqual(microseconds, 5.95, delta=0.01)

    def test_text_windows_come_once_in_three_memory_cycles(self) -> None:
        # Arrange
        found = windows(TEXT)

        # Act
        gap = largest_gap_inside(found, TEXT_ACTIVE)

        # Assert
        self.assertEqual(gap, 3 * 4)

    def test_multicolor_windows_come_once_in_four_memory_cycles(self) -> None:
        # Arrange
        found = windows(MULTICOLOR)

        # Act
        gap = largest_gap_inside(found, PATTERN_ACTIVE)

        # Assert
        self.assertEqual(gap, 4 * 4)

    def test_no_access_in_any_mode_waits_past_the_8_microseconds_printed(self) -> None:
        # Arrange
        modes = MODES

        # Act
        found = {name: worst_wait(r1) for name, r1 in modes.items()}

        # Assert
        self.assertEqual([name for name, wait in found.items() if wait > 8.0], [])

    def test_with_the_display_off_an_access_rounds_to_the_2_microseconds_printed(
        self,
    ) -> None:
        # Arrange
        mode = OFF

        # Act
        microseconds = worst_wait(mode)

        # Assert
        self.assertEqual(round(microseconds), 2)


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
    def test_the_display_off_means_the_off_windows_whatever_the_mode(self) -> None:
        # Arrange
        modes = (GRAPHICS, MULTICOLOR, TEXT)

        # Act
        chosen = [windows(r1 & ~GRAPHICS) for r1 in modes]

        # Assert
        self.assertEqual(chosen, [windows(OFF)] * len(modes))

    def test_the_display_on_means_each_mode_its_own_windows(self) -> None:
        # Arrange
        modes = (GRAPHICS, MULTICOLOR, TEXT, OFF)

        # Act
        chosen = {tuple(windows(r1)) for r1 in modes}

        # Assert
        self.assertEqual(len(chosen), len(modes))


class GridTest(unittest.TestCase):
    def test_the_grid_turns_on_48_ticks_before_the_line_ahead_of_the_display(
        self,
    ) -> None:
        # Arrange
        asked = ((LINES - 2, 617), (LINES - 2, 621), (LINES - 3, 621))

        # Act
        found = [landing(line, tick) for line, tick in asked]

        # Assert
        self.assertEqual(found, [633, 665, 637])

    def test_and_turns_off_48_ticks_before_the_last_active_line_ends(self) -> None:
        # Arrange
        asked = ((191, 621), (190, 621))

        # Act
        found = [landing(line, tick) for line, tick in asked]

        # Assert
        self.assertEqual(found, [637, 665])

    def test_the_grid_spans_the_line_before_the_first_to_the_last_active_one(self) -> None:
        # Arrange
        asked = ((LINES - 3, 617), (LINES - 1, 617), (191, 100), (192, 100))

        # Act
        found = [landing(line, tick) for line, tick in asked]

        # Assert
        self.assertEqual(found, [633, 665, 173, 117])


if __name__ == "__main__":
    unittest.main()

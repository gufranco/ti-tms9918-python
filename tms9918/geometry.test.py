import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import unittest  # noqa: E402
from collections import Counter  # noqa: E402
from typing import Any  # noqa: E402

import tms9918  # noqa: E402

PATTERN_COUNTS = {"active": 256, "border": 28, "blanking": 18, "sync": 26, "burst": 14}

TEXT_COUNTS = {"active": 240, "border": 44, "blanking": 18, "sync": 26, "burst": 14}

TEXT = 0x10

GRAPHICS_ONE = 0x00

SAMPLED_DOT = 100

ACTIVE_DOT = 100

SYNC_DOT = 290

BURST_DOT = 310

BORDER_LINE = 192

BLANKING_LINE = 216

SYNC_LINE = 219


def ready(model: str = "tms9918a", mode: int = GRAPHICS_ONE) -> Any:
    part: Any = tms9918.Chip(model, tms9918.Vram(fill=0)).reset()
    part.read_status()
    part.write_control(mode)
    part.write_control(0x81)
    return part


def row(line: int, mode: int = GRAPHICS_ONE) -> list[str]:
    part = ready(mode=mode)
    while (part.line, part.dot) != (line, 0):
        part.clock()
    found: list[str] = []
    while not found or (part.line, part.dot) != (line + 1, 0):
        part.clock()
        found.append(part.region)
    return found


def column(model: str) -> list[str]:
    part = ready(model)
    found: list[str] = []
    for line in range(part.part.lines):
        while (part.line, part.dot) != (line, SAMPLED_DOT):
            part.clock()
        part.clock()
        found.append(part.region)
    return found


def span(regions: list[str], wanted: str) -> tuple[int, int]:
    return (regions.index(wanted), len(regions) - regions[::-1].index(wanted) - 1)


class HorizontalTest(unittest.TestCase):
    def test_a_pattern_line_holds_the_dots_table_3_3_gives_each_region(self) -> None:
        # Arrange
        mode = GRAPHICS_ONE

        # Act
        counted = Counter(row(0, mode))

        # Assert
        self.assertEqual(dict(counted), PATTERN_COUNTS)

    def test_a_text_line_holds_its_own_column_of_table_3_3(self) -> None:
        # Arrange
        mode = TEXT

        # Act
        counted = Counter(row(0, mode))

        # Assert
        self.assertEqual(dict(counted), TEXT_COUNTS)

    def test_both_lines_are_342_dots(self) -> None:
        # Arrange
        modes = (GRAPHICS_ONE, TEXT)

        # Act
        lengths = [len(row(0, mode)) for mode in modes]

        # Assert
        self.assertEqual(lengths, [342, 342])

    def test_the_pattern_active_area_starts_the_line(self) -> None:
        # Arrange
        regions = row(0, GRAPHICS_ONE)

        # Act
        found = span(regions, "active")

        # Assert
        self.assertEqual(found, (0, 255))

    def test_sync_falls_on_the_same_dots_in_both_lines(self) -> None:
        # Arrange
        rows = (row(0, GRAPHICS_ONE), row(0, TEXT))

        # Act
        syncs = [[dot for dot, one in enumerate(regions) if one == "sync"] for regions in rows]

        # Assert
        self.assertEqual(syncs[0], syncs[1])
        self.assertEqual((syncs[0][0], syncs[0][-1]), (279, 304))

    def test_so_the_text_area_starts_six_dots_later(self) -> None:
        # Arrange
        regions = row(0, TEXT)

        # Act
        found = span(regions, "active")

        # Assert
        self.assertEqual(found, (6, 245))


class VerticalTest(unittest.TestCase):
    def test_an_ntsc_frame_holds_the_lines_table_3_3_gives_each_region(self) -> None:
        # Arrange
        model = "tms9918a"

        # Act
        counted = Counter(column(model))

        # Assert
        self.assertEqual(dict(counted), {"active": 192, "border": 51, "blanking": 16, "sync": 3})

    def test_a_pal_frame_holds_313_lines_with_the_same_blanking(self) -> None:
        # Arrange
        model = "tms9929a"

        # Act
        counted = Counter(column(model))

        # Assert
        self.assertEqual(dict(counted), {"active": 192, "border": 102, "blanking": 16, "sync": 3})

    def test_the_ntsc_sync_follows_the_bottom_border_and_its_blanking(self) -> None:
        # Arrange
        model = "tms9928a"

        # Act
        kinds = column(model)

        # Assert
        self.assertEqual(
            kinds[215:223],
            [
                "border",
                "blanking",
                "blanking",
                "blanking",
                "sync",
                "sync",
                "sync",
                "blanking",
            ],
        )


class RegionTest(unittest.TestCase):
    def test_an_active_line_shows_its_row(self) -> None:
        # Arrange
        line = 0

        # Act
        found = row(line)[300]

        # Assert
        self.assertEqual(found, "sync")

    def test_a_border_line_turns_the_active_dots_to_border(self) -> None:
        # Arrange
        regions = row(BORDER_LINE)

        # Act
        found = [regions[dot] for dot in (ACTIVE_DOT, BURST_DOT, SYNC_DOT)]

        # Assert
        self.assertEqual(found, ["border", "burst", "sync"])

    def test_a_blanking_line_keeps_sync_and_suppresses_the_burst(self) -> None:
        # Arrange
        regions = row(BLANKING_LINE)

        # Act
        found = [regions[dot] for dot in (ACTIVE_DOT, BURST_DOT, SYNC_DOT)]

        # Assert
        self.assertEqual(found, ["blanking", "blanking", "sync"])

    def test_a_sync_line_is_sync_throughout(self) -> None:
        # Arrange
        regions = row(SYNC_LINE)

        # Act
        found = set(regions)

        # Assert
        self.assertEqual(found, {"sync"})


if __name__ == "__main__":
    unittest.main()

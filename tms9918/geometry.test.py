import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import unittest  # noqa: E402
from collections import Counter  # noqa: E402

from tms9918 import geometry  # noqa: E402
from tms9918.models import MODELS  # noqa: E402

PATTERN_COUNTS = {"active": 256, "border": 28, "blanking": 18, "sync": 26, "burst": 14}

TEXT_COUNTS = {"active": 240, "border": 44, "blanking": 18, "sync": 26, "burst": 14}


class HorizontalTest(unittest.TestCase):
    def test_a_pattern_line_holds_the_dots_table_3_3_gives_each_region(self) -> None:
        # Arrange
        row = geometry.PATTERN_ROW

        # Act
        counted = Counter(row)

        # Assert
        self.assertEqual(dict(counted), PATTERN_COUNTS)

    def test_a_text_line_holds_its_own_column_of_table_3_3(self) -> None:
        # Arrange
        row = geometry.TEXT_ROW

        # Act
        counted = Counter(row)

        # Assert
        self.assertEqual(dict(counted), TEXT_COUNTS)

    def test_both_lines_are_342_dots(self) -> None:
        # Arrange
        rows = (geometry.PATTERN_ROW, geometry.TEXT_ROW)

        # Act
        lengths = [len(row) for row in rows]

        # Assert
        self.assertEqual(lengths, [342, 342])

    def test_the_pattern_active_area_starts_the_line(self) -> None:
        # Arrange
        row = geometry.PATTERN_ROW

        # Act
        span = (row.index("active"), len(row) - row[::-1].index("active") - 1)

        # Assert
        self.assertEqual(span, (0, 255))

    def test_sync_falls_on_the_same_dots_in_both_lines(self) -> None:
        # Arrange
        rows = (geometry.PATTERN_ROW, geometry.TEXT_ROW)

        # Act
        syncs = [[dot for dot, one in enumerate(row) if one == "sync"] for row in rows]

        # Assert
        self.assertEqual(syncs[0], syncs[1])
        self.assertEqual((syncs[0][0], syncs[0][-1]), (279, 304))

    def test_so_the_text_area_starts_six_dots_later(self) -> None:
        # Arrange
        row = geometry.TEXT_ROW

        # Act
        span = (row.index("active"), len(row) - row[::-1].index("active") - 1)

        # Assert
        self.assertEqual(span, (6, 245))


class VerticalTest(unittest.TestCase):
    def test_an_ntsc_frame_holds_the_lines_table_3_3_gives_each_region(self) -> None:
        # Arrange
        part = MODELS["tms9918a"]

        # Act
        counted = Counter(geometry.lines_of(part))

        # Assert
        self.assertEqual(dict(counted), {"active": 192, "border": 51, "blanking": 16, "sync": 3})

    def test_a_pal_frame_holds_313_lines_with_the_same_blanking(self) -> None:
        # Arrange
        part = MODELS["tms9929a"]

        # Act
        counted = Counter(geometry.lines_of(part))

        # Assert
        self.assertEqual(dict(counted), {"active": 192, "border": 102, "blanking": 16, "sync": 3})

    def test_the_ntsc_sync_follows_the_bottom_border_and_its_blanking(self) -> None:
        # Arrange
        part = MODELS["tms9928a"]

        # Act
        kinds = geometry.lines_of(part)

        # Assert
        self.assertEqual(
            kinds[215:223],
            (
                "border",
                "blanking",
                "blanking",
                "blanking",
                "sync",
                "sync",
                "sync",
                "blanking",
            ),
        )


class RegionTest(unittest.TestCase):
    def test_an_active_line_shows_its_row(self) -> None:
        # Arrange
        line = "active"

        # Act
        found = geometry.region(line, geometry.PATTERN_ROW[300])

        # Assert
        self.assertEqual(found, "sync")

    def test_a_border_line_turns_the_active_dots_to_border(self) -> None:
        # Arrange
        line = "border"

        # Act
        found = [geometry.region(line, one) for one in ("active", "burst", "sync")]

        # Assert
        self.assertEqual(found, ["border", "burst", "sync"])

    def test_a_blanking_line_keeps_sync_and_suppresses_the_burst(self) -> None:
        # Arrange
        line = "blanking"

        # Act
        found = [geometry.region(line, one) for one in ("active", "burst", "sync")]

        # Assert
        self.assertEqual(found, ["blanking", "blanking", "sync"])

    def test_a_sync_line_is_sync_throughout(self) -> None:
        # Arrange
        line = "sync"

        # Act
        found = {geometry.region(line, one) for one in set(geometry.PATTERN_ROW)}

        # Assert
        self.assertEqual(found, {"sync"})


if __name__ == "__main__":
    unittest.main()

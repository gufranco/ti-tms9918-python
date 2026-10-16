import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import unittest  # noqa: E402

from tms9918 import levels  # noqa: E402


class CompositeTest(unittest.TestCase):
    def test_white_is_full_luminance_with_no_chrominance(self) -> None:
        # Arrange
        colour = 0xF

        # Act
        level = levels.COMPOSITE[colour]

        # Assert
        self.assertEqual(level, (1.00, None))

    def test_cyan_reads_as_printed_on_the_composite_part(self) -> None:
        # Arrange
        colour = 0x7

        # Act
        level = levels.COMPOSITE[colour]

        # Assert
        self.assertEqual(level, (0.67, 0.60))

    def test_transparent_has_no_entry_of_its_own(self) -> None:
        # Arrange
        colour = 0x0

        # Act
        present = colour in levels.COMPOSITE

        # Assert
        self.assertFalse(present)

    def test_sync_sits_below_black(self) -> None:
        # Arrange
        named = levels.COMPOSITE_SPECIAL

        # Act
        sync = named["sync"]

        # Assert
        self.assertEqual(sync, (-0.40, None))


class DifferenceTest(unittest.TestCase):
    def test_dark_blue_keeps_the_single_digit_the_page_prints(self) -> None:
        # Arrange
        colour = 0x4

        # Act
        level = levels.DIFFERENCE[colour]

        # Assert
        self.assertEqual(level, (0.40, 0.4, 1.00))

    def test_cyan_reads_point_73_on_the_difference_parts(self) -> None:
        # Arrange
        colour = 0x7

        # Act
        level = levels.DIFFERENCE[colour]

        # Assert
        self.assertEqual(level, (0.73, 0.00, 0.70))

    def test_the_burst_differs_between_the_two_difference_parts(self) -> None:
        # Arrange
        parts = ("tms9928a", "tms9929a")

        # Act
        bursts = [levels.burst(part) for part in parts]

        # Assert
        self.assertEqual(bursts, [(0.00, 0.47, 0.1), (0.00, 0.73, 0.2)])

    def test_external_video_swings_both_differences_to_the_sync_level(self) -> None:
        # Arrange
        named = levels.DIFFERENCE_SPECIAL

        # Act
        external = named["external"]

        # Assert
        self.assertEqual(external, (0.00, -0.46, -0.46))

    def test_every_colour_but_transparent_has_a_level_on_both_kinds_of_part(
        self,
    ) -> None:
        # Arrange
        colours = range(1, 16)

        # Act
        missing = [c for c in colours if c not in levels.COMPOSITE or c not in levels.DIFFERENCE]

        # Assert
        self.assertEqual(missing, [])


class BurstTest(unittest.TestCase):
    def test_the_composite_part_has_no_difference_burst(self) -> None:
        # Arrange
        part = "tms9918a"

        # Act
        attempt = lambda: levels.burst(part)  # noqa: E731

        # Assert
        self.assertRaises(KeyError, attempt)


if __name__ == "__main__":
    unittest.main()

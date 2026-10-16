import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import functools  # noqa: E402
import unittest  # noqa: E402

from tms9918 import models  # noqa: E402
from tms9918.errors import UnknownModelError  # noqa: E402


class CatalogueTest(unittest.TestCase):
    def test_it_covers_the_three_parts_the_manual_documents(self) -> None:
        # Arrange
        documented = ["tms9918a", "tms9928a", "tms9929a"]

        # Act
        covered = sorted(models.MODELS)

        # Assert
        self.assertEqual(covered, documented)

    def test_the_two_ntsc_parts_run_262_lines_and_the_pal_part_313(self) -> None:
        # Arrange
        catalogue = models.MODELS

        # Act
        lines = {name: model.lines for name, model in catalogue.items()}

        # Assert
        self.assertEqual(lines, {"tms9918a": 262, "tms9928a": 262, "tms9929a": 313})

    def test_only_the_composite_part_brings_out_the_clock_pins(self) -> None:
        # Arrange
        catalogue = models.MODELS

        # Act
        pins = {name: model.clock_pins for name, model in catalogue.items()}

        # Assert
        self.assertEqual(pins, {"tms9918a": True, "tms9928a": False, "tms9929a": False})

    def test_the_ntsc_borders_are_the_ones_table_3_3_prints(self) -> None:
        # Arrange
        part = models.MODELS["tms9918a"]

        # Act
        borders = (part.top_border, part.bottom_border)

        # Assert
        self.assertEqual(borders, (27, 24))

    def test_the_pal_borders_fill_the_294_lines_figure_5_13_gives_them(self) -> None:
        # Arrange
        part = models.MODELS["tms9929a"]

        # Act
        bordered = part.top_border + 192 + part.bottom_border

        # Assert
        self.assertEqual(bordered, 294)

    def test_a_model_describes_itself_by_name_lines_and_output(self) -> None:
        # Arrange
        part = models.MODELS["tms9929a"]

        # Act
        shown = repr(part)

        # Assert
        self.assertEqual(shown, "<Model tms9929a, 313 lines, colour difference>")


class LookupTest(unittest.TestCase):
    def test_a_name_is_found_however_it_is_spelled(self) -> None:
        # Arrange
        spelled = " TMS-9928A "

        # Act
        found = models.lookup(spelled)

        # Assert
        self.assertIs(found, models.MODELS["tms9928a"])

    def test_a_short_alias_finds_its_part(self) -> None:
        # Arrange
        alias = "9929a"

        # Act
        found = models.lookup(alias)

        # Assert
        self.assertIs(found, models.MODELS["tms9929a"])

    def test_the_part_without_the_a_suffix_is_not_taken_for_it(self) -> None:
        # Arrange
        name = "tms9918"

        # Act
        attempt = functools.partial(models.lookup, name)

        # Assert
        with self.assertRaisesRegex(UnknownModelError, "tms9918 is not a model"):
            attempt()

    def test_naming_no_model_is_refused_with_the_list(self) -> None:
        # Arrange
        name = None

        # Act
        attempt = functools.partial(models.lookup, name)

        # Assert
        with self.assertRaisesRegex(UnknownModelError, "tms9918a, tms9928a, tms9929a"):
            attempt()

    def test_a_name_no_model_goes_by_is_refused(self) -> None:
        # Arrange
        name = "tms9938"

        # Act
        attempt = functools.partial(models.lookup, name)

        # Assert
        with self.assertRaisesRegex(UnknownModelError, "tms9938 is not a model"):
            attempt()


if __name__ == "__main__":
    unittest.main()

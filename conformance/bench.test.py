import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from conformance import bench  # noqa: E402


class RecordTest(unittest.TestCase):
    def test_a_value_is_read_from_the_fact_it_names(self) -> None:
        # Arrange
        name = "memoryCycle"

        # Act
        held = bench.value(name)

        # Assert
        self.assertEqual(held, 372)

    def test_the_quotes_are_read_from_the_fact_they_belong_to(self) -> None:
        # Arrange
        name = "fourPerLine"

        # Act
        held = bench.quotes(name)

        # Assert
        self.assertEqual(held[0], "Only four sprites can be active on any horizontal line.")


class PartTest(unittest.TestCase):
    def test_a_bench_part_comes_up_reset_with_its_flags_read(self) -> None:
        # Arrange
        model = "tms9929a"

        # Act
        part = bench.chip(model)

        # Assert
        self.assertEqual(
            (part.model, part.registers[0], part.registers[1], part.status & 0xE0, part.latch),
            (model, 0, 0, 0, False),
        )

    def test_programming_a_register_loads_it(self) -> None:
        # Arrange
        part = bench.chip()

        # Act
        bench.program(part, {7: 0x5A})

        # Assert
        self.assertEqual(part.registers[7], 0x5A)

    def test_running_to_a_dot_stops_on_it(self) -> None:
        # Arrange
        part = bench.chip()

        # Act
        bench.dots_until(part, 3, 17)

        # Assert
        self.assertEqual((part.line, part.dot), (3, 17))

    def test_the_colour_at_a_border_dot_is_the_backdrop(self) -> None:
        # Arrange
        part = bench.program(bench.chip(), {1: 0x40, 7: 0x09})

        # Act
        shown = bench.colour_at(part, 0, 260)

        # Assert
        self.assertEqual(shown, 9)


if __name__ == "__main__":
    unittest.main()

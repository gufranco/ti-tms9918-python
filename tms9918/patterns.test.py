import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import random  # noqa: E402
import unittest  # noqa: E402

from tms9918 import patterns  # noqa: E402
from tms9918.memory import Vram  # noqa: E402

SEED = 1982


def registers(**values: int) -> bytearray:
    held = bytearray(8)
    for name, value in values.items():
        held[int(name[1:])] = value
    return held


class ModeTest(unittest.TestCase):
    def test_the_four_documented_modes_follow_the_m1_m2_m3_table(self) -> None:
        # Arrange
        settings = {
            "graphics1": (0x00, 0x00),
            "graphics2": (0x02, 0x00),
            "multicolor": (0x00, 0x08),
            "text": (0x00, 0x10),
        }

        # Act
        found = {name: patterns.mode_of(r0, r1) for name, (r0, r1) in settings.items()}

        # Assert
        self.assertEqual(found, {name: name for name in settings})

    def test_the_combinations_the_table_leaves_out_are_named_apart(self) -> None:
        # Arrange
        settings = [(0x00, 0x18), (0x02, 0x08), (0x02, 0x10), (0x02, 0x18)]

        # Act
        found = [patterns.mode_of(r0, r1) for r0, r1 in settings]

        # Assert
        self.assertEqual(
            found,
            [
                "text+multicolor",
                "graphics2+multicolor",
                "text+graphics2",
                "text+graphics2+multicolor",
            ],
        )

    def test_text_and_its_combinations_use_the_text_line(self) -> None:
        # Arrange
        modes = ("text", "text+multicolor", "graphics1", "multicolor")

        # Act
        texty = [patterns.is_text(mode) for mode in modes]

        # Assert
        self.assertEqual(texty, [True, True, False, False])


class GraphicsOneTest(unittest.TestCase):
    def test_a_cell_takes_its_bits_from_the_pattern_and_its_colours_from_the_group(
        self,
    ) -> None:
        # Arrange
        vram = Vram(fill=0)
        held = registers(r2=0x06, r3=0x80, r4=0x00)
        name = 0x41
        vram.write8(0x1800 + 3 * 32 + 5, name)
        vram.write8(0x0000 + name * 8 + 2, 0b10110000)
        vram.write8(0x2000 + (name >> 3), 0x71)

        # Act
        dots = patterns.cell(vram.read8, held, "graphics1", 3 * 8 + 2, 5)

        # Assert
        self.assertEqual(dots, (7, 1, 7, 7, 1, 1, 1, 1))


class GraphicsTwoTest(unittest.TestCase):
    def test_the_lower_third_reads_the_third_pattern_and_colour_block(self) -> None:
        # Arrange
        vram = Vram(fill=0)
        held = registers(r0=0x02, r2=0x0E, r3=0xFF, r4=0x03)
        name = 0x10
        line = 128 + 8 * 2 + 6
        vram.write8(0x3800 + (line >> 3) * 32 + 9, name)
        vram.write8(0x0000 + 0x1000 + name * 8 + 6, 0b00000001)
        vram.write8(0x2000 + 0x1000 + name * 8 + 6, 0xF4)

        # Act
        dots = patterns.cell(vram.read8, held, "graphics2", line, 9)

        # Assert
        self.assertEqual(dots, (4, 4, 4, 4, 4, 4, 4, 15))

    def test_clear_low_bits_in_r4_fold_the_pattern_thirds_together(self) -> None:
        # Arrange
        vram = Vram(fill=0)
        held = registers(r0=0x02, r2=0x0E, r3=0xFF, r4=0x00)
        name = 0x10
        line = 128
        vram.write8(0x3800 + (line >> 3) * 32, name)
        vram.write8(0x0000 + name * 8, 0xFF)
        vram.write8(0x2000 + 0x1000 + name * 8, 0x50)

        # Act
        dots = patterns.cell(vram.read8, held, "graphics2", line, 0)

        # Assert
        self.assertEqual(dots, (5,) * 8)


class MulticolorTest(unittest.TestCase):
    def test_each_name_row_reads_its_own_pair_of_bytes(self) -> None:
        # Arrange
        vram = Vram(fill=0)
        held = registers(r2=0x02, r4=0x01)
        name = 0x20
        line = 8 * 1 + 4
        vram.write8(0x0800 + (line >> 3) * 32 + 2, name)
        vram.write8(0x0800 + name * 8 + 3, 0x9C)

        # Act
        dots = patterns.cell(vram.read8, held, "multicolor", line, 2)

        # Assert
        self.assertEqual(dots, (9, 9, 9, 9, 12, 12, 12, 12))


class TextTest(unittest.TestCase):
    def test_a_cell_is_six_dots_in_the_two_register_7_colours(self) -> None:
        # Arrange
        vram = Vram(fill=0)
        held = registers(r2=0x00, r4=0x01, r7=0xF4)
        name = random.Random(SEED).randrange(256)
        vram.write8(0x0000 + 2 * 40 + 39, name)
        vram.write8(0x0800 + name * 8 + 1, 0b11000111)

        # Act
        dots = patterns.cell(vram.read8, held, "text", 2 * 8 + 1, 39)

        # Assert
        self.assertEqual(dots, (15, 15, 4, 4, 4, 15))


class UndocumentedTest(unittest.TestCase):
    def test_text_with_multicolor_draws_four_on_and_two_off(self) -> None:
        # Arrange
        vram = Vram(fill=0)
        held = registers(r7=0x6A)

        # Act
        dots = patterns.cell(vram.read8, held, "text+multicolor", 0, 0)

        # Assert
        self.assertEqual(dots, (6, 6, 6, 6, 10, 10))

    def test_text_with_graphics_two_reads_the_masked_third(self) -> None:
        # Arrange
        vram = Vram(fill=0)
        held = registers(r0=0x02, r3=0xFF, r4=0x03, r7=0xF0)
        name = 0x02
        line = 64
        vram.write8(0x0000 + (line >> 3) * 40, name)
        vram.write8(0x0000 + 0x0800 + name * 8, 0b10000000)

        # Act
        dots = patterns.cell(vram.read8, held, "text+graphics2", line, 0)

        # Assert
        self.assertEqual(dots, (15, 0, 0, 0, 0, 0))

    def test_graphics_two_with_multicolor_reads_colours_through_the_thirds(
        self,
    ) -> None:
        # Arrange
        vram = Vram(fill=0)
        held = registers(r0=0x02, r2=0x06, r3=0xFF, r4=0x03)
        name = 0x01
        line = 64 + 4
        vram.write8(0x1800 + (line >> 3) * 32, name)
        vram.write8(0x0000 + 0x0800 + name * 8 + 1, 0x3E)

        # Act
        dots = patterns.cell(vram.read8, held, "graphics2+multicolor", line, 0)

        # Assert
        self.assertEqual(dots, (3, 3, 3, 3, 14, 14, 14, 14))


class WidthTest(unittest.TestCase):
    def test_text_cells_are_six_wide_and_forty_to_a_line(self) -> None:
        # Arrange
        modes = ("text", "graphics1")

        # Act
        shapes = [(patterns.width(mode), patterns.cells(mode)) for mode in modes]

        # Assert
        self.assertEqual(shapes, [(6, 40), (8, 32)])


if __name__ == "__main__":
    unittest.main()

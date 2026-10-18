import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import random  # noqa: E402
import unittest  # noqa: E402
from typing import Any  # noqa: E402

import tms9918  # noqa: E402

SEED = 1982

DISPLAY = 0x40

M1 = 0x10

M2 = 0x08

M3 = 0x02

TEXT_WIDTH = 6

PATTERN_WIDTH = 8

TEXT_START = 6

NO_SPRITES = 0x3F80

TERMINATOR = 0xD0


def ready(registers: dict[int, int], writes: dict[int, int] | None = None) -> Any:
    part: Any = tms9918.Chip("tms9918a", tms9918.Vram(fill=0)).reset()
    part.read_status()
    for register, value in {5: NO_SPRITES >> 7, **registers}.items():
        part.write_control(value)
        part.write_control(0x80 | register)
    part.memory.write8(NO_SPRITES, TERMINATOR)
    for address, value in (writes or {}).items():
        part.memory.write8(address, value)
    return part


def run_to(part: Any, line: int, dot: int) -> Any:
    while (part.line, part.dot) != (line, dot):
        part.clock()
    return part


def colours(part: Any, count: int) -> tuple[int, ...]:
    seen: list[int] = []
    for _ in range(count):
        part.clock()
        seen.append(part.colour)
    return tuple(seen)


def cell(
    registers: dict[int, int], writes: dict[int, int], line: int, column: int
) -> tuple[int, ...]:
    text = bool(registers.get(1, 0) & M1)
    width = TEXT_WIDTH if text else PATTERN_WIDTH
    start = (TEXT_START if text else 0) + column * width
    return colours(run_to(ready(registers, writes), line, start), width)


def mode(r0: int, r1: int) -> str:
    part: Any = ready({0: r0, 1: r1})
    return str(part.mode)


def first_region(r1: int) -> str:
    part = run_to(ready({1: r1}), 0, 0)
    part.clock()
    return str(part.region)


def lit(r1: int, writes: dict[int, int]) -> tuple[int, int]:
    registers = {1: DISPLAY | r1, 2: 0x06, 3: 0x80, 4: 0x00, 7: 0xF4}
    part = run_to(ready(registers, writes), 0, 0)
    shown = colours(part, 256)
    found = [dot for dot, colour in enumerate(shown) if colour == 15]
    return (found[1] - found[0], len(found))


class ModeTest(unittest.TestCase):
    def test_the_four_documented_modes_follow_the_m1_m2_m3_table(self) -> None:
        # Arrange
        settings = {
            "graphics1": (0x00, 0x00),
            "graphics2": (M3, 0x00),
            "multicolor": (0x00, M2),
            "text": (0x00, M1),
        }

        # Act
        found = {name: mode(r0, r1) for name, (r0, r1) in settings.items()}

        # Assert
        self.assertEqual(found, {name: name for name in settings})

    def test_the_combinations_the_table_leaves_out_are_named_apart(self) -> None:
        # Arrange
        settings = [(0x00, M1 | M2), (M3, M2), (M3, M1), (M3, M1 | M2)]

        # Act
        found = [mode(r0, r1) for r0, r1 in settings]

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
        modes = (M1, M1 | M2, 0x00, M2)

        # Act
        found = [first_region(r1) for r1 in modes]

        # Assert
        self.assertEqual(found, ["border", "border", "active", "active"])


class GraphicsOneTest(unittest.TestCase):
    def test_a_cell_takes_its_bits_from_the_pattern_and_its_colours_from_the_group(
        self,
    ) -> None:
        # Arrange
        name = 0x41
        registers = {1: DISPLAY, 2: 0x06, 3: 0x80, 4: 0x00}
        writes = {
            0x1800 + 3 * 32 + 5: name,
            0x0000 + name * 8 + 2: 0b10110000,
            0x2000 + (name >> 3): 0x71,
        }

        # Act
        dots = cell(registers, writes, 3 * 8 + 2, 5)

        # Assert
        self.assertEqual(dots, (7, 1, 7, 7, 1, 1, 1, 1))


class GraphicsTwoTest(unittest.TestCase):
    def test_the_lower_third_reads_the_third_pattern_and_colour_block(self) -> None:
        # Arrange
        name = 0x10
        line = 128 + 8 * 2 + 6
        registers = {0: M3, 1: DISPLAY, 2: 0x0E, 3: 0xFF, 4: 0x03}
        writes = {
            0x3800 + (line >> 3) * 32 + 9: name,
            0x0000 + 0x1000 + name * 8 + 6: 0b00000001,
            0x2000 + 0x1000 + name * 8 + 6: 0xF4,
        }

        # Act
        dots = cell(registers, writes, line, 9)

        # Assert
        self.assertEqual(dots, (4, 4, 4, 4, 4, 4, 4, 15))

    def test_clear_low_bits_in_r4_fold_the_pattern_thirds_together(self) -> None:
        # Arrange
        name = 0x10
        line = 128
        registers = {0: M3, 1: DISPLAY, 2: 0x0E, 3: 0xFF, 4: 0x00}
        writes = {
            0x3800 + (line >> 3) * 32: name,
            0x0000 + name * 8: 0xFF,
            0x2000 + 0x1000 + name * 8: 0x50,
        }

        # Act
        dots = cell(registers, writes, line, 0)

        # Assert
        self.assertEqual(dots, (5,) * 8)


class MulticolorTest(unittest.TestCase):
    def test_each_name_row_reads_its_own_pair_of_bytes(self) -> None:
        # Arrange
        name = 0x20
        line = 8 * 1 + 4
        registers = {1: DISPLAY | M2, 2: 0x02, 4: 0x01}
        writes = {
            0x0800 + (line >> 3) * 32 + 2: name,
            0x0800 + name * 8 + 3: 0x9C,
        }

        # Act
        dots = cell(registers, writes, line, 2)

        # Assert
        self.assertEqual(dots, (9, 9, 9, 9, 12, 12, 12, 12))


class TextTest(unittest.TestCase):
    def test_a_cell_is_six_dots_in_the_two_register_7_colours(self) -> None:
        # Arrange
        name = random.Random(SEED).randrange(256)
        registers = {1: DISPLAY | M1, 2: 0x00, 4: 0x01, 7: 0xF4}
        writes = {
            0x0000 + 2 * 40 + 39: name,
            0x0800 + name * 8 + 1: 0b11000111,
        }

        # Act
        dots = cell(registers, writes, 2 * 8 + 1, 39)

        # Assert
        self.assertEqual(dots, (15, 15, 4, 4, 4, 15))


class UndocumentedTest(unittest.TestCase):
    def test_text_with_multicolor_draws_four_on_and_two_off(self) -> None:
        # Arrange
        registers = {1: DISPLAY | M1 | M2, 7: 0x6A}

        # Act
        dots = cell(registers, {}, 0, 0)

        # Assert
        self.assertEqual(dots, (6, 6, 6, 6, 10, 10))

    def test_text_with_graphics_two_reads_the_masked_third(self) -> None:
        # Arrange
        name = 0x02
        line = 64
        registers = {0: M3, 1: DISPLAY | M1, 2: 0x00, 3: 0xFF, 4: 0x03, 7: 0xF0}
        writes = {
            0x0000 + (line >> 3) * 40: name,
            0x0000 + 0x0800 + name * 8: 0b10000000,
        }

        # Act
        dots = cell(registers, writes, line, 0)

        # Assert
        self.assertEqual(dots, (15, 1, 1, 1, 1, 1))

    def test_graphics_two_with_multicolor_reads_colours_through_the_thirds(
        self,
    ) -> None:
        # Arrange
        name = 0x01
        line = 64 + 4
        registers = {0: M3, 1: DISPLAY | M2, 2: 0x06, 3: 0xFF, 4: 0x03}
        writes = {
            0x1800 + (line >> 3) * 32: name,
            0x0000 + 0x0800 + name * 8 + 1: 0x3E,
        }

        # Act
        dots = cell(registers, writes, line, 0)

        # Assert
        self.assertEqual(dots, (3, 3, 3, 3, 14, 14, 14, 14))


class WidthTest(unittest.TestCase):
    def test_text_cells_are_six_wide_and_forty_to_a_line(self) -> None:
        # Arrange
        first_rows = {0x0000: 0x80, 0x2000: 0xF4}

        # Act
        shapes = [lit(M1, first_rows), lit(0x00, first_rows)]

        # Assert
        self.assertEqual(shapes, [(6, 40), (8, 32)])


if __name__ == "__main__":
    unittest.main()

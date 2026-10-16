import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import unittest  # noqa: E402

from tms9918 import sprites  # noqa: E402
from tms9918.memory import Vram  # noqa: E402

ATTRIBUTES = 0x1B00

GENERATOR = 0x3800


def registers(r1: int = 0x40) -> bytearray:
    held = bytearray(8)
    held[1] = r1
    held[5] = ATTRIBUTES >> 7
    held[6] = GENERATOR >> 11
    return held


def place(vram: Vram, plane: int, entry: tuple[int, int, int, int]) -> None:
    for offset, value in enumerate(entry):
        vram.write8(ATTRIBUTES + plane * 4 + offset, value)


def terminate(vram: Vram, plane: int) -> None:
    vram.write8(ATTRIBUTES + plane * 4, 0xD0)


class EvaluationTest(unittest.TestCase):
    def test_a_vertical_position_of_minus_one_starts_on_the_top_line(self) -> None:
        # Arrange
        vram = Vram(fill=0)
        place(vram, 0, (0xFF, 10, 0, 0x0F))
        terminate(vram, 1)

        # Act
        found = sprites.evaluate(vram.read8, registers(), 0)

        # Assert
        self.assertEqual([one.plane for one in found.shown], [0])

    def test_the_terminator_stops_the_scan_at_its_plane(self) -> None:
        # Arrange
        vram = Vram(fill=0)
        place(vram, 0, (0xFF, 0, 0, 1))
        terminate(vram, 1)
        place(vram, 2, (0xFF, 0, 0, 1))

        # Act
        found = sprites.evaluate(vram.read8, registers(), 0)

        # Assert
        self.assertEqual(([one.plane for one in found.shown], found.last), ([0], 1))

    def test_a_fifth_sprite_on_a_line_is_reported_and_not_shown(self) -> None:
        # Arrange
        vram = Vram(fill=0)
        for plane in range(6):
            place(vram, plane, (49, plane * 20, 0, 2))
        terminate(vram, 6)

        # Act
        found = sprites.evaluate(vram.read8, registers(), 50)

        # Assert
        self.assertEqual(([one.plane for one in found.shown], found.fifth), ([0, 1, 2, 3], 4))

    def test_with_no_terminator_the_last_plane_examined_is_31(self) -> None:
        # Arrange
        vram = Vram(fill=0)
        for plane in range(32):
            place(vram, plane, (100, 0, 0, 0))

        # Act
        found = sprites.evaluate(vram.read8, registers(), 0)

        # Assert
        self.assertEqual((found.shown, found.fifth, found.last), ((), None, 31))

    def test_positions_from_e1_upward_are_negative(self) -> None:
        # Arrange
        vram = Vram(fill=0)
        place(vram, 0, (0xE1, 0, 0, 1))
        terminate(vram, 1)

        # Act
        found = sprites.evaluate(vram.read8, registers(r1=0x43), 1)

        # Assert
        self.assertEqual([one.row for one in found.shown], [15])

    def test_a_magnified_sprite_covers_twice_the_lines(self) -> None:
        # Arrange
        vram = Vram(fill=0)
        place(vram, 0, (9, 0, 0, 1))
        terminate(vram, 1)

        # Act
        rows = [sprites.evaluate(vram.read8, registers(r1=0x41), line).shown for line in (25, 26)]

        # Assert
        self.assertEqual([[one.row for one in shown] for shown in rows], [[7], []])


class PatternTest(unittest.TestCase):
    def test_a_size_one_sprite_reads_its_right_half_sixteen_bytes_on(self) -> None:
        # Arrange
        vram = Vram(fill=0)
        place(vram, 0, (0xFF, 0, 0x07, 1))
        terminate(vram, 1)
        vram.write8(GENERATOR + 0x04 * 8 + 3, 0xAA)
        vram.write8(GENERATOR + 0x04 * 8 + 16 + 3, 0x55)

        # Act
        found = sprites.evaluate(vram.read8, registers(r1=0x42), 3)

        # Assert
        self.assertEqual(found.shown[0].bits, (0xAA, 0x55))

    def test_the_early_clock_bit_moves_a_sprite_32_dots_left(self) -> None:
        # Arrange
        vram = Vram(fill=0)
        place(vram, 0, (0xFF, 40, 0, 0x85))
        terminate(vram, 1)

        # Act
        found = sprites.evaluate(vram.read8, registers(), 0)

        # Assert
        self.assertEqual((found.shown[0].x, found.shown[0].colour), (8, 5))


class LineTest(unittest.TestCase):
    def test_the_lower_plane_number_wins_where_two_sprites_meet(self) -> None:
        # Arrange
        vram = Vram(fill=0)
        place(vram, 0, (0xFF, 4, 0, 6))
        place(vram, 1, (0xFF, 0, 1, 9))
        terminate(vram, 2)
        vram.write8(GENERATOR + 0, 0x80)
        vram.write8(GENERATOR + 8, 0xFF)
        found = sprites.evaluate(vram.read8, registers(), 0)

        # Act
        drawn = sprites.draw(found.shown, magnified=False)

        # Assert
        self.assertEqual(drawn.colours[:9], [9, 9, 9, 9, 6, 9, 9, 9, None])
        self.assertEqual(drawn.collision, 4)

    def test_a_transparent_sprite_still_collides_but_shows_what_is_behind(self) -> None:
        # Arrange
        vram = Vram(fill=0)
        place(vram, 0, (0xFF, 0, 0, 0))
        place(vram, 1, (0xFF, 0, 0, 3))
        terminate(vram, 2)
        vram.write8(GENERATOR + 0, 0x01)
        found = sprites.evaluate(vram.read8, registers(), 0)

        # Act
        drawn = sprites.draw(found.shown, magnified=False)

        # Assert
        self.assertEqual((drawn.colours[7], drawn.collision), (3, 7))

    def test_dots_beyond_the_active_area_neither_show_nor_collide(self) -> None:
        # Arrange
        vram = Vram(fill=0)
        place(vram, 0, (0xFF, 252, 0, 2))
        place(vram, 1, (0xFF, 0, 0, 0x82))
        terminate(vram, 2)
        vram.write8(GENERATOR + 0, 0xFF)
        found = sprites.evaluate(vram.read8, registers(), 0)

        # Act
        drawn = sprites.draw(found.shown, magnified=False)

        # Assert
        self.assertEqual((drawn.colours[252:], drawn.collision), ([2, 2, 2, 2], None))

    def test_a_magnified_bit_covers_two_dots(self) -> None:
        # Arrange
        vram = Vram(fill=0)
        place(vram, 0, (0xFF, 0, 0, 7))
        terminate(vram, 1)
        vram.write8(GENERATOR + 0, 0x40)
        found = sprites.evaluate(vram.read8, registers(r1=0x41), 0)

        # Act
        drawn = sprites.draw(found.shown, magnified=True)

        # Assert
        self.assertEqual(drawn.colours[:5], [None, None, 7, 7, None])


if __name__ == "__main__":
    unittest.main()

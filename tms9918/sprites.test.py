import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import unittest  # noqa: E402
from typing import Any  # noqa: E402

import tms9918  # noqa: E402

ATTRIBUTES = 0x1B00

GENERATOR = 0x3800

DISPLAY = 0x40

SIZE = 0x02

MAGNIFY = 0x01

BACKDROP = 4

FIFTH = 0x40

COINCIDENCE = 0x20

NUMBER = 0x1F

TERMINATOR = (0xD0, 0, 0, 0)

Entry = tuple[int, int, int, int]


def ready(r1: int, entries: list[Entry], rows: dict[int, int]) -> Any:
    part: Any = tms9918.Chip("tms9918a", tms9918.Vram(fill=0)).reset()
    part.read_status()
    registers = {
        1: r1,
        2: 0x06,
        3: 0x80,
        4: 0x00,
        5: ATTRIBUTES >> 7,
        6: GENERATOR >> 11,
        7: BACKDROP,
    }
    for register, value in registers.items():
        part.write_control(value)
        part.write_control(0x80 | register)
    for plane, entry in enumerate(entries):
        for offset, value in enumerate(entry):
            part.memory.write8(ATTRIBUTES + plane * 4 + offset, value)
    for offset, value in rows.items():
        part.memory.write8(GENERATOR + offset, value)
    return part


def drawn(
    entries: list[Entry], rows: dict[int, int], line: int, r1: int = DISPLAY
) -> tuple[dict[int, int], int]:
    part = ready(r1, entries, rows)
    while (part.line, part.dot) != (line, 0):
        part.clock()
    shown: dict[int, int] = {}
    for dot in range(256):
        part.clock()
        if part.colour != BACKDROP:
            shown[dot] = part.colour
    return (shown, part.status)


class EvaluationTest(unittest.TestCase):
    def test_a_vertical_position_of_minus_one_starts_on_the_top_line(self) -> None:
        # Arrange
        entries = [(0xFF, 10, 0, 0x0F), TERMINATOR]

        # Act
        shown, _ = drawn(entries, {0: 0xFF}, 0)

        # Assert
        self.assertEqual(shown, dict.fromkeys(range(10, 18), 15))

    def test_the_terminator_stops_the_scan_at_its_plane(self) -> None:
        # Arrange
        entries = [(0xFF, 0, 0, 2), TERMINATOR, (0xFF, 40, 0, 3)]

        # Act
        shown, status = drawn(entries, {0: 0xFF}, 0)

        # Assert
        self.assertEqual((shown, status & NUMBER), (dict.fromkeys(range(8), 2), 1))

    def test_a_fifth_sprite_on_a_line_is_reported_and_not_shown(self) -> None:
        # Arrange
        entries = [(49, plane * 20, 0, 2) for plane in range(6)] + [TERMINATOR]

        # Act
        shown, status = drawn(entries, {0: 0x80}, 50)

        # Assert
        self.assertEqual(
            (shown, status & (FIFTH | NUMBER)),
            (dict.fromkeys((0, 20, 40, 60), 2), FIFTH | 4),
        )

    def test_with_no_terminator_the_last_plane_examined_is_31(self) -> None:
        # Arrange
        entries = [(100, 0, 0, 2)] * 32

        # Act
        shown, status = drawn(entries, {0: 0xFF}, 0)

        # Assert
        self.assertEqual((shown, status & (FIFTH | NUMBER)), ({}, 31))

    def test_positions_from_e1_upward_are_negative(self) -> None:
        # Arrange
        entries = [(0xE1, 0, 0, 2), TERMINATOR]

        # Act
        shown, _ = drawn(entries, {15: 0x80}, 1, DISPLAY | SIZE | MAGNIFY)

        # Assert
        self.assertEqual(shown, {0: 2, 1: 2})

    def test_a_magnified_sprite_covers_twice_the_lines(self) -> None:
        # Arrange
        entries = [(9, 0, 0, 2), TERMINATOR]

        # Act
        rows = [drawn(entries, {7: 0x80}, line, DISPLAY | MAGNIFY)[0] for line in (25, 26)]

        # Assert
        self.assertEqual(rows, [{0: 2, 1: 2}, {}])


class PatternTest(unittest.TestCase):
    def test_a_size_one_sprite_reads_its_right_half_sixteen_bytes_on(self) -> None:
        # Arrange
        entries = [(0xFF, 0, 0x07, 2), TERMINATOR]
        rows = {0x04 * 8 + 3: 0xAA, 0x04 * 8 + 16 + 3: 0x55}

        # Act
        shown, _ = drawn(entries, rows, 3, DISPLAY | SIZE)

        # Assert
        self.assertEqual(shown, dict.fromkeys((0, 2, 4, 6, 9, 11, 13, 15), 2))

    def test_the_early_clock_bit_moves_a_sprite_32_dots_left(self) -> None:
        # Arrange
        entries = [(0xFF, 40, 0, 0x85), TERMINATOR]

        # Act
        shown, _ = drawn(entries, {0: 0xFF}, 0)

        # Assert
        self.assertEqual(shown, dict.fromkeys(range(8, 16), 5))


class LineTest(unittest.TestCase):
    def test_the_lower_plane_number_wins_where_two_sprites_meet(self) -> None:
        # Arrange
        entries = [(0xFF, 4, 0, 6), (0xFF, 0, 1, 9), TERMINATOR]
        rows = {0: 0x80, 8: 0xFF}

        # Act
        shown, status = drawn(entries, rows, 0)

        # Assert
        self.assertEqual(shown, {0: 9, 1: 9, 2: 9, 3: 9, 4: 6, 5: 9, 6: 9, 7: 9})
        self.assertEqual(status & COINCIDENCE, COINCIDENCE)

    def test_a_transparent_sprite_still_collides_but_shows_what_is_behind(self) -> None:
        # Arrange
        entries = [(0xFF, 0, 0, 0), (0xFF, 0, 0, 3), TERMINATOR]

        # Act
        shown, status = drawn(entries, {0: 0x01}, 0)

        # Assert
        self.assertEqual((shown, status & COINCIDENCE), ({7: 3}, COINCIDENCE))

    def test_dots_beyond_the_active_area_neither_show_nor_collide(self) -> None:
        # Arrange
        entries = [(0xFF, 252, 0, 2), (0xFF, 0, 0, 0x82), TERMINATOR]

        # Act
        shown, status = drawn(entries, {0: 0xFF}, 0)

        # Assert
        self.assertEqual((shown, status & COINCIDENCE), (dict.fromkeys(range(252, 256), 2), 0))

    def test_a_magnified_bit_covers_two_dots(self) -> None:
        # Arrange
        entries = [(0xFF, 0, 0, 7), TERMINATOR]

        # Act
        shown, _ = drawn(entries, {0: 0x40}, 0, DISPLAY | MAGNIFY)

        # Assert
        self.assertEqual(shown, {2: 7, 3: 7})


if __name__ == "__main__":
    unittest.main()

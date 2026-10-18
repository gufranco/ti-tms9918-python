import re
import sys
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import tms9918  # noqa: E402
from conformance.bench import chip, colour_at, dots_until, program, quotes, value  # noqa: E402

BLACK = 1

WHITE = 15

BACKDROP = 4

FIFTH = 0x40

NUMBER = 0x1F

INTERRUPT_ENABLE = 0x20

MAGNIFY = 0x01

ATTRIBUTES = 0x1B00

SPRITE_PATTERNS = 0x3800

NO_SPRITES = 0x3F80

TEXT = 0x10

MULTICOLOR = 0x08

ACTIVE_LINES = 192

ACTIVE_DOTS = 256

TEXT_START = 6

Planes = list[tuple[int, int, int]]


def ready(registers: dict[int, int], writes: dict[int, int]) -> Any:
    part = program(chip(), {5: NO_SPRITES >> 7, **registers})
    part.memory.write8(NO_SPRITES, value("terminator"))
    for address, held in writes.items():
        part.memory.write8(address, held)
    return part


def with_sprites(registers: dict[int, int], planes: Planes, pattern: int = 0xFF) -> Any:
    tables = {2: 0x06, 3: 0x80, 4: 0x00, 7: BACKDROP}
    sprites = {5: ATTRIBUTES >> 7, 6: SPRITE_PATTERNS >> 11}
    part = program(chip(), {**tables, **sprites, **registers})
    for plane, (y, x, colour) in enumerate(planes):
        for offset, held in enumerate((y, x, 0, colour)):
            part.memory.write8(ATTRIBUTES + plane * 4 + offset, held)
    part.memory.write8(ATTRIBUTES + len(planes) * 4, value("terminator"))
    part.memory.write8(SPRITE_PATTERNS, pattern)
    return part


def shown_on(part: Any, line: int) -> dict[int, int]:
    dots_until(part, line, 0)
    found: dict[int, int] = {}
    for dot in range(ACTIVE_DOTS):
        part.clock()
        if part.colour != BACKDROP:
            found[dot] = part.colour
    return found


def drawn(planes: Planes, line: int, r1: int = 0x40, pattern: int = 0xFF) -> dict[int, int]:
    return shown_on(with_sprites({1: r1}, planes, pattern), line)


def collided() -> Any:
    part = with_sprites({1: value("blank")}, [(9, 40, 15), (9, 44, 15)])
    return dots_until(part, 10, 50)


def mode_with(bits: list[int]) -> str:
    r1 = value("blank") | bits[0] * TEXT | bits[1] * MULTICOLOR
    part = program(chip(), {0: bits[2] * 0x02, 1: r1})
    return str(part.mode)


def lit_text(writes: dict[int, int]) -> list[tuple[int, int]]:
    part = ready({1: value("blank") | TEXT, 2: 0, 4: 1, 7: WHITE << 4 | BLACK}, writes)
    dots_until(part, 0, 0)
    found: list[tuple[int, int]] = []
    while (part.line, part.dot) != (ACTIVE_LINES, 0):
        line, dot = part.line, part.dot
        part.clock()
        if part.colour == WHITE:
            found = [*found, (line, dot)]
    return found


def run_of(part: Any, line: int, dot: int, count: int) -> tuple[int, ...]:
    dots_until(part, line, dot)
    seen: list[int] = []
    for _ in range(count):
        part.clock()
        seen = [*seen, part.colour]
    return tuple(seen)


def counted(sentence: str, pattern: str) -> list[float]:
    return [float(one) for one in re.findall(pattern, sentence)]


class TableTest(unittest.TestCase):
    def test_each_base_register_scales_by_the_factor_printed(self) -> None:
        # Arrange
        bases = value("tableBases")
        writes = {bases["2"]: 1, bases["4"] + 8: 0x80, bases["3"]: WHITE << 4}
        part = ready({1: value("blank"), 2: 1, 3: 1, 4: 1, 7: BACKDROP}, writes)

        # Act
        shown = run_of(part, 0, 0, 2)

        # Assert
        self.assertEqual(shown, (WHITE, BACKDROP))

    def test_the_sprite_tables_scale_by_the_factors_printed(self) -> None:
        # Arrange
        bases = value("tableBases")
        entry = (value("spriteTop") & 0xFF, 0, 0, WHITE, value("terminator"))
        writes = {bases["5"] + offset: held for offset, held in enumerate(entry)}
        registers = {1: value("blank"), 2: 0x06, 3: 0x80, 4: 0, 5: 1, 6: 1, 7: BACKDROP}
        part = program(chip(), registers)
        for address, held in {**writes, bases["6"]: 0x80}.items():
            part.memory.write8(address, held)

        # Act
        shown = run_of(part, 0, 0, 2)

        # Assert
        self.assertEqual(shown, (WHITE, BACKDROP))

    def test_text_has_the_grid_the_manual_prints(self) -> None:
        # Arrange
        printed = value("text")

        # Act
        lit = lit_text({0x0800: 0x80})

        # Assert
        lines = sorted({line for line, _ in lit})
        dots = sorted({dot for _, dot in lit})
        held = {"columns": len(dots), "rows": len(lines), "width": dots[1] - dots[0]}
        self.assertEqual(held, printed)

    def test_a_text_cell_drops_the_two_low_bits_and_a_row_holds_the_printed_columns(
        self,
    ) -> None:
        # Arrange
        printed = value("text")
        writes = {printed["columns"]: 1, 0x0800 + 8: 0xFF}

        # Act
        lit = lit_text(writes)

        # Assert
        start = TEXT_START
        self.assertEqual(lit, [(8, dot) for dot in range(start, start + printed["width"])])

    def test_the_second_row_of_multicolor_names_reads_bytes_three_and_four(
        self,
    ) -> None:
        # Arrange
        writes = {0x0800 + byte: (byte + 1) << 4 | 0x0F for byte in range(8)}
        registers = {1: value("blank") | MULTICOLOR, 2: 0, 4: 1, 7: BACKDROP}

        # Act
        read = [colour_at(ready(registers, writes), line, 0) for line in (8, 12)]

        # Assert
        self.assertEqual(read, value("multicolor")["secondNameRowBytes"])

    def test_the_mode_bits_select_the_modes_printed(self) -> None:
        # Arrange
        printed = {"graphics1": value("graphicsOne"), "graphics2": value("graphicsTwo")}

        # Act
        held = {name: mode_with(bits) for name, bits in printed.items()}

        # Assert
        self.assertEqual(held, {name: name for name in printed})

    def test_graphics_two_reads_a_third_of_256_patterns_from_the_half_register_4_names(
        self,
    ) -> None:
        # Arrange
        bits = value("graphicsTwo")
        halves = {0x03: 0, 0x07: 0x2000}
        colours = {third: 0x2000 + third * 256 * 8 for third in range(3)}

        # Act
        shown = {
            base: [
                colour_at(
                    ready(
                        {0: bits[2] * 0x02, 1: value("blank"), 2: 0x0E, 3: 0xFF, 4: base},
                        {half + third * 256 * 8: 0xF4, colours[third]: 0xF4},
                    ),
                    third * 64,
                    0,
                )
                for third in range(3)
            ]
            for base, half in halves.items()
        }

        # Assert
        self.assertEqual(shown, dict.fromkeys(halves, [WHITE] * 3))


class ColourTest(unittest.TestCase):
    def test_register_7_gives_text_its_two_colours_and_every_mode_its_backdrop(self) -> None:
        # Arrange
        part = program(chip(), {1: 0x50, 2: 0, 4: 1, 7: 0x24})
        part.memory.write8(0x0800, 0x80)

        # Act
        shown = [colour_at(part, 0, dot) for dot in (6, 7, 260)]

        # Assert
        self.assertEqual(shown, [2, 4, 4], value("register7"))

    def test_the_tables_carry_the_printed_number_of_colours_from_black_to_white(self) -> None:
        # Arrange
        printed = quotes("colourLevels")
        count = counted(printed[0], r"(\d+) colors")[0]
        black, white = counted(printed[1], r"(\d\.\d\d) being")

        # Act
        held = {
            name: (len(table), table[BLACK][0], table[WHITE][0])
            for name, table in (
                ("composite", tms9918.COMPOSITE),
                ("difference", tms9918.DIFFERENCE),
            )
        }

        # Assert
        self.assertEqual(held, dict.fromkeys(held, (count, black, white)), value("colourLevels"))

    def test_blanking_shows_the_border_colour_where_a_pattern_would_be(self) -> None:
        # Arrange
        printed = value("blank")
        parts = {
            bits: program(chip(), {1: bits, 2: 6, 3: 0x80, 4: 0, 7: 4}) for bits in (printed, 0)
        }
        for part in parts.values():
            for address, byte in ((0x1800, 0x01), (0x0008, 0x80), (0x2000, 0xF0)):
                part.memory.write8(address, byte)

        # Act
        shown = {bits: colour_at(part, 0, 0) for bits, part in parts.items()}

        # Assert
        self.assertEqual(shown, {printed: 15, 0: 4})

    def test_a_transparent_backdrop_is_black_or_the_external_video(self) -> None:
        # Arrange
        enables = (0, value("externalVideo"))
        parts = [program(chip(), {0: bits, 1: 0x40, 7: 0}) for bits in enables]

        # Act
        shown = [colour_at(part, 0, 260) for part in parts]

        # Assert
        self.assertEqual(shown, [BLACK, tms9918.EXTERNAL], value("transparentBackdrop"))


class SpriteTest(unittest.TestCase):
    def test_a_position_of_minus_one_reaches_the_top_line(self) -> None:
        # Arrange
        printed = value("spriteTop")

        # Act
        shown = drawn([(printed & 0xFF, 40, 2)], 0)

        # Assert
        self.assertEqual(shown, dict.fromkeys(range(40, 48), 2))

    def test_only_the_printed_number_of_sprites_show_on_a_line(self) -> None:
        # Arrange
        printed = value("fourPerLine")
        part = with_sprites({1: 0x40}, [(9, 20 * n, 2) for n in range(printed + 1)], 0x80)

        # Act
        shown = shown_on(part, 10)

        # Assert
        self.assertEqual(
            (sorted(shown), part.status & (FIFTH | NUMBER)),
            ([20 * n for n in range(printed)], FIFTH | printed),
        )

    def test_the_early_clock_bit_moves_a_sprite_left_by_the_printed_dots(self) -> None:
        # Arrange
        early = 0x80

        # Act
        shown = drawn([(9, 40, early | 2)], 10, pattern=0x80)

        # Assert
        self.assertEqual(shown, {40 - value("earlyClock"): 2})

    def test_two_sprites_meeting_set_the_flag_a_status_read_clears(self) -> None:
        # Arrange
        printed = value("coincidence")
        part = collided()

        # Act
        read = part.read_status()

        # Assert
        self.assertEqual((read & printed, part.status & printed), (printed, 0))

    def test_a_reset_clears_the_coincidence_flag(self) -> None:
        # Arrange
        printed = value("coincidence")
        part = collided()

        # Act
        part.reset()

        # Assert
        self.assertEqual(part.status & printed, 0)

    def test_a_fifth_sprite_sets_its_flag_without_an_interrupt(self) -> None:
        # Arrange
        enabled = {1: value("blank") | INTERRUPT_ENABLE}
        part = with_sprites(enabled, [(29, 20 * n, 15) for n in range(5)])

        # Act
        dots_until(part, 30, 0)

        # Assert
        self.assertEqual(
            (part.status & FIFTH, part.interrupt),
            (FIFTH, not value("fifthSpriteNoInterrupt")),
        )

    def test_plane_0_shows_in_front_of_plane_1(self) -> None:
        # Arrange
        planes = [(9, 40, 2), (9, 40, 3)]

        # Act
        shown = drawn(planes, 10)

        # Assert
        self.assertEqual(shown, dict.fromkeys(range(40, 48), 2), value("planePriority"))

    def test_text_mode_draws_no_sprite(self) -> None:
        # Arrange
        registers = {1: 0x50, 2: 0, 4: 1, 7: 0x24}
        part = with_sprites(registers, [(9, 40, 15), (9, 40, 15)])

        # Act
        shown = colour_at(part, 10, 44)

        # Assert
        self.assertEqual(
            (shown == 4, part.status & value("coincidence")), (value("noSpritesInText"), 0)
        )

    def test_no_plane_after_the_terminator_is_shown(self) -> None:
        # Arrange
        part = with_sprites({1: 0x40}, [(value("terminator"), 0, 2), (9, 40, 3)])

        # Act
        shown = shown_on(part, 10)

        # Assert
        self.assertEqual((shown, part.status & NUMBER), ({}, 0))

    def test_a_magnified_bit_covers_the_printed_square_of_dots(self) -> None:
        # Arrange
        part = with_sprites({1: 0x40 | MAGNIFY}, [(9, 40, 2)], 0x80)

        # Act
        rows = [shown_on(part, line) for line in range(10, 14)]

        # Assert
        counts = [len(one) for one in rows]
        self.assertEqual((sum(map(bool, counts)), max(counts)), (value("magnification"),) * 2)


if __name__ == "__main__":
    unittest.main()

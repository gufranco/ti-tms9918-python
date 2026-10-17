import re
import sys
import unittest
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from conformance.bench import chip, colour_at, dots_until, program, quotes, value  # noqa: E402
from tms9918 import core, geometry, levels, patterns, sprites  # noqa: E402
from tms9918.memory import Vram  # noqa: E402

BLACK = 1

WHITE = 15

FIFTH = 0x40

ATTRIBUTES = 0x1B00

SPRITE_PATTERNS = 0x3800

Planes = list[tuple[int, int, int]]


def addresses_read(held: bytearray, mode: str, line: int, column: int) -> list[int]:
    seen: list[int] = []

    def read(address: int) -> int:
        seen.append(address)
        return 0

    patterns.cell(read, held, mode, line, column)
    return seen


def with_sprites(registers: dict[int, int], planes: Planes) -> core.Chip:
    part = program(chip(), {5: ATTRIBUTES >> 7, 6: SPRITE_PATTERNS >> 11, **registers})
    for plane, (y, x, colour) in enumerate(planes):
        for offset, held in enumerate((y, x, 0, colour)):
            part.memory.write8(ATTRIBUTES + plane * 4 + offset, held)
    part.memory.write8(ATTRIBUTES + len(planes) * 4, sprites.TERMINATOR)
    part.memory.write8(SPRITE_PATTERNS, 0xFF)
    return part


def sprite_memory(planes: Planes, pattern: int) -> Callable[[int], int]:
    held = Vram(fill=0)
    for plane, (y, x, colour) in enumerate(planes):
        for offset, one in enumerate((y, x, 0, colour)):
            held.write8(plane * 4 + offset, one)
    held.write8(SPRITE_PATTERNS, pattern)
    return held.read8


def sprite_registers(magnified: bool) -> bytearray:
    held = bytearray(8)
    held[1] = core.BLANK | (core.MAGNIFY if magnified else 0)
    held[6] = SPRITE_PATTERNS >> 11
    return held


def collided() -> core.Chip:
    part = with_sprites({1: core.BLANK}, [(9, 40, 15), (9, 44, 15)])
    return dots_until(part, 10, 50)


def mode_with(bits: list[int]) -> str:
    return patterns.mode_of(bits[2] * patterns.M3, bits[0] * patterns.M1 | bits[1] * patterns.M2)


def counted(sentence: str, pattern: str) -> list[float]:
    return [float(one) for one in re.findall(pattern, sentence)]


class TableTest(unittest.TestCase):
    def test_each_base_register_scales_by_the_factor_printed(self) -> None:
        # Arrange
        held = bytearray(8)
        held[2], held[3], held[4] = 1, 1, 1

        # Act
        name, pattern, colour = addresses_read(held, "graphics1", 0, 0)

        # Assert
        bases = value("tableBases")
        self.assertEqual((name, pattern, colour), (bases["2"], bases["4"], bases["3"]))

    def test_the_sprite_tables_scale_by_the_factors_printed(self) -> None:
        # Arrange
        held = bytearray(8)
        held[1], held[5], held[6] = 0x40, 1, 1
        seen: list[int] = []

        def read(address: int) -> int:
            seen.append(address)
            return 0xFF if not seen[:-1] else 0

        # Act
        sprites.evaluate(read, held, 0)

        # Assert
        bases = value("tableBases")
        self.assertEqual((seen[0], seen[4]), (bases["5"], bases["6"]))

    def test_text_has_the_grid_the_manual_prints(self) -> None:
        # Arrange
        printed = value("text")

        # Act
        held = {
            "columns": patterns.TEXT_COLUMNS,
            "rows": geometry.ACTIVE_LINES // 8,
            "width": patterns.TEXT_WIDTH,
        }

        # Assert
        self.assertEqual(held, printed)

    def test_a_text_cell_drops_the_two_low_bits_and_a_row_holds_the_printed_columns(
        self,
    ) -> None:
        # Arrange
        printed = value("text")
        held = bytearray(8)
        held[7] = WHITE << 4 | BLACK

        # Act
        cell = patterns.cell(lambda _: 0xFF, held, "text", 0, 0)
        name = addresses_read(held, "text", 8, 0)[0]

        # Assert
        self.assertEqual((cell, name), ((WHITE,) * printed["width"], printed["columns"]))

    def test_the_second_row_of_multicolor_names_reads_bytes_three_and_four(
        self,
    ) -> None:
        # Arrange
        held = bytearray(8)

        # Act
        read = [addresses_read(held, "multicolor", line, 0)[1] for line in (8, 12)]

        # Assert
        self.assertEqual([one + 1 for one in read], value("multicolor")["secondNameRowBytes"])

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
        mode = mode_with(value("graphicsTwo"))
        held = {base: bytearray([0, 0, 0, 0xFF, base, 0, 0, 0]) for base in (0x03, 0x07)}

        # Act
        read = [
            addresses_read(held[base], mode, line, 0)[1] for base in held for line in (0, 64, 128)
        ]

        # Assert
        self.assertEqual(
            read, [half + third * 256 * 8 for half in (0, 0x2000) for third in range(3)]
        )


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
            for name, table in (("composite", levels.COMPOSITE), ("difference", levels.DIFFERENCE))
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
        self.assertEqual(shown, [BLACK, core.EXTERNAL], value("transparentBackdrop"))


class SpriteTest(unittest.TestCase):
    def test_the_sprite_constants_are_the_ones_printed(self) -> None:
        # Arrange
        printed = (value("fourPerLine"), value("terminator"), value("earlyClock"))

        # Act
        held = (sprites.SHOWN_PER_LINE, sprites.TERMINATOR, sprites.EARLY_SHIFT)

        # Assert
        self.assertEqual(held, printed)

    def test_a_position_of_minus_one_reaches_the_top_line(self) -> None:
        # Arrange
        printed = value("spriteTop")

        # Act
        top = sprites._top(printed & 0xFF)

        # Assert
        self.assertEqual(top, 0)

    def test_only_the_printed_number_of_sprites_show_on_a_line(self) -> None:
        # Arrange
        printed = value("fourPerLine")
        read = sprite_memory([(9, 20 * n, 2) for n in range(printed + 1)], 0xFF)

        # Act
        found = sprites.evaluate(read, sprite_registers(False), 10)

        # Assert
        self.assertEqual((len(found.shown), found.fifth), (printed, printed))

    def test_the_early_clock_bit_moves_a_sprite_left_by_the_printed_dots(self) -> None:
        # Arrange
        read = sprite_memory([(9, 40, sprites.EARLY_CLOCK | 2)], 0xFF)

        # Act
        found = sprites.evaluate(read, sprite_registers(False), 10)

        # Assert
        self.assertEqual(found.shown[0].x, 40 - value("earlyClock"))

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
        enabled = {1: core.BLANK | core.INTERRUPT_ENABLE}
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
        read = sprite_memory([(9, 40, 2), (9, 40, 3), (sprites.TERMINATOR, 0, 0)], 0xFF)
        found = sprites.evaluate(read, sprite_registers(False), 10)

        # Act
        drawn = sprites.draw(found.shown, False)

        # Assert
        self.assertEqual(drawn.colours[40], 2, value("planePriority"))

    def test_text_mode_draws_no_sprite(self) -> None:
        # Arrange
        registers = {1: 0x50, 2: 0, 4: 1, 7: 0x24}
        part = with_sprites(registers, [(9, 40, 15)])

        # Act
        shown = colour_at(part, 10, 44)

        # Assert
        self.assertEqual((shown == 4, part.drawn), (value("noSpritesInText"), None))

    def test_no_plane_after_the_terminator_is_shown(self) -> None:
        # Arrange
        read = sprite_memory([(value("terminator"), 0, 2), (9, 40, 3)], 0xFF)

        # Act
        found = sprites.evaluate(read, sprite_registers(False), 10)

        # Assert
        self.assertEqual((found.shown, found.last), ((), 0))

    def test_a_magnified_bit_covers_the_printed_square_of_dots(self) -> None:
        # Arrange
        read = sprite_memory([(9, 40, 2), (sprites.TERMINATOR, 0, 0)], 0x80)
        held = sprite_registers(True)

        # Act
        drawn = [
            sprites.draw(sprites.evaluate(read, held, line).shown, True) for line in range(10, 14)
        ]

        # Assert
        counts = [one.colours.count(2) for one in drawn]
        self.assertEqual((sum(map(bool, counts)), max(counts)), (value("magnification"),) * 2)


if __name__ == "__main__":
    unittest.main()

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import random  # noqa: E402
import unittest  # noqa: E402

import tms9918  # noqa: E402
from tms9918 import core, slots  # noqa: E402
from tms9918.memory import Vram  # noqa: E402

SEED = 1982

MASTER_HZ = 10_738_635

LINE = 342


def chip(model: str = "tms9918a", fill: int = 0) -> core.Chip:
    built = tms9918.Chip(model, Vram(fill=fill))
    built.reset()
    built.read_status()
    return built


def program(part: core.Chip, values: dict[int, int]) -> None:
    for register, value in values.items():
        part.write_control(value)
        part.write_control(0x80 | register)


def dots_until(part: core.Chip, line: int, dot: int) -> int:
    count = 0
    while (part.line, part.dot) != (line, dot):
        part.clock()
        count += 1
    return count


def ticks_to_land(registers: dict[int, int]) -> int:
    part = chip()
    program(part, registers)
    dots_until(part, 100, 40)
    part.write_control(0x00)
    part.write_control(0x40)
    part.write_data(0xAB)
    waited = 0
    while part.memory.read8(0) != 0xAB:
        part.tick()
        waited += 1
    return waited


def frame_flag_period(part: core.Chip) -> int:
    dots_until(part, 192, 0)
    part.read_status()
    part.clock()
    count = 1
    while not part.status & 0x80:
        part.clock()
        count += 1
    return count


class FrameTest(unittest.TestCase):
    def test_an_ntsc_frame_is_342_dots_by_262_lines(self) -> None:
        # Arrange
        part = chip("tms9928a")

        # Act
        period = frame_flag_period(part)

        # Assert
        self.assertEqual(period, LINE * 262)

    def test_a_pal_frame_is_342_dots_by_313_lines(self) -> None:
        # Arrange
        part = chip("tms9929a")

        # Act
        period = frame_flag_period(part)

        # Assert
        self.assertEqual(period, LINE * 313)

    def test_a_dot_is_two_master_ticks(self) -> None:
        # Arrange
        part = chip()
        before = part.cycles

        # Act
        part.clock()

        # Assert
        self.assertEqual(part.cycles - before, 2)


class ClockPinTest(unittest.TestCase):
    def count_edges(self, model: str) -> tuple[int, int]:
        part = chip(model)
        edges = [part.tick() for _ in range(LINE * 262 * 2)]
        return (
            sum(1 for one in edges if one & core.CPUCLK),
            sum(1 for one in edges if one & core.GROMCLK),
        )

    def test_cpuclk_and_gromclk_divide_the_master_by_3_and_24(self) -> None:
        # Arrange
        model = "tms9918a"

        # Act
        counted = self.count_edges(model)

        # Assert
        self.assertEqual(counted, (LINE * 262 * 2 // 3, LINE * 262 * 2 // 24))

    def test_a_colour_difference_part_has_no_clock_pins(self) -> None:
        # Arrange
        model = "tms9928a"

        # Act
        counted = self.count_edges(model)

        # Assert
        self.assertEqual(counted, (0, 0))


class ControlPortTest(unittest.TestCase):
    def test_data_then_register_number_loads_the_register(self) -> None:
        # Arrange
        part = chip()
        value = random.Random(SEED).randrange(256)

        # Act
        program(part, {5: value})

        # Assert
        self.assertEqual(part.registers[5], value)

    def test_reset_clears_registers_0_and_1_and_nothing_else(self) -> None:
        # Arrange
        part = chip()
        program(part, {0: 0x03, 1: 0xE2, 2: 0x0F})

        # Act
        part.reset()

        # Assert
        self.assertEqual(bytes(part.registers[:3]), bytes([0, 0, 0x0F]))

    def test_a_read_setup_prefetches_the_byte_it_names(self) -> None:
        # Arrange
        part = chip()
        value = random.Random(SEED).randrange(256)
        part.memory.write8(0x1234, value)
        part.write_control(0x34)
        part.write_control(0x12)
        part.run_dots(64)

        # Act
        read = part.read_data()

        # Assert
        self.assertEqual((read, part.address), (value, 0x1236))

    def test_a_write_setup_lands_data_at_its_address(self) -> None:
        # Arrange
        part = chip()
        value = random.Random(SEED).randrange(256)
        part.write_control(0x00)
        part.write_control(0x40 | 0x3F)

        # Act
        part.write_data(value)
        part.run_dots(64)

        # Assert
        self.assertEqual(part.memory.read8(0x3F00), value)


class StatusTest(unittest.TestCase):
    def test_the_frame_flag_rises_with_the_first_line_after_the_active_area(
        self,
    ) -> None:
        # Arrange
        part = chip()
        dots_until(part, 191, 341)

        # Act
        before = part.status & 0x80
        part.clock()

        # Assert
        self.assertEqual((before, part.status & 0x80), (0, 0x80))

    def test_the_interrupt_follows_the_flag_only_when_enabled(self) -> None:
        # Arrange
        part = chip()
        dots_until(part, 192, 1)

        # Act
        disabled = part.interrupt
        program(part, {1: 0x20})

        # Assert
        self.assertEqual((disabled, part.interrupt), (False, True))

    def test_reading_the_status_clears_the_flags_and_releases_the_interrupt(
        self,
    ) -> None:
        # Arrange
        part = chip()
        program(part, {1: 0x20})
        dots_until(part, 192, 1)

        # Act
        first = part.read_status()
        second = part.read_status()

        # Assert
        self.assertEqual((first & 0x80, second & 0xE0, part.interrupt), (0x80, 0, False))


class AccessTest(unittest.TestCase):
    def test_a_write_in_the_active_area_waits_for_a_graphics_window(self) -> None:
        # Arrange
        part = chip()
        program(part, {1: 0x40})
        dots_until(part, 100, 40)
        part.write_control(0x00)
        part.write_control(0x40)

        # Act
        part.write_data(0xAB)
        waited = 0
        while part.memory.read8(0) != 0xAB:
            part.tick()
            waited += 1

        # Assert
        self.assertLessEqual(waited * 1e6 / MASTER_HZ, 8.0)
        self.assertGreater(waited, 14)

    def test_a_text_mode_write_lands_sooner_than_in_graphics_one(self) -> None:
        # Arrange
        graphics = ticks_to_land({1: 0x40})

        # Act
        text = ticks_to_land({1: 0x50})

        # Assert
        self.assertLess(text, graphics)

    def test_an_access_asked_too_close_to_a_window_waits_for_the_next(self) -> None:
        # Arrange
        part = chip()
        program(part, {1: 0x40})
        windows = [one for one in slots.TABLES["graphics"] if 0 <= one < 512]
        dots_until(part, 100, 0)
        while part.dot * 2 + part.half != windows[1] - 5:
            part.tick()
        part.write_control(0x00)
        part.write_control(0x40)

        # Act
        part.write_data(0x5A)
        for _ in range(windows[1] - (windows[1] - 5) + 1):
            part.tick()

        # Assert
        self.assertEqual(part.memory.read8(0), 0)

    def test_a_second_write_before_the_window_replaces_the_first(self) -> None:
        # Arrange
        part = chip()
        program(part, {1: 0x40})
        dots_until(part, 100, 40)
        part.write_control(0x00)
        part.write_control(0x40)

        # Act
        part.write_data(0x11)
        part.write_data(0x22)
        part.run_dots(64)

        # Assert
        self.assertEqual((part.memory.read8(0), part.memory.read8(1)), (0, 0x22))


class DisplayTest(unittest.TestCase):
    def test_the_border_shows_the_backdrop(self) -> None:
        # Arrange
        part = chip()
        program(part, {1: 0x40, 7: 0x05})
        dots_until(part, 0, 260)

        # Act
        part.clock()

        # Assert
        self.assertEqual((part.region, part.colour), ("border", 5))

    def test_a_transparent_backdrop_shows_black(self) -> None:
        # Arrange
        part = chip()
        program(part, {1: 0x40, 7: 0x00})
        dots_until(part, 0, 260)

        # Act
        part.clock()

        # Assert
        self.assertEqual(part.colour, 1)

    def test_or_the_external_video_when_register_0_enables_it(self) -> None:
        # Arrange
        part = chip()
        program(part, {0: 0x01, 1: 0x40, 7: 0x00})
        dots_until(part, 0, 260)

        # Act
        part.clock()

        # Assert
        self.assertEqual(part.colour, core.EXTERNAL)

    def test_sync_and_blanking_carry_no_colour(self) -> None:
        # Arrange
        part = chip()
        program(part, {1: 0x40})
        dots_until(part, 0, 280)

        # Act
        part.clock()

        # Assert
        self.assertEqual((part.region, part.colour), ("sync", None))

    def test_a_graphics_one_cell_reaches_the_screen(self) -> None:
        # Arrange
        part = chip()
        program(part, {1: 0x40, 2: 0x06, 3: 0x80, 4: 0x00, 7: 0x04})
        part.memory.write8(0x1800, 0x01)
        part.memory.write8(0x0008, 0x80)
        part.memory.write8(0x2000, 0xF0)
        dots_until(part, 0, 0)

        # Act
        shown: list[int | None] = []
        for _ in range(3):
            part.clock()
            shown = [*shown, part.colour]

        # Assert
        self.assertEqual(shown, [15, 4, 4])

    def test_blanking_the_display_shows_the_backdrop_in_the_active_area(self) -> None:
        # Arrange
        part = chip()
        program(part, {1: 0x00, 7: 0x0C})
        dots_until(part, 0, 100)

        # Act
        part.clock()

        # Assert
        self.assertEqual((part.region, part.colour), ("active", 12))

    def test_text_mode_starts_its_cells_six_dots_in(self) -> None:
        # Arrange
        part = chip()
        program(part, {1: 0x50, 2: 0x00, 4: 0x01, 7: 0xF1})
        part.memory.write8(0x0800, 0xFC)
        dots_until(part, 0, 5)

        # Act
        shown: list[tuple[str, int | None]] = []
        for _ in range(2):
            part.clock()
            shown = [*shown, (part.region, part.colour)]

        # Assert
        self.assertEqual(shown, [("border", 1), ("active", 15)])


class ModeChangeTest(unittest.TestCase):
    def test_a_mode_change_inside_a_cell_draws_the_rest_in_the_new_mode(self) -> None:
        # Arrange
        part = chip()
        program(part, {1: 0x50, 4: 0x01, 7: 0xF1})
        part.memory.write8(0x0800, 0xFF)
        dots_until(part, 0, 14)

        # Act
        program(part, {1: 0x40})
        part.clock()

        # Assert
        self.assertEqual((part.region, part.colour), ("active", 1))


class SpriteStatusTest(unittest.TestCase):
    def sprites(self, planes: list[tuple[int, int]]) -> core.Chip:
        part = chip()
        program(part, {1: 0x40, 5: 0x36, 6: 0x07})
        for plane, (y, x) in enumerate(planes):
            for offset, value in enumerate((y, x, 0, 0x0F)):
                part.memory.write8(0x1B00 + plane * 4 + offset, value)
        part.memory.write8(0x1B00 + len(planes) * 4, 0xD0)
        part.memory.write8(0x3800, 0xFF)
        return part

    def test_two_sprites_meeting_set_the_coincidence_flag_when_drawn(self) -> None:
        # Arrange
        part = self.sprites([(9, 40), (9, 44)])
        dots_until(part, 10, 44)

        # Act
        before = part.status & 0x20
        part.clock()

        # Assert
        self.assertEqual((before, part.status & 0x20), (0, 0x20))

    def test_a_fifth_sprite_sets_the_flag_and_its_number(self) -> None:
        # Arrange
        part = self.sprites([(29, 20 * n) for n in range(5)])

        # Act
        dots_until(part, 30, 0)

        # Assert
        self.assertEqual(part.status & 0x5F, 0x40 | 4)


class ResetTest(unittest.TestCase):
    def test_reset_hands_the_part_back(self) -> None:
        # Arrange
        part = tms9918.Chip("tms9918a")

        # Act
        handed = part.reset()

        # Assert
        self.assertIs(handed, part)

    def test_reset_starts_the_frame_at_the_top_blanking(self) -> None:
        # Arrange
        part = tms9918.Chip("tms9929a")

        # Act
        part.reset()

        # Assert
        self.assertEqual((part.line, part.dot), (313 - 51 - 13, 0))

    def test_reset_clears_the_three_flags(self) -> None:
        # Arrange
        part = tms9918.Chip("tms9918a")
        part.status = 0xFF

        # Act
        part.reset()

        # Assert
        self.assertEqual(part.status & 0xE0, 0)


if __name__ == "__main__":
    unittest.main()

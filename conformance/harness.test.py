import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from conformance import cartridges, harness  # noqa: E402

READY = harness.why_not() is None

LD_A = 0x3E

OUT = 0xD3

IN = 0xDB

JR = 0x18

HALT = 0x76

EI = 0xFB

DI = 0xF3

IM_PREFIX = 0xED

IM_ONE = 0x56

RETI = 0x4D


def program(*parts: int) -> bytes:
    image = bytearray(0x2000)
    image[: len(parts)] = bytes(parts)
    return bytes(image)


def register_write(register: int, value: int) -> tuple[int, ...]:
    return (LD_A, value, OUT, 0xBF, LD_A, 0x80 | register, OUT, 0xBF)


@unittest.skipUnless(READY, "zilog-z80-python is not checked out")
class MemoryTest(unittest.TestCase):
    def test_the_cartridge_answers_below_c000(self) -> None:
        # Arrange
        board = harness.Board(program(0x12, 0x34))

        # Act
        read = board.read8(0x0001)

        # Assert
        self.assertEqual(read, 0x34)

    def test_a_byte_past_the_end_of_a_short_cartridge_reads_ff(self) -> None:
        # Arrange
        board = harness.Board(program())

        # Act
        read = board.read8(0x8000)

        # Assert
        self.assertEqual(read, 0xFF)

    def test_the_kilobyte_of_ram_repeats_up_to_ffff(self) -> None:
        # Arrange
        board = harness.Board(program())

        # Act
        board.write8(0xC010, 0x5A)

        # Assert
        self.assertEqual((board.read8(0xC410), board.read8(0xFC10)), (0x5A, 0x5A))

    def test_a_write_below_c000_changes_nothing(self) -> None:
        # Arrange
        board = harness.Board(program(0x11))

        # Act
        board.write8(0x0000, 0x99)

        # Assert
        self.assertEqual(board.read8(0x0000), 0x11)

    def test_a_board_with_cartridge_ram_keeps_a_write_at_8000(self) -> None:
        # Arrange
        board = harness.Board(program(), layout=cartridges.LAYOUTS["othello"])

        # Act
        board.write8(0x8010, 0xA5)

        # Assert
        self.assertEqual((board.read8(0x8810), board.read8(0xC010) == 0xA5), (0xA5, False))

    def test_an_image_no_table_lists_gets_the_plain_board(self) -> None:
        # Arrange
        rom = program(0x22)

        # Act
        board = harness.Board(rom)

        # Assert
        self.assertIs(board.layout, cartridges.LAYOUTS[cartridges.PLAIN])


@unittest.skipUnless(READY, "zilog-z80-python is not checked out")
class PortTest(unittest.TestCase):
    def test_bf_writes_reach_the_vdp_control_port(self) -> None:
        # Arrange
        board = harness.Board(program(*register_write(7, 0x1C), HALT))

        # Act
        board.run_frames(1)

        # Assert
        self.assertEqual((board.vdp.registers[7], board.seen.registers[(7, 0x1C)]), (0x1C, 1))

    def test_7f_writes_are_counted_as_the_sound_generator(self) -> None:
        # Arrange
        board = harness.Board(program(LD_A, 0x9F, OUT, 0x7F, HALT))

        # Act
        board.run_frames(1)

        # Assert
        self.assertEqual(board.seen.sound, 1)

    def test_the_controller_ports_read_as_nothing_pressed(self) -> None:
        # Arrange
        board = harness.Board(program())

        # Act
        read = board.read_port(0xDC)

        # Assert
        self.assertEqual(read, 0xFF)

    def test_a_second_access_before_the_first_is_served_is_counted_as_lost(
        self,
    ) -> None:
        # Arrange
        board = harness.Board(program())

        # Act
        board.write_port(0xBE, 1)
        board.write_port(0xBE, 2)

        # Assert
        self.assertEqual(board.seen.lost, 1)

    def test_a_data_read_before_a_write_is_served_is_counted_as_lost(self) -> None:
        # Arrange
        board = harness.Board(program())
        board.write_port(0xBE, 1)

        # Act
        board.read_port(0xBE)

        # Assert
        self.assertEqual(board.seen.lost, 1)

    def test_a_read_setup_before_a_write_is_served_is_counted_as_lost(self) -> None:
        # Arrange
        board = harness.Board(program())
        board.write_port(0xBE, 1)
        board.write_port(0xBF, 0x00)

        # Act
        board.write_port(0xBF, 0x00)

        # Assert
        self.assertEqual(board.seen.lost, 1)


@unittest.skipUnless(READY, "zilog-z80-python is not checked out")
class FrameTest(unittest.TestCase):
    def test_a_frame_is_342_dots_by_262_lines_of_cpu_time(self) -> None:
        # Arrange
        board = harness.Board(program(JR, 0xFE))

        # Act
        board.run_frames(2)

        # Assert
        self.assertEqual(board.frames, 2)
        self.assertEqual(board.cpu.cycles * 3 // 2 // 342 // 262 >= 1, True)

    def test_the_vdp_interrupt_reaches_the_processor(self) -> None:
        # Arrange
        handler = 0x38
        code = bytearray(
            program(
                *register_write(1, 0x60),
                IM_PREFIX,
                IM_ONE,
                EI,
                JR,
                0xFE,
            )
        )
        code[handler : handler + 4] = bytes([IN, 0xBF, EI, IM_PREFIX])
        code[handler + 4] = RETI
        board = harness.Board(bytes(code))

        # Act
        board.run_frames(3)

        # Assert
        self.assertGreaterEqual(board.seen.status_reads, 2)

    def test_the_display_is_recorded_when_a_frame_ends_with_it_on(self) -> None:
        # Arrange
        board = harness.Board(program(*register_write(1, 0x40), DI, JR, 0xFE))

        # Act
        board.run_frames(2)

        # Assert
        self.assertEqual(board.seen.modes["graphics1"], 2)

    def test_a_text_frame_records_no_sprite_size(self) -> None:
        # Arrange
        board = harness.Board(program(*register_write(1, 0x50), DI, JR, 0xFE))

        # Act
        board.run_frames(2)

        # Assert
        self.assertEqual((board.seen.modes["text"], dict(board.seen.sprites)), (2, {}))


class ReadinessTest(unittest.TestCase):
    def test_without_the_processor_the_reason_is_named(self) -> None:
        # Arrange
        absent = Path("/nonexistent")

        # Act
        why = harness.why_not(absent)

        # Assert
        self.assertIn("git submodule update --init", str(why))


if __name__ == "__main__":
    unittest.main()

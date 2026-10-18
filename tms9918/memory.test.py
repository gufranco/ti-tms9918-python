import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import random  # noqa: E402
import unittest  # noqa: E402

import tms9918  # noqa: E402

SEED = 9918

REACHED = 16384


def contents(store: tms9918.Vram) -> bytes:
    return bytes(store.read8(address) for address in range(REACHED))


class SizeTest(unittest.TestCase):
    def test_it_holds_the_16384_bytes_a_14_bit_address_reaches(self) -> None:
        # Arrange
        store = tms9918.Vram(fill=0)
        for address in range(REACHED):
            store.write8(address, address ^ address >> 8)

        # Act
        held = contents(store)

        # Assert
        self.assertEqual(held, bytes((one ^ one >> 8) & 0xFF for one in range(REACHED)))

    def test_an_address_wraps_at_14_bits(self) -> None:
        # Arrange
        store = tms9918.Vram(fill=0)
        value = random.Random(SEED).randrange(1, 256)

        # Act
        store.write8(0x4000 + 0x123, value)

        # Assert
        self.assertEqual(store.read8(0x123), value)


class PowerOnTest(unittest.TestCase):
    def test_it_comes_up_holding_whatever_the_seed_scrambled(self) -> None:
        # Arrange
        expected = bytearray(random.Random(SEED).randbytes(16384))

        # Act
        store = tms9918.Vram(seed=SEED)

        # Assert
        self.assertEqual(contents(store), expected)

    def test_two_seeds_come_up_differently(self) -> None:
        # Arrange
        first = tms9918.Vram(seed=SEED)

        # Act
        second = tms9918.Vram(seed=SEED + 1)

        # Assert
        self.assertNotEqual(contents(first), contents(second))

    def test_a_fill_byte_is_everywhere(self) -> None:
        # Arrange
        byte = random.Random(SEED).randrange(256)

        # Act
        store = tms9918.Vram(fill=byte)

        # Assert
        self.assertEqual(set(contents(store)), {byte})

    def test_a_fill_of_bytes_is_laid_from_the_start_and_zero_after(self) -> None:
        # Arrange
        image = random.Random(SEED).randbytes(100)

        # Act
        store = tms9918.Vram(fill=image)

        # Assert
        self.assertEqual(contents(store)[:100], image)
        self.assertEqual(set(contents(store)[100:]), {0})


class ByteTest(unittest.TestCase):
    def test_a_written_value_is_read_back_as_a_byte(self) -> None:
        # Arrange
        store = tms9918.Vram(fill=0)

        # Act
        store.write8(0x2000, 0x1FF)

        # Assert
        self.assertEqual(store.read8(0x2000), 0xFF)


if __name__ == "__main__":
    unittest.main()

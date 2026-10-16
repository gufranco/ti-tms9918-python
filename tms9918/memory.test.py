import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import random  # noqa: E402
import unittest  # noqa: E402

from tms9918 import memory  # noqa: E402

SEED = 9918


class SizeTest(unittest.TestCase):
    def test_it_holds_the_16384_bytes_a_14_bit_address_reaches(self) -> None:
        # Arrange
        store = memory.Vram()

        # Act
        size = len(store.data)

        # Assert
        self.assertEqual(size, 16384)

    def test_an_address_wraps_at_14_bits(self) -> None:
        # Arrange
        store = memory.Vram(fill=0)
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
        store = memory.Vram(seed=SEED)

        # Assert
        self.assertEqual(store.data, expected)

    def test_two_seeds_come_up_differently(self) -> None:
        # Arrange
        first = memory.Vram(seed=SEED)

        # Act
        second = memory.Vram(seed=SEED + 1)

        # Assert
        self.assertNotEqual(first.data, second.data)

    def test_a_fill_byte_is_everywhere(self) -> None:
        # Arrange
        byte = random.Random(SEED).randrange(256)

        # Act
        store = memory.Vram(fill=byte)

        # Assert
        self.assertEqual(set(store.data), {byte})

    def test_a_fill_of_bytes_is_laid_from_the_start_and_zero_after(self) -> None:
        # Arrange
        image = random.Random(SEED).randbytes(100)

        # Act
        store = memory.Vram(fill=image)

        # Assert
        self.assertEqual(bytes(store.data[:100]), image)
        self.assertEqual(set(store.data[100:]), {0})


class ByteTest(unittest.TestCase):
    def test_a_written_value_is_read_back_as_a_byte(self) -> None:
        # Arrange
        store = memory.Vram(fill=0)

        # Act
        store.write8(0x2000, 0x1FF)

        # Assert
        self.assertEqual(store.read8(0x2000), 0xFF)


if __name__ == "__main__":
    unittest.main()

import random

UNSET_SEED = 0x9918

ADDRESS_BITS = 14

SIZE = 1 << ADDRESS_BITS

ADDRESS_MASK = SIZE - 1


def scramble(size: int, seed: int = UNSET_SEED) -> bytearray:
    return bytearray(random.Random(seed).randbytes(size))


class Vram:
    __slots__ = ("data",)

    def __init__(
        self,
        fill: int | bytes | bytearray | None = None,
        seed: int = UNSET_SEED,
    ) -> None:
        if fill is None:
            self.data = scramble(SIZE, seed)
        elif isinstance(fill, int):
            self.data = bytearray([fill & 0xFF]) * SIZE
        else:
            self.data = bytearray(SIZE)
            self.data[: len(fill)] = fill

    def read8(self, address: int) -> int:
        return self.data[address & ADDRESS_MASK]

    def write8(self, address: int, value: int) -> None:
        self.data[address & ADDRESS_MASK] = value & 0xFF

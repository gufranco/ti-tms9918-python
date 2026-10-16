import statistics
import sys
import time
from collections.abc import Sequence

import tms9918
from tms9918.core import Chip
from tms9918.memory import Vram

MEASURED_HERE = 950_000

HEADROOM = 10

FLOOR_STEP = 10_000

FLOOR = MEASURED_HERE // HEADROOM // FLOOR_STEP * FLOOR_STEP

DOTS = 342 * 262

REPEATS = 5

BUSY = {0: 0x02, 1: 0x62, 2: 0x0E, 3: 0xFF, 4: 0x03, 5: 0x76, 6: 0x07, 7: 0x04}

SEED = 9918


def busy_chip() -> Chip:
    part: Chip = tms9918.Chip("tms9918a", Vram(seed=SEED), seed=SEED)
    part.reset()
    part.read_status()
    for register, value in BUSY.items():
        part.write_control(value)
        part.write_control(0x80 | register)
    for plane in range(32):
        part.memory.write8(0x3B00 + plane * 4, (plane * 6) & 0xFF)
    return part


class Timed:
    __slots__ = ("calls", "seconds", "what")

    def __init__(self, what: str, calls: int, seconds: Sequence[float]) -> None:
        self.what = what
        self.calls = calls
        self.seconds = list(seconds)

    def median(self) -> float:
        return statistics.median(self.seconds)

    def rate(self) -> float:
        taken = self.median()
        return self.calls / taken if taken > 0 else 0.0

    def beats(self, floor: int) -> bool:
        return self.rate() >= floor


def measure(calls: int = DOTS, repeats: int = REPEATS) -> Timed:
    seconds = []
    for _ in range(repeats):
        part = busy_chip()
        started = time.perf_counter()
        for _ in range(calls):
            part.clock()
        seconds.append(time.perf_counter() - started)
    return Timed("dots of a Graphics II frame with sprites on every line", calls, seconds)


def lines_for(found: Timed, floor: int = FLOOR) -> list[str]:
    runtime = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    lines = [
        f"  {found.what}: {found.rate():,.0f} per second"
        f" (median of {len(found.seconds)}) on Python {runtime}",
        f"  floor: {floor:,} per second",
    ]
    if not found.beats(floor):
        lines.append(f"  below the floor: {found.rate():,.0f} is under {floor:,}")
    return lines


def main(calls: int = DOTS, repeats: int = REPEATS, floor: int = FLOOR) -> int:
    found = measure(calls, repeats)
    for line in lines_for(found, floor):
        print(line)
    return 0 if found.beats(floor) else 1


if __name__ == "__main__":
    raise SystemExit(main())

COMPOSITE: dict[int, tuple[float, float | None]] = {
    0x1: (0.00, None),
    0x2: (0.53, 0.53),
    0x3: (0.67, 0.40),
    0x4: (0.40, 0.60),
    0x5: (0.53, 0.53),
    0x6: (0.47, 0.47),
    0x7: (0.67, 0.60),
    0x8: (0.53, 0.60),
    0x9: (0.67, 0.60),
    0xA: (0.73, 0.47),
    0xB: (0.80, 0.33),
    0xC: (0.46, 0.47),
    0xD: (0.53, 0.40),
    0xE: (0.80, None),
    0xF: (1.00, None),
}

COMPOSITE_SPECIAL: dict[str, tuple[float, float | None]] = {
    "black": (0.00, None),
    "burst": (0.00, 0.40),
    "sync": (-0.40, None),
}

DIFFERENCE: dict[int, tuple[float, float, float]] = {
    0x1: (0.00, 0.47, 0.47),
    0x2: (0.53, 0.07, 0.20),
    0x3: (0.67, 0.17, 0.27),
    0x4: (0.40, 0.4, 1.00),
    0x5: (0.53, 0.43, 0.93),
    0x6: (0.47, 0.83, 0.30),
    0x7: (0.73, 0.00, 0.70),
    0x8: (0.53, 0.93, 0.27),
    0x9: (0.67, 0.93, 0.27),
    0xA: (0.73, 0.57, 0.07),
    0xB: (0.80, 0.57, 0.17),
    0xC: (0.47, 0.13, 0.23),
    0xD: (0.53, 0.73, 0.67),
    0xE: (0.80, 0.47, 0.47),
    0xF: (1.00, 0.47, 0.47),
}

DIFFERENCE_SPECIAL: dict[str, tuple[float, float, float]] = {
    "black": (0.00, 0.47, 0.47),
    "sync": (-0.46, 0.47, 0.47),
    "external": (0.00, -0.46, -0.46),
}

_BURSTS: dict[str, tuple[float, float, float]] = {
    "tms9928a": (0.00, 0.47, 0.1),
    "tms9929a": (0.00, 0.73, 0.2),
}


def burst(part: str) -> tuple[float, float, float]:
    return _BURSTS[part]

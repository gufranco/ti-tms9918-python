TICKS = 684

LEAD = 16

OPENMSX_TICKS = 1368

OPENMSX_ACTIVE_START = 258

GRID_SWITCH = 636

GRID_FIRST_LINE = -1

GRID_LAST_LINE = 191

OPENMSX_GRAPHICS = (
    4, 12, 20, 28, 116, 124, 132, 140, 220, 348,
    476, 604, 732, 860, 988, 1116, 1236, 1244, 1364,
)  # fmt: skip

OPENMSX_MULTICOLOR = (
    4, 12, 20, 28, 116, 124, 132, 140, 220, 228,
    260, 292, 324, 348, 356, 388, 420, 452, 476, 484,
    516, 548, 580, 604, 612, 644, 676, 708, 732, 740,
    772, 804, 836, 860, 868, 900, 932, 964, 988, 996,
    1028, 1060, 1092, 1116, 1124, 1156, 1188, 1220, 1236, 1244,
    1364,
)  # fmt: skip

OPENMSX_TEXT = (
    4, 12, 20, 28, 36, 44, 52, 60, 68, 76,
    84, 92, 100, 108, 116, 124, 132, 140, 148, 156,
    164, 172, 180, 188, 196, 204, 212, 220, 228, 244,
    268, 292, 316, 340, 364, 388, 412, 436, 460, 484,
    508, 532, 556, 580, 604, 628, 652, 676, 700, 724,
    748, 772, 796, 820, 844, 868, 892, 916, 940, 964,
    988, 1012, 1036, 1060, 1084, 1108, 1132, 1156, 1180, 1196,
    1204, 1212, 1220, 1228, 1236, 1244, 1252, 1260, 1268, 1276,
    1284, 1292, 1300, 1308, 1316, 1324, 1332, 1340, 1348, 1356,
    1364,
)  # fmt: skip

OPENMSX_OFF = (
    4, 12, 20, 28, 36, 44, 52, 60, 68, 76,
    84, 92, 100, 108, 116, 124, 132, 140, 148, 156,
    164, 172, 180, 188, 196, 204, 220, 236, 252, 268,
    284, 300, 316, 332, 348, 364, 380, 396, 412, 428,
    444, 460, 476, 492, 508, 524, 540, 556, 572, 588,
    604, 620, 636, 652, 668, 684, 700, 716, 732, 748,
    764, 780, 796, 812, 828, 844, 860, 876, 892, 908,
    924, 940, 956, 972, 988, 1004, 1020, 1036, 1052, 1068,
    1084, 1100, 1116, 1132, 1148, 1164, 1180, 1196, 1212, 1228,
    1236, 1244, 1252, 1260, 1268, 1276, 1284, 1292, 1300, 1308,
    1316, 1324, 1332, 1340, 1348, 1356, 1364,
)  # fmt: skip


def from_openmsx(position: int) -> int:
    return (position - OPENMSX_ACTIVE_START) // 2 % TICKS


def _converted(positions: tuple[int, ...]) -> tuple[int, ...]:
    return tuple(sorted(from_openmsx(one) for one in positions))


TABLES = {
    "graphics": _converted(OPENMSX_GRAPHICS),
    "multicolor": _converted(OPENMSX_MULTICOLOR),
    "text": _converted(OPENMSX_TEXT),
    "off": _converted(OPENMSX_OFF),
}

SERVED = {name: frozenset(table) for name, table in TABLES.items()}


def table_for(display: bool, mode: str) -> tuple[int, ...]:
    return TABLES[mode if display else "off"]


def grid_line(line: int, tick: int, lines: int) -> int:
    ahead = line + (1 if tick >= GRID_SWITCH else 0)
    return ahead - lines if ahead >= lines - 2 else ahead


def display_grid(line: int) -> bool:
    return GRID_FIRST_LINE <= line <= GRID_LAST_LINE

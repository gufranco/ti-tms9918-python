TICKS = 684

LEAD = 16

GRID_SWITCH = 636

GRID_FIRST_LINE = -1

GRID_LAST_LINE = 191

OUTSIDE_PICTURE = (489, 493, *range(553, 570, 4), *range(613, 626, 4), 665)

GRAPHICS = tuple(sorted((*range(45, 430, 64), *OUTSIDE_PICTURE)))

MULTICOLOR = tuple(sorted({*range(1, 482, 16), *GRAPHICS, 669}))

TEXT = (*range(5, 462, 12), *range(469, 670, 4), 677)

OFF = (*range(5, 486, 8), *range(489, 658, 4), 665, 673, 681)

TABLES = {
    "graphics": GRAPHICS,
    "multicolor": MULTICOLOR,
    "text": TEXT,
    "off": OFF,
}

SERVED = {name: frozenset(table) for name, table in TABLES.items()}


def grid_line(line: int, tick: int, lines: int) -> int:
    ahead = line + (1 if tick >= GRID_SWITCH else 0)
    return ahead - lines if ahead >= lines - 2 else ahead


def display_grid(line: int) -> bool:
    return GRID_FIRST_LINE <= line <= GRID_LAST_LINE

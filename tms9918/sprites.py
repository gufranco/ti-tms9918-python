from collections.abc import Callable

Reader = Callable[[int], int]

PLANES = 32

SHOWN_PER_LINE = 4

TERMINATOR = 0xD0

NEGATIVE_FROM = 0xE1

EARLY_CLOCK = 0x80

EARLY_SHIFT = 32

SIZE = 0x02

MAG = 0x01

ACTIVE_DOTS = 256

RIGHT_HALF = 16


class Sprite:
    __slots__ = ("bits", "colour", "plane", "row", "x")

    def __init__(self, plane: int, x: int, colour: int, row: int, bits: tuple[int, ...]) -> None:
        self.plane = plane
        self.x = x
        self.colour = colour
        self.row = row
        self.bits = bits


class Evaluated:
    __slots__ = ("fifth", "last", "shown")

    def __init__(self, shown: tuple[Sprite, ...], fifth: int | None, last: int) -> None:
        self.shown = shown
        self.fifth = fifth
        self.last = last


class Drawn:
    __slots__ = ("collision", "colours")

    def __init__(self, colours: list[int | None], collision: int | None) -> None:
        self.colours = colours
        self.collision = collision


def _top(position: int) -> int:
    return (position - 256 if position >= NEGATIVE_FROM else position) + 1


def _height(held: bytearray) -> int:
    return (16 if held[1] & SIZE else 8) << (held[1] & MAG)


def _bits(read: Reader, held: bytearray, name: int, row: int) -> tuple[int, ...]:
    base = (held[6] & 7) << 11
    if not held[1] & SIZE:
        return (read(base | name << 3 | row),)
    first = base | (name & 0xFC) << 3 | row
    return (read(first), read(first + RIGHT_HALF))


def _sprite(read: Reader, held: bytearray, plane: int, row: int) -> Sprite:
    entry = (held[5] & 0x7F) << 7 | plane << 2
    tag = read(entry + 3)
    x = read(entry + 1) - (EARLY_SHIFT if tag & EARLY_CLOCK else 0)
    return Sprite(plane, x, tag & 0x0F, row, _bits(read, held, read(entry + 2), row))


def evaluate(read: Reader, held: bytearray, line: int) -> Evaluated:
    height = _height(held)
    shown: list[Sprite] = []
    for plane in range(PLANES):
        position = read((held[5] & 0x7F) << 7 | plane << 2)
        if position == TERMINATOR:
            return Evaluated(tuple(shown), None, plane)
        offset = line - _top(position)
        if not 0 <= offset < height:
            continue
        if len(shown) == SHOWN_PER_LINE:
            return Evaluated(tuple(shown), plane, plane)
        shown = [*shown, _sprite(read, held, plane, offset >> (held[1] & MAG))]
    return Evaluated(tuple(shown), None, PLANES - 1)


def _dots(sprite: Sprite, magnified: bool) -> list[int]:
    scale = 2 if magnified else 1
    return [
        sprite.x + (half * 8 + bit) * scale + repeat
        for half, byte in enumerate(sprite.bits)
        for bit in range(8)
        if byte & (0x80 >> bit)
        for repeat in range(scale)
    ]


def draw(shown: tuple[Sprite, ...], magnified: bool) -> Drawn:
    colours: list[int | None] = [None] * ACTIVE_DOTS
    seen = [False] * ACTIVE_DOTS
    first: int | None = None
    for sprite in shown:
        for dot in _dots(sprite, magnified):
            if not 0 <= dot < ACTIVE_DOTS:
                continue
            if seen[dot] and (first is None or dot < first):
                first = dot
            seen[dot] = True
            if sprite.colour and colours[dot] is None:
                colours[dot] = sprite.colour
    return Drawn(colours, first)

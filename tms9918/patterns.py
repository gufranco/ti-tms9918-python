from collections.abc import Callable

Reader = Callable[[int], int]

M3 = 0x02

M1 = 0x10

M2 = 0x08

TEXT_COLUMNS = 40

PATTERN_COLUMNS = 32

TEXT_WIDTH = 6

PATTERN_WIDTH = 8

THIRD_LINES = 64

_MODES = {
    (0, 0, 0): "graphics1",
    (0, 0, 1): "graphics2",
    (0, 1, 0): "multicolor",
    (1, 0, 0): "text",
    (1, 1, 0): "text+multicolor",
    (0, 1, 1): "graphics2+multicolor",
    (1, 0, 1): "text+graphics2",
    (1, 1, 1): "text+graphics2+multicolor",
}


def mode_of(r0: int, r1: int) -> str:
    return _MODES[(int(bool(r1 & M1)), int(bool(r1 & M2)), int(bool(r0 & M3)))]


def is_text(mode: str) -> bool:
    return mode.startswith("text")


def width(mode: str) -> int:
    return TEXT_WIDTH if is_text(mode) else PATTERN_WIDTH


def cells(mode: str) -> int:
    return TEXT_COLUMNS if is_text(mode) else PATTERN_COLUMNS


def _bits(byte: int, one: int, zero: int, count: int) -> tuple[int, ...]:
    return tuple(one if byte & (0x80 >> bit) else zero for bit in range(count))


def _halves(byte: int) -> tuple[int, ...]:
    return (byte >> 4,) * 4 + (byte & 0x0F,) * 4


def _name(read: Reader, held: bytearray, line: int, column: int, columns: int) -> int:
    return read((held[2] & 0x0F) << 10 | ((line >> 3) * columns + column))


def _colour_mask(held: bytearray) -> int:
    return (held[3] & 0x7F) << 3 | 7


def _pattern_mask(held: bytearray) -> int:
    return (held[4] & 3) << 8 | (_colour_mask(held) & 0xFF)


def _third(name: int, line: int) -> int:
    return name + ((line // THIRD_LINES) << 8)


def _graphics1(read: Reader, held: bytearray, line: int, column: int) -> tuple[int, ...]:
    name = _name(read, held, line, column, PATTERN_COLUMNS)
    pattern = read((held[4] & 7) << 11 | name << 3 | (line & 7))
    colour = read(held[3] << 6 | name >> 3)
    return _bits(pattern, colour >> 4, colour & 0x0F, PATTERN_WIDTH)


def _graphics2(read: Reader, held: bytearray, line: int, column: int) -> tuple[int, ...]:
    entry = _third(_name(read, held, line, column, PATTERN_COLUMNS), line)
    pattern = read((held[4] & 4) << 11 | (entry & _pattern_mask(held)) << 3 | (line & 7))
    colour = read((held[3] & 0x80) << 6 | (entry & _colour_mask(held)) << 3 | (line & 7))
    return _bits(pattern, colour >> 4, colour & 0x0F, PATTERN_WIDTH)


def _multicolor(read: Reader, held: bytearray, line: int, column: int) -> tuple[int, ...]:
    name = _name(read, held, line, column, PATTERN_COLUMNS)
    return _halves(read((held[4] & 7) << 11 | name << 3 | (line >> 2) & 7))


def _graphics2_multicolor(read: Reader, held: bytearray, line: int, column: int) -> tuple[int, ...]:
    entry = _third(_name(read, held, line, column, PATTERN_COLUMNS), line)
    masked = entry & _pattern_mask(held)
    return _halves(read((held[4] & 4) << 11 | masked << 3 | (line >> 2) & 7))


def _text(read: Reader, held: bytearray, line: int, column: int) -> tuple[int, ...]:
    name = _name(read, held, line, column, TEXT_COLUMNS)
    pattern = read((held[4] & 7) << 11 | name << 3 | (line & 7))
    return _bits(pattern, held[7] >> 4, held[7] & 0x0F, TEXT_WIDTH)


def _text_graphics2(read: Reader, held: bytearray, line: int, column: int) -> tuple[int, ...]:
    entry = _third(_name(read, held, line, column, TEXT_COLUMNS), line)
    pattern = read((held[4] & 4) << 11 | (entry & _pattern_mask(held)) << 3 | (line & 7))
    return _bits(pattern, held[7] >> 4, held[7] & 0x0F, TEXT_WIDTH)


def _stripes(read: Reader, held: bytearray, line: int, column: int) -> tuple[int, ...]:
    return _bits(0xF0, held[7] >> 4, held[7] & 0x0F, TEXT_WIDTH)


_DRAW: dict[str, Callable[[Reader, bytearray, int, int], tuple[int, ...]]] = {
    "graphics1": _graphics1,
    "graphics2": _graphics2,
    "multicolor": _multicolor,
    "text": _text,
    "text+multicolor": _stripes,
    "graphics2+multicolor": _graphics2_multicolor,
    "text+graphics2": _text_graphics2,
    "text+graphics2+multicolor": _stripes,
}


def cell(read: Reader, held: bytearray, mode: str, line: int, column: int) -> tuple[int, ...]:
    return _DRAW[mode](read, held, line, column)

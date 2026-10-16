from typing import Any

ACTIVE = "active"

BORDER = "border"

BLANKING = "blanking"

SYNC = "sync"

BURST = "burst"

DOTS = 342

ACTIVE_LINES = 192

BOTTOM_BLANKING = 3

VERTICAL_SYNC = 3

TOP_BLANKING = 13

PATTERN_COUNTS = (
    (ACTIVE, 256),
    (BORDER, 15),
    (BLANKING, 8),
    (SYNC, 26),
    (BLANKING, 2),
    (BURST, 14),
    (BLANKING, 8),
    (BORDER, 13),
)

TEXT_COUNTS = (
    (ACTIVE, 240),
    (BORDER, 25),
    (BLANKING, 8),
    (SYNC, 26),
    (BLANKING, 2),
    (BURST, 14),
    (BLANKING, 8),
    (BORDER, 19),
)

TEXT_LEFT_BORDER = TEXT_COUNTS[-1][1]

PATTERN_LEFT_BORDER = PATTERN_COUNTS[-1][1]

TEXT_OFFSET = TEXT_LEFT_BORDER - PATTERN_LEFT_BORDER


def _row(counts: tuple[tuple[str, int], ...], offset: int) -> tuple[str, ...]:
    laid = [kind for kind, count in counts for _ in range(count)]
    return tuple(laid[-offset:] + laid[:-offset]) if offset else tuple(laid)


PATTERN_ROW = _row(PATTERN_COUNTS, 0)

TEXT_ROW = _row(TEXT_COUNTS, TEXT_OFFSET)


def lines_of(model: Any) -> tuple[str, ...]:
    bottom: int = model.bottom_border
    top: int = model.top_border
    return (
        (ACTIVE,) * ACTIVE_LINES
        + (BORDER,) * bottom
        + (BLANKING,) * BOTTOM_BLANKING
        + (SYNC,) * VERTICAL_SYNC
        + (BLANKING,) * TOP_BLANKING
        + (BORDER,) * top
    )


def region(line: str, dot: str) -> str:
    if line == SYNC:
        return SYNC
    if line == BLANKING:
        return SYNC if dot == SYNC else BLANKING
    if line == BORDER and dot == ACTIVE:
        return BORDER
    return dot

from collections.abc import Callable, Sequence
from typing import Any, override

from tms9918.errors import UnknownModelError

COMPOSITE = "composite"

COLOUR_DIFFERENCE = "colour difference"

NTSC_LINES = 262

PAL_LINES = 313

NTSC_TOP_BORDER = 27

NTSC_BOTTOM_BORDER = 24

PAL_TOP_BORDER = 51

PAL_BOTTOM_BORDER = 51


class Model:
    __slots__ = (
        "aliases",
        "bottom_border",
        "clock_pins",
        "core",
        "lines",
        "name",
        "output",
        "summary",
        "top_border",
    )

    def __init__(
        self,
        name: str,
        summary: str,
        lines: int,
        borders: tuple[int, int],
        output: str,
        core: Callable[..., Any],
        aliases: Sequence[str] = (),
    ) -> None:
        self.name = name
        self.summary = summary
        self.lines = lines
        self.top_border, self.bottom_border = borders
        self.output = output
        self.clock_pins = output == COMPOSITE
        self.core = core
        self.aliases = tuple(aliases)

    def build(self, memory: Any, **options: Any) -> Any:
        return self.core(self, memory, **options)

    @override
    def __repr__(self) -> str:
        return f"<Model {self.name}, {self.lines} lines, {self.output}>"


def _build(model: Model, memory: Any, **options: Any) -> Any:
    from .core import Chip

    return Chip(model, memory, **options)


_CATALOGUE = (
    Model(
        name="tms9918a",
        summary=(
            "The TMS9918A: 262 lines at about 60 frames a second, an NTSC composite "
            "video output, and the CPUCLK and GROMCLK pins."
        ),
        lines=NTSC_LINES,
        borders=(NTSC_TOP_BORDER, NTSC_BOTTOM_BORDER),
        output=COMPOSITE,
        core=_build,
        aliases=("9918a",),
    ),
    Model(
        name="tms9928a",
        summary=(
            "The TMS9928A: the TMS9918A's timing with luminance and two colour "
            "difference outputs in place of composite video and the clock pins."
        ),
        lines=NTSC_LINES,
        borders=(NTSC_TOP_BORDER, NTSC_BOTTOM_BORDER),
        output=COLOUR_DIFFERENCE,
        core=_build,
        aliases=("9928a",),
    ),
    Model(
        name="tms9929a",
        summary=(
            "The TMS9929A: 313 lines at about 50 frames a second, with the colour "
            "difference outputs of the TMS9928A and a colour burst on both of them."
        ),
        lines=PAL_LINES,
        borders=(PAL_TOP_BORDER, PAL_BOTTOM_BORDER),
        output=COLOUR_DIFFERENCE,
        core=_build,
        aliases=("9929a",),
    ),
)

MODELS = {model.name: model for model in _CATALOGUE}

_BY_ALIAS = {alias: model for model in _CATALOGUE for alias in (model.name, *model.aliases)}


def _normalise(name: str) -> str:
    return str(name).strip().lower().replace("-", "").replace("_", "")


def lookup(name: str | None) -> Model:
    if name is None:
        raise UnknownModelError(
            "no model was named, and this package will not choose one for you."
            f" Name one of: {', '.join(sorted(MODELS))}"
        )
    found = _BY_ALIAS.get(_normalise(name))
    if found is None:
        raise UnknownModelError(
            f"{name} is not a model this package covers; it has {', '.join(sorted(MODELS))}"
        )
    return found

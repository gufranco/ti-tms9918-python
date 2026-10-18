from typing import Any

from . import core as core
from . import errors as errors
from . import geometry as geometry
from . import levels as levels
from . import memory as memory
from . import models as models
from . import patterns as patterns
from . import slots as slots
from . import sprites as sprites
from .core import CPUCLK, EXTERNAL, GROMCLK
from .errors import UnknownModelError
from .levels import COMPOSITE, COMPOSITE_SPECIAL, DIFFERENCE, DIFFERENCE_SPECIAL, burst
from .memory import UNSET_SEED, Vram
from .models import MODELS, Model
from .version import VERSION

__version__ = VERSION


def Chip(model: str | None = None, memory: Any = None, **options: Any) -> "core.Chip":  # noqa: N802
    seed = options.get("seed", UNSET_SEED)
    built: core.Chip = models.lookup(model).build(
        Vram(seed=seed) if memory is None else memory, **options
    )
    return built


__all__ = [
    "COMPOSITE",
    "COMPOSITE_SPECIAL",
    "CPUCLK",
    "DIFFERENCE",
    "DIFFERENCE_SPECIAL",
    "EXTERNAL",
    "GROMCLK",
    "MODELS",
    "UNSET_SEED",
    "Chip",
    "Model",
    "UnknownModelError",
    "Vram",
    "__version__",
    "burst",
]

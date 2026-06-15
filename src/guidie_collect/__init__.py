"""guidie-and-collect — guide workers, collect VLA training data.

Reference implementation of the data contract: schemas, guidance-plan parsing,
episode validation (incl. the force-channel invariant), and LeRobot export.

Public names are imported lazily (PEP 562) so that ``python -m
guidie_collect.validate`` does not re-import a submodule that the package
``__init__`` already pulled in.
"""

from typing import TYPE_CHECKING

__version__ = "0.0.1"

__all__ = ["GuidancePlan", "Episode", "ValidationReport", "validate_episode"]

if TYPE_CHECKING:  # pragma: no cover
    from .episode import Episode
    from .guidance import GuidancePlan
    from .validate import ValidationReport, validate_episode

_LAZY = {
    "GuidancePlan": "guidie_collect.guidance",
    "Episode": "guidie_collect.episode",
    "ValidationReport": "guidie_collect.validate",
    "validate_episode": "guidie_collect.validate",
}


def __getattr__(name: str):
    if name in _LAZY:
        import importlib

        module = importlib.import_module(_LAZY[name])
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

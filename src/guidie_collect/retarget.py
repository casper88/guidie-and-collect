"""Retargeting: master (human) action -> a specific embodiment's action space.

The master is deliberately embodiment-agnostic (docs/01, docs/04): it stores the
human representation (wrist 6DoF + finger joints + pinch). Retargeting to a
concrete robot is a *downstream / value-add* step — a buyer picks the adapter
for their hardware. This module defines the pluggable adapter interface and two
fully-implemented adapters:

- ``human`` (passthrough): keep the wrist 6DoF as-is (the universal default).
- ``parallel_jaw``: wrist 6DoF -> end-effector 6DoF + 1-DoF gripper width, with
  the gripper width derived from the thumb-index pinch distance. This is the
  UMI-style mapping that makes bare-hand demos usable on a parallel-jaw gripper.

Dexterous multi-finger retargeting (keypoint-vector / DexPilot-style
optimization) is intentionally out of scope here; it is delegated to external
tools such as ``dex-retargeting`` (see docs/02_RESEARCH_VLA.md). Adapters operate
on a single :class:`HandFrame` so they are pure, dependency-free, and testable
without decoded capture artifacts.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import Any

_WRIST_AXES = ("x", "y", "z", "roll", "pitch", "yaw")


@dataclass(frozen=True)
class HandFrame:
    """One timestep of the master human hand action.

    wrist_pose: (x, y, z, roll, pitch, yaw) in metres / radians.
    pinch:      thumb-tip to index-tip distance in metres (None if untracked).
    side:       "left" or "right".
    """

    wrist_pose: tuple[float, ...]
    pinch: float | None = None
    side: str = "right"

    def __post_init__(self) -> None:
        if len(self.wrist_pose) != 6:
            raise ValueError(f"wrist_pose must have 6 components, got {len(self.wrist_pose)}")


class EmbodimentAdapter(abc.ABC):
    """Maps a master :class:`HandFrame` to a target embodiment action vector."""

    embodiment: str

    @abc.abstractmethod
    def action_names(self) -> list[str]:
        """Ordered names of the produced action vector components."""

    @abc.abstractmethod
    def retarget(self, frame: HandFrame) -> list[float]:
        """Convert one master frame to this embodiment's action vector."""

    def feature_spec(self) -> dict[str, Any]:
        """LeRobot-style feature entry for the ``action`` produced by this adapter."""
        names = self.action_names()
        return {"action": {"dtype": "float32", "shape": [len(names)], "names": names}}


class PassthroughAdapter(EmbodimentAdapter):
    """Identity retarget: keep the human wrist 6DoF (embodiment-agnostic default)."""

    embodiment = "human"

    def action_names(self) -> list[str]:
        return [f"wrist_{a}" for a in _WRIST_AXES]

    def retarget(self, frame: HandFrame) -> list[float]:
        return list(frame.wrist_pose)


class ParallelJawAdapter(EmbodimentAdapter):
    """Wrist 6DoF -> end-effector 6DoF + 1-DoF gripper width (UMI-style).

    Gripper width is a linear, clamped map of the pinch distance:
        width = clip(pinch / human_open_distance * max_gripper_width,
                     0, max_gripper_width)
    """

    embodiment = "parallel_jaw"

    def __init__(self, max_gripper_width: float = 0.085, human_open_distance: float = 0.10):
        if max_gripper_width <= 0 or human_open_distance <= 0:
            raise ValueError("max_gripper_width and human_open_distance must be > 0")
        self.max_gripper_width = max_gripper_width
        self.human_open_distance = human_open_distance

    def action_names(self) -> list[str]:
        return [f"ee_{a}" for a in _WRIST_AXES] + ["gripper_width"]

    def retarget(self, frame: HandFrame) -> list[float]:
        if frame.pinch is None:
            raise ValueError("parallel_jaw retarget requires a pinch distance")
        raw = frame.pinch / self.human_open_distance * self.max_gripper_width
        width = max(0.0, min(self.max_gripper_width, raw))
        return list(frame.wrist_pose) + [round(width, 4)]


_ADAPTERS: dict[str, type[EmbodimentAdapter]] = {
    PassthroughAdapter.embodiment: PassthroughAdapter,
    ParallelJawAdapter.embodiment: ParallelJawAdapter,
}


def available_adapters() -> list[str]:
    return sorted(_ADAPTERS)


def get_adapter(name: str, **kwargs: Any) -> EmbodimentAdapter:
    try:
        cls = _ADAPTERS[name]
    except KeyError:
        raise ValueError(
            f"unknown embodiment '{name}'; available: {', '.join(available_adapters())}"
        ) from None
    return cls(**kwargs)


def retarget_sequence(adapter: EmbodimentAdapter, frames: list[HandFrame]) -> list[list[float]]:
    """Retarget a whole trajectory."""
    return [adapter.retarget(f) for f in frames]

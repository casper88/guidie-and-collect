"""Guidance plan = annotation schema.

A :class:`GuidancePlan` is what a factory authors to define a workflow. The same
object drives both the operator-facing guidance and the automatic labels
(language instructions, step segmentation, success criteria) attached to every
recorded :class:`~guidie_collect.episode.Episode`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .schema import GUIDANCE_PLAN_SCHEMA, load_json, validate_against_schema

# success_criterion types that can only be auto-verified with a force/contact
# channel. Drives the force-channel invariant in validate.py.
FORCE_DEPENDENT_CRITERIA = {"force_threshold", "click_detected"}


@dataclass(frozen=True)
class Step:
    step_id: str
    order: int
    type: str
    instruction: str
    target: dict[str, Any]
    success_criterion: dict[str, Any]

    @property
    def requires_force(self) -> bool:
        return self.success_criterion.get("type") in FORCE_DEPENDENT_CRITERIA


@dataclass(frozen=True)
class GuidancePlan:
    plan_id: str
    version: str
    task_name: str
    language: str
    steps: tuple[Step, ...]
    raw: dict[str, Any]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GuidancePlan":
        steps = tuple(
            Step(
                step_id=s["step_id"],
                order=s["order"],
                type=s["type"],
                instruction=s["instruction"],
                target=s["target"],
                success_criterion=s["success_criterion"],
            )
            for s in sorted(data["steps"], key=lambda s: s["order"])
        )
        return cls(
            plan_id=data["plan_id"],
            version=data["version"],
            task_name=data["task_name"],
            language=data.get("language", "zh-TW"),
            steps=steps,
            raw=data,
        )

    @classmethod
    def from_file(cls, path: str | Path) -> "GuidancePlan":
        return cls.from_dict(load_json(path))

    def validate_schema(self) -> list[str]:
        return validate_against_schema(self.raw, GUIDANCE_PLAN_SCHEMA)

    def step(self, step_id: str) -> Step | None:
        for s in self.steps:
            if s.step_id == step_id:
                return s
        return None

    @property
    def requires_force(self) -> bool:
        """True if ANY step's success depends on a force/contact channel."""
        return any(s.requires_force for s in self.steps)

    def language_labels(self) -> dict[str, str]:
        """step_id -> language instruction, the auto-generated language labels."""
        return {s.step_id: s.instruction for s in self.steps}

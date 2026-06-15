"""Episode = embodiment-agnostic master record of one guided execution."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .schema import EPISODE_SCHEMA, load_json, validate_against_schema


@dataclass(frozen=True)
class EpisodeStep:
    step_id: str
    instruction: str
    t_start: float
    t_end: float
    outcome: str
    peak_force_n: float | None = None


@dataclass(frozen=True)
class Episode:
    episode_id: str
    plan_id: str
    plan_version: str
    duration_s: float | None
    meta: dict[str, Any]
    streams: dict[str, Any]
    steps: tuple[EpisodeStep, ...]
    events: tuple[dict[str, Any], ...]
    raw: dict[str, Any]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Episode":
        steps = tuple(
            EpisodeStep(
                step_id=s["step_id"],
                instruction=s["instruction"],
                t_start=s["t_start"],
                t_end=s["t_end"],
                outcome=s["outcome"],
                peak_force_n=s.get("peak_force_n"),
            )
            for s in data.get("steps", [])
        )
        return cls(
            episode_id=data["episode_id"],
            plan_id=data["plan_id"],
            plan_version=data["plan_version"],
            duration_s=data.get("duration_s"),
            meta=data.get("meta", {}),
            streams=data.get("streams", {}),
            steps=steps,
            events=tuple(data.get("events", [])),
            raw=data,
        )

    @classmethod
    def from_file(cls, path: str | Path) -> "Episode":
        return cls.from_dict(load_json(path))

    def validate_schema(self) -> list[str]:
        return validate_against_schema(self.raw, EPISODE_SCHEMA)

    @property
    def has_force_stream(self) -> bool:
        force = self.streams.get("force")
        return bool(force and force.get("uri"))

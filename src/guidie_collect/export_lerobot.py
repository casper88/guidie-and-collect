"""Export the embodiment-agnostic master Episode to a LeRobot-style dataset.

LeRobot is the de-facto fine-tuning format in 2025-2026 (openpi/π0, GR00T N1.5,
SmolVLA all consume it), so we export to it rather than inventing a training
format. We deliberately keep the rich master upstream (see docs/04) and *derive*
LeRobot here.

This is a SKELETON: it builds the LeRobot-shaped metadata/feature layout and the
per-timestep frame plan, but does not yet decode MP4s or write Parquet (that
needs the real captured artifacts + the `lerobot` package). The mapping decisions
it encodes — fixed resample rate, which channels become `action` vs
`observation`, force as a first-class feature — are the load-bearing part.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .episode import Episode
from .guidance import GuidancePlan


@dataclass
class LeRobotFeatureSpec:
    """A minimal description of the LeRobot feature layout we target."""

    fps: int
    features: dict[str, dict[str, Any]] = field(default_factory=dict)


def build_feature_spec(episode: Episode, fps: int = 30) -> LeRobotFeatureSpec:
    """Decide the LeRobot feature layout from the episode's available streams.

    Action source (embodiment-agnostic default): right/left wrist 6DoF from
    hand_pose. Buyers retargeting to a specific robot replace this with their
    end-effector/joint action. Force/contact is exported as its own feature —
    most public datasets drop it; we keep it.
    """
    features: dict[str, dict[str, Any]] = {}

    if "egocentric_rgb" in episode.streams:
        features["observation.images.ego"] = {"dtype": "video", "source": "egocentric_rgb"}
    if "external_rgb" in episode.streams:
        features["observation.images.external"] = {"dtype": "video", "source": "external_rgb"}
    if "hand_pose" in episode.streams:
        # Master action = human wrist/hand pose; retargeting is a downstream step.
        features["action"] = {"dtype": "float32", "source": "hand_pose", "space": "human_wrist_6dof"}
        features["observation.state.hand"] = {"dtype": "float32", "source": "hand_pose"}
    if "object_poses" in episode.streams:
        features["observation.state.objects"] = {"dtype": "float32", "source": "object_poses"}
    if episode.has_force_stream:
        features["observation.force"] = {"dtype": "float32", "source": "force"}

    return LeRobotFeatureSpec(fps=fps, features=features)


def build_language_task(episode: Episode, plan: GuidancePlan) -> str:
    """Top-level language string for the episode (LeRobot 'task')."""
    return plan.task_name


def to_lerobot_plan(episode: Episode, plan: GuidancePlan, fps: int = 30) -> dict[str, Any]:
    """Return a JSON-able description of how this episode maps onto LeRobot.

    A real exporter consumes this plan to write the dataset; here we surface it
    so the mapping is testable and reviewable without the heavy dependencies.
    """
    spec = build_feature_spec(episode, fps=fps)
    n_frames = int(round((episode.duration_s or 0.0) * fps))

    # Per-step language sub-segmentation, derived from the guidance plan.
    segments = [
        {
            "step_id": st.step_id,
            "task": plan.step(st.step_id).instruction if plan.step(st.step_id) else st.instruction,
            "frame_start": int(round(st.t_start * fps)),
            "frame_end": int(round(st.t_end * fps)),
            "outcome": st.outcome,
        }
        for st in episode.steps
    ]

    return {
        "episode_id": episode.episode_id,
        "fps": fps,
        "num_frames": n_frames,
        "task": build_language_task(episode, plan),
        "features": spec.features,
        "segments": segments,
        "has_force": episode.has_force_stream,
        "source_format": "guidie-collect/master/v0",
        "target_format": "lerobot",
    }

"""Export the embodiment-agnostic master Episode to a LeRobot-style dataset.

LeRobot is the de-facto fine-tuning format in 2025-2026 (openpi/π0, GR00T N1.5,
SmolVLA all consume it), so we export to it rather than inventing a training
format. We keep the rich master upstream (docs/04) and *derive* LeRobot here.

What this module DOES now: build and write the LeRobot ``meta/`` directory —
``info.json`` (feature schema + totals), ``tasks.jsonl`` (language tasks, taken
straight from the guidance plan), ``episodes.jsonl`` (per-episode length + tasks),
plus a G&C-extension ``segments.jsonl`` that preserves the auto-derived per-step
language segmentation (our differentiator).

What it does NOT do yet: decode MP4s or write the per-timestep data Parquet —
that needs the real captured artifacts and a pinned ``lerobot`` version. The
load-bearing decisions (which channel becomes ``action`` vs ``observation``,
force as a first-class feature, language from the guidance plan) live here.

The LeRobot layout targeted is v2.1-style; pin the exact schema when wiring real
training, since the upstream format still evolves.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .episode import Episode
from .guidance import GuidancePlan

CODEBASE_VERSION = "v2.1"
ROBOT_TYPE = "human_master"  # embodiment-agnostic; buyers retarget downstream

_WRIST_AXES = ["x", "y", "z", "roll", "pitch", "yaw"]


# --------------------------------------------------------------------------- #
# Feature spec (kept stable: used by to_lerobot_plan and the metadata writer)
# --------------------------------------------------------------------------- #
@dataclass
class LeRobotFeatureSpec:
    fps: int
    features: dict[str, dict[str, Any]] = field(default_factory=dict)


def build_feature_spec(episode: Episode, fps: int = 30) -> LeRobotFeatureSpec:
    """Decide the LeRobot feature layout from the episode's available streams.

    Action source (embodiment-agnostic default): wrist 6DoF from hand_pose.
    Buyers retargeting to a specific robot replace this with their
    end-effector/joint action. Force/contact is exported as its own feature —
    most public datasets drop it; we keep it.
    """
    features: dict[str, dict[str, Any]] = {}
    if "egocentric_rgb" in episode.streams:
        features["observation.images.ego"] = {"dtype": "video", "source": "egocentric_rgb"}
    if "external_rgb" in episode.streams:
        features["observation.images.external"] = {"dtype": "video", "source": "external_rgb"}
    if "hand_pose" in episode.streams:
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
    """A JSON-able description of how one episode maps onto LeRobot (testable)."""
    spec = build_feature_spec(episode, fps=fps)
    n_frames = int(round((episode.duration_s or 0.0) * fps))
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


# --------------------------------------------------------------------------- #
# LeRobot metadata (info.json / tasks.jsonl / episodes.jsonl / segments.jsonl)
# --------------------------------------------------------------------------- #
def _lerobot_features(episode: Episode, plan: GuidancePlan) -> dict[str, dict[str, Any]]:
    """Concrete LeRobot feature schema (dtype/shape/names) for ``info.json``.

    Shapes are best-effort and documented: video from declared resolution,
    force from the declared source count, objects from the plan. Vector shapes
    for hand/wrist are nominal and finalized when the data Parquet schema is
    pinned.
    """
    feats: dict[str, dict[str, Any]] = {}

    def video(stream_key: str, name: str) -> None:
        res = episode.streams.get(stream_key, {}).get("resolution")
        shape = [res[1], res[0], 3] if res else [0, 0, 3]  # resolution is [W, H]
        feats[name] = {"dtype": "video", "shape": shape, "names": ["height", "width", "channel"]}

    if "egocentric_rgb" in episode.streams:
        video("egocentric_rgb", "observation.images.ego")
    if "external_rgb" in episode.streams:
        video("external_rgb", "observation.images.external")

    if "hand_pose" in episode.streams:
        names = [f"{side}_wrist_{ax}" for side in ("left", "right") for ax in _WRIST_AXES]
        feats["action"] = {"dtype": "float32", "shape": [len(names)], "names": names}
        feats["observation.state.hand"] = {"dtype": "float32", "shape": [2, 26, 3], "names": None}

    if "object_poses" in episode.streams:
        feats["observation.state.objects"] = {
            "dtype": "float32",
            "shape": [len(plan.raw.get("objects", [])), 7],  # pose: xyz + quat
            "names": None,
        }

    if episode.has_force_stream:
        sources = [s["source_id"] for s in episode.streams["force"].get("sources", [])]
        feats["observation.force"] = {
            "dtype": "float32",
            "shape": [len(sources)],
            "names": sources or None,
        }

    feats["timestamp"] = {"dtype": "float32", "shape": [1], "names": None}
    return feats


def build_metadata(
    episodes: list[Episode],
    plan: GuidancePlan,
    fps: int = 30,
) -> dict[str, Any]:
    """Build (but don't write) the LeRobot meta structures from master episodes."""
    # Task table: top-level task first, then every distinct step instruction.
    task_strings: list[str] = [plan.task_name]
    for ep in episodes:
        for st in ep.steps:
            if st.instruction not in task_strings:
                task_strings.append(st.instruction)
    task_index = {t: i for i, t in enumerate(task_strings)}

    episodes_index: list[dict[str, Any]] = []
    segments: list[dict[str, Any]] = []
    total_frames = 0
    total_videos = 0

    for ep_idx, ep in enumerate(episodes):
        n_frames = int(round((ep.duration_s or 0.0) * fps))
        total_frames += n_frames
        total_videos += sum(1 for k in ("egocentric_rgb", "external_rgb") if k in ep.streams)
        ep_tasks = list(dict.fromkeys(st.instruction for st in ep.steps))
        episodes_index.append({"episode_index": ep_idx, "tasks": ep_tasks, "length": n_frames})
        for st in ep.steps:
            segments.append(
                {
                    "episode_index": ep_idx,
                    "step_id": st.step_id,
                    "task_index": task_index[st.instruction],
                    "frame_start": int(round(st.t_start * fps)),
                    "frame_end": int(round(st.t_end * fps)),
                    "outcome": st.outcome,
                }
            )

    # Feature schema is the union across episodes (use the richest episode).
    features: dict[str, Any] = {}
    for ep in episodes:
        for name, spec in _lerobot_features(ep, plan).items():
            features.setdefault(name, spec)

    info = {
        "codebase_version": CODEBASE_VERSION,
        "robot_type": ROBOT_TYPE,
        "total_episodes": len(episodes),
        "total_frames": total_frames,
        "total_tasks": len(task_strings),
        "total_videos": total_videos,
        "fps": fps,
        "splits": {"train": f"0:{len(episodes)}"},
        "data_path": "data/chunk-000/episode_{episode_index:06d}.parquet",
        "video_path": "videos/chunk-000/{video_key}/episode_{episode_index:06d}.mp4",
        "features": features,
    }
    tasks = [{"task_index": i, "task": t} for i, t in enumerate(task_strings)]
    return {"info": info, "tasks": tasks, "episodes": episodes_index, "segments": segments}


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_lerobot_metadata(
    out_dir: str | Path,
    episodes: list[Episode],
    plan: GuidancePlan,
    fps: int = 30,
) -> dict[str, Any]:
    """Write the LeRobot ``meta/`` directory and return the built structures."""
    meta = build_metadata(episodes, plan, fps=fps)
    meta_dir = Path(out_dir) / "meta"
    meta_dir.mkdir(parents=True, exist_ok=True)
    with open(meta_dir / "info.json", "w", encoding="utf-8") as fh:
        json.dump(meta["info"], fh, ensure_ascii=False, indent=2)
    _write_jsonl(meta_dir / "tasks.jsonl", meta["tasks"])
    _write_jsonl(meta_dir / "episodes.jsonl", meta["episodes"])
    _write_jsonl(meta_dir / "segments.jsonl", meta["segments"])  # G&C extension
    return meta


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export master episodes to LeRobot metadata.")
    parser.add_argument("plan", help="guidance plan JSON")
    parser.add_argument("episodes", nargs="+", help="one or more master episode JSON files")
    parser.add_argument("-o", "--out", required=True, help="output dataset directory")
    parser.add_argument("--fps", type=int, default=30)
    args = parser.parse_args(argv)

    plan = GuidancePlan.from_file(args.plan)
    eps = [Episode.from_file(p) for p in args.episodes]
    meta = write_lerobot_metadata(args.out, eps, plan, fps=args.fps)
    info = meta["info"]
    print(f"Wrote LeRobot metadata to {args.out}/meta/")
    print(
        f"  episodes={info['total_episodes']} frames={info['total_frames']} "
        f"tasks={info['total_tasks']} features={len(info['features'])}"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())

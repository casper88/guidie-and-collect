"""Tests for the LeRobot metadata exporter."""

import json
from pathlib import Path

from guidie_collect.episode import Episode
from guidie_collect.export_lerobot import build_metadata, write_lerobot_metadata
from guidie_collect.guidance import GuidancePlan
from guidie_collect.retarget import get_adapter

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = REPO_ROOT / "schema" / "examples"
PLAN_PATH = EXAMPLES / "plug_insertion.plan.json"
EPISODE_PATH = EXAMPLES / "plug_insertion.episode.json"

FPS = 30


def _meta():
    plan = GuidancePlan.from_file(PLAN_PATH)
    ep = Episode.from_file(EPISODE_PATH)
    return build_metadata([ep], plan, fps=FPS)


def test_info_totals_and_features():
    meta = _meta()
    info = meta["info"]
    assert info["total_episodes"] == 1
    assert info["total_frames"] == int(round(14.2 * FPS))
    assert info["fps"] == FPS
    assert info["robot_type"] == "human_master"
    # force is a first-class feature; action derived from hand pose
    assert "observation.force" in info["features"]
    assert "action" in info["features"]
    # force feature shape matches the declared source count, names = source ids
    assert info["features"]["observation.force"]["shape"] == [2]
    assert info["features"]["observation.force"]["names"] == ["socket_J1", "socket_J3"]
    # ego video shape derived from resolution [W=1280, H=960] -> [H, W, C]
    assert info["features"]["observation.images.ego"]["shape"] == [960, 1280, 3]


def test_tasks_from_guidance_plan():
    meta = _meta()
    tasks = [t["task"] for t in meta["tasks"]]
    # top-level task name first, then the per-step language instructions
    assert tasks[0] == "依序插接前面板連接器"
    assert any(t.startswith("把電源接頭") for t in tasks)
    assert any(t.startswith("把接地線") for t in tasks)


def test_episodes_and_segments():
    meta = _meta()
    assert len(meta["episodes"]) == 1
    assert meta["episodes"][0]["length"] == int(round(14.2 * FPS))
    # one segment per step, each referencing a valid task_index
    assert len(meta["segments"]) == 3
    n_tasks = len(meta["tasks"])
    for seg in meta["segments"]:
        assert 0 <= seg["task_index"] < n_tasks
        assert seg["frame_start"] < seg["frame_end"]


def test_embodiment_override_produces_derived_sku():
    plan = GuidancePlan.from_file(PLAN_PATH)
    ep = Episode.from_file(EPISODE_PATH)
    # raw master: human action space
    raw = build_metadata([ep], plan, fps=FPS)
    assert raw["info"]["robot_type"] == "human_master"
    assert raw["info"]["features"]["action"]["shape"] == [12]  # two-hand wrist
    # retargeted SKU: parallel-jaw action space
    pj = build_metadata([ep], plan, fps=FPS, adapter=get_adapter("parallel_jaw"))
    assert pj["info"]["robot_type"] == "parallel_jaw"
    assert pj["info"]["features"]["action"]["shape"] == [7]
    assert pj["info"]["features"]["action"]["names"][-1] == "gripper_width"
    # everything else (tasks/segments/force) is unchanged by retargeting
    assert pj["tasks"] == raw["tasks"]
    assert "observation.force" in pj["info"]["features"]


def test_write_metadata_files(tmp_path):
    plan = GuidancePlan.from_file(PLAN_PATH)
    ep = Episode.from_file(EPISODE_PATH)
    write_lerobot_metadata(tmp_path, [ep], plan, fps=FPS)

    meta_dir = tmp_path / "meta"
    assert (meta_dir / "info.json").exists()
    for name in ("tasks.jsonl", "episodes.jsonl", "segments.jsonl"):
        lines = (meta_dir / name).read_text(encoding="utf-8").strip().splitlines()
        assert lines, f"{name} is empty"
        for line in lines:  # every line is valid JSON
            json.loads(line)
    # info.json round-trips
    info = json.loads((meta_dir / "info.json").read_text(encoding="utf-8"))
    assert info["total_frames"] == int(round(14.2 * FPS))

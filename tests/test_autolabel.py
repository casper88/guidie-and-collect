"""Tests for the auto-labeling engine: raw capture -> labeled master episode."""

import json
from pathlib import Path

from guidie_collect.autolabel import build_episode_from_capture
from guidie_collect.guidance import GuidancePlan
from guidie_collect.schema import load_json
from guidie_collect.validate import validate_episode

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = REPO_ROOT / "schema" / "examples"
PLAN_PATH = EXAMPLES / "plug_insertion.plan.json"
CAPTURE_PATH = EXAMPLES / "plug_insertion.capture.json"


def _build():
    plan = GuidancePlan.from_file(PLAN_PATH)
    capture = load_json(CAPTURE_PATH)
    return plan, capture, build_episode_from_capture(plan, capture)


def test_autolabel_segments_and_language():
    _, _, ep = _build()
    assert [s["step_id"] for s in ep["steps"]] == ["s1", "s2", "s3"]
    # language instruction copied from the plan, no human annotation
    assert ep["steps"][0]["instruction"].startswith("把電源接頭")
    # segmentation taken from start/terminal events
    assert ep["steps"][0]["t_start"] == 2.40
    assert ep["steps"][0]["t_end"] == 6.85


def test_autolabel_peak_force_only_for_force_threshold():
    _, _, ep = _build()
    by_id = {s["step_id"]: s for s in ep["steps"]}
    # s1 (force_threshold) -> peak from socket_J1 window max = 37.4
    assert by_id["s1"]["peak_force_n"] == 37.4
    # s2 (click_detected) -> no peak force
    assert "peak_force_n" not in by_id["s2"]
    # s3 (force_threshold) -> peak from socket_J3 window max = 23.6
    assert by_id["s3"]["peak_force_n"] == 23.6


def test_autolabel_marks_correction():
    _, _, ep = _build()
    by_id = {s["step_id"]: s for s in ep["steps"]}
    # s3 had a 'correction' event -> outcome corrected
    assert by_id["s3"]["outcome"] == "corrected"
    assert by_id["s1"]["outcome"] == "success"


def test_autolabeled_episode_passes_validation(tmp_path):
    _, _, ep = _build()
    # produced episode must NOT carry raw force_samples (schema forbids extra keys)
    assert "force_samples" not in ep
    out = tmp_path / "ep_0002.episode.json"
    out.write_text(json.dumps(ep), encoding="utf-8")
    report = validate_episode(out, PLAN_PATH)
    assert report.ok, f"unexpected errors: {report.errors}"

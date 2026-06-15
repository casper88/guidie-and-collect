"""Tests for the data contract: parsing, validation invariants, LeRobot export."""

import copy
import json
from pathlib import Path

import pytest

from guidie_collect.episode import Episode
from guidie_collect.export_lerobot import to_lerobot_plan
from guidie_collect.guidance import GuidancePlan
from guidie_collect.validate import validate_episode

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = REPO_ROOT / "schema" / "examples"
PLAN_PATH = EXAMPLES / "plug_insertion.plan.json"
EPISODE_PATH = EXAMPLES / "plug_insertion.episode.json"


def test_guidance_plan_parsing():
    plan = GuidancePlan.from_file(PLAN_PATH)
    assert plan.plan_id == "plug_insertion_v1"
    assert len(plan.steps) == 3
    # steps come out ordered
    assert [s.order for s in plan.steps] == [1, 2, 3]
    # s1 (force_threshold) and s2 (click_detected) are force-dependent
    assert plan.requires_force is True
    assert plan.step("s1").requires_force is True
    assert plan.language_labels()["s1"].startswith("把電源接頭")


def test_example_episode_is_valid():
    report = validate_episode(EPISODE_PATH, PLAN_PATH)
    assert report.ok, f"unexpected errors: {report.errors}"


def test_force_channel_invariant_warns_when_force_missing(tmp_path):
    data = json.loads(EPISODE_PATH.read_text(encoding="utf-8"))
    del data["streams"]["force"]  # contact-rich plan but no force stream
    ep_file = tmp_path / "no_force.episode.json"
    ep_file.write_text(json.dumps(data), encoding="utf-8")

    report = validate_episode(ep_file, PLAN_PATH)
    assert report.ok  # still valid, but...
    assert any("force" in w for w in report.warnings), report.warnings


def test_unknown_step_is_error(tmp_path):
    data = json.loads(EPISODE_PATH.read_text(encoding="utf-8"))
    data["steps"][0]["step_id"] = "does_not_exist"
    ep_file = tmp_path / "bad_step.episode.json"
    ep_file.write_text(json.dumps(data), encoding="utf-8")

    report = validate_episode(ep_file, PLAN_PATH)
    assert not report.ok
    assert any("not defined in guidance plan" in e for e in report.errors)


def test_missing_consent_is_error(tmp_path):
    data = json.loads(EPISODE_PATH.read_text(encoding="utf-8"))
    data["meta"].pop("consent_ref")
    ep_file = tmp_path / "no_consent.episode.json"
    ep_file.write_text(json.dumps(data), encoding="utf-8")

    report = validate_episode(ep_file, PLAN_PATH)
    assert not report.ok
    # Either the schema (required) or the governance invariant catches it.
    assert any("consent" in e.lower() for e in report.errors)


def test_bad_time_order_is_error(tmp_path):
    data = json.loads(EPISODE_PATH.read_text(encoding="utf-8"))
    data["steps"][0]["t_start"] = 9.0
    data["steps"][0]["t_end"] = 1.0
    ep_file = tmp_path / "bad_time.episode.json"
    ep_file.write_text(json.dumps(data), encoding="utf-8")

    report = validate_episode(ep_file, PLAN_PATH)
    assert not report.ok
    assert any("t_start < t_end" in e for e in report.errors)


def test_lerobot_export_plan():
    episode = Episode.from_file(EPISODE_PATH)
    plan = GuidancePlan.from_file(PLAN_PATH)
    out = to_lerobot_plan(episode, plan, fps=30)

    assert out["target_format"] == "lerobot"
    assert out["has_force"] is True
    assert "observation.force" in out["features"]
    assert "action" in out["features"]
    # language segmentation derived from the guidance plan
    assert len(out["segments"]) == 3
    assert out["segments"][0]["task"].startswith("把電源接頭")
    assert out["num_frames"] == int(round(14.2 * 30))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))

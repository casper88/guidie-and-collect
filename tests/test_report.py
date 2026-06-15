"""Tests for the dataset QA / statistics report."""

import json
from pathlib import Path

from guidie_collect.report import scan

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = REPO_ROOT / "schema" / "examples"
PLAN_PATH = EXAMPLES / "plug_insertion.plan.json"
EPISODE_PATH = EXAMPLES / "plug_insertion.episode.json"


def _degraded_copy(tmp_path: Path) -> Path:
    """Same episode but with the force channel and peak forces stripped."""
    data = json.loads(EPISODE_PATH.read_text(encoding="utf-8"))
    data["episode_id"] = "ep_degraded"
    del data["streams"]["force"]
    for st in data["steps"]:
        st.pop("peak_force_n", None)
    out = tmp_path / "ep_degraded.episode.json"
    out.write_text(json.dumps(data), encoding="utf-8")
    return out


def test_full_coverage_example():
    rep = scan(PLAN_PATH, [str(EPISODE_PATH)])
    assert rep.total_episodes == 1
    assert rep.valid_episodes == 1
    # s1 and s3 are force_threshold and both carry a peak force -> 100%
    assert rep.force_threshold_steps == 2
    assert rep.force_covered_steps == 2
    assert rep.force_coverage == 1.0
    assert rep.outcomes["success"] == 3
    assert rep.distinct_tasks == 3


def test_degraded_episode_drops_coverage(tmp_path):
    degraded = _degraded_copy(tmp_path)
    rep = scan(PLAN_PATH, [str(degraded)])
    assert rep.force_coverage == 0.0
    # still schema-valid, but the force invariant raises a warning
    assert rep.episodes_with_warnings == 1
    assert rep.episodes[0].has_force is False


def test_mixed_dataset_aggregates(tmp_path):
    degraded = _degraded_copy(tmp_path)
    rep = scan(PLAN_PATH, [str(EPISODE_PATH), str(degraded)])
    assert rep.total_episodes == 2
    assert rep.force_threshold_steps == 4
    assert rep.force_covered_steps == 2
    assert rep.force_coverage == 0.5
    assert "force coverage" in rep.render()


def test_directory_resolution(tmp_path):
    # one good copy in a directory
    data = json.loads(EPISODE_PATH.read_text(encoding="utf-8"))
    (tmp_path / "a.episode.json").write_text(json.dumps(data), encoding="utf-8")
    rep = scan(PLAN_PATH, [str(tmp_path)])
    assert rep.total_episodes == 1
    assert rep.to_dict()["force_coverage"] == 1.0

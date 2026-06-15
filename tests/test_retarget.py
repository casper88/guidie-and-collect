"""Tests for embodiment retargeting adapters."""

import pytest

from guidie_collect.retarget import (
    HandFrame,
    ParallelJawAdapter,
    available_adapters,
    get_adapter,
    retarget_sequence,
)

WRIST = (0.1, 0.2, 0.3, 0.0, 1.57, 0.0)


def test_handframe_rejects_bad_wrist():
    with pytest.raises(ValueError):
        HandFrame(wrist_pose=(0.0, 0.0, 0.0))  # not 6 components


def test_passthrough_is_identity():
    adapter = get_adapter("human")
    frame = HandFrame(wrist_pose=WRIST, pinch=0.05)
    assert adapter.retarget(frame) == list(WRIST)
    assert adapter.action_names() == [
        "wrist_x", "wrist_y", "wrist_z", "wrist_roll", "wrist_pitch", "wrist_yaw"
    ]


def test_parallel_jaw_maps_pinch_to_width():
    adapter = ParallelJawAdapter(max_gripper_width=0.085, human_open_distance=0.10)
    # fully open pinch -> max width
    assert adapter.retarget(HandFrame(WRIST, pinch=0.10))[-1] == 0.085
    # closed -> 0
    assert adapter.retarget(HandFrame(WRIST, pinch=0.0))[-1] == 0.0
    # half open -> half width
    assert adapter.retarget(HandFrame(WRIST, pinch=0.05))[-1] == pytest.approx(0.0425)
    # over-open is clamped
    assert adapter.retarget(HandFrame(WRIST, pinch=0.20))[-1] == 0.085
    # action = 6 ee dofs + width
    out = adapter.retarget(HandFrame(WRIST, pinch=0.05))
    assert out[:6] == list(WRIST)
    assert len(out) == 7


def test_parallel_jaw_requires_pinch():
    adapter = get_adapter("parallel_jaw")
    with pytest.raises(ValueError):
        adapter.retarget(HandFrame(WRIST, pinch=None))


def test_registry_and_unknown():
    assert set(available_adapters()) == {"human", "parallel_jaw"}
    with pytest.raises(ValueError):
        get_adapter("franka_dexhand_9000")


def test_feature_spec_shapes():
    assert get_adapter("human").feature_spec()["action"]["shape"] == [6]
    pj = get_adapter("parallel_jaw").feature_spec()["action"]
    assert pj["shape"] == [7]
    assert pj["names"][-1] == "gripper_width"


def test_retarget_sequence():
    adapter = get_adapter("parallel_jaw")
    frames = [HandFrame(WRIST, pinch=p) for p in (0.0, 0.05, 0.10)]
    out = retarget_sequence(adapter, frames)
    assert [row[-1] for row in out] == [0.0, pytest.approx(0.0425), 0.085]

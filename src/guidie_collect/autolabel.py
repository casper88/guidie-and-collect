"""Auto-labeling: raw capture + guidance plan -> labeled master Episode.

This is the project's core thesis made executable ("guidance plan IS the
annotation schema", docs/01 & docs/05). The MR runtime emits a *raw capture* —
stream references plus a flat list of discrete events (step_start / step_success
/ step_fail / correction) and, for the pipeline/tests, optional inline force
samples. From that, together with the guidance plan, we derive every training
label with no human annotation:

- temporal segmentation  (t_start / t_end per step, from start/terminal events)
- language instruction   (copied from the plan step)
- outcome                (success / fail / corrected)
- peak force             (computed from the force channel for force_threshold steps)

In production the force samples live in the force Parquet; we accept them inline
in the capture so the whole pipeline is testable without binary artifacts. The
produced episode deliberately omits ``force_samples`` so it conforms to
``episode.schema.json`` (which forbids unknown top-level keys).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .guidance import GuidancePlan
from .schema import load_json

_TERMINAL = {"step_success": "success", "step_fail": "fail"}


def _compute_peak_force(
    point_id: str | None,
    t_start: float,
    t_end: float,
    force_samples: list[dict[str, Any]],
) -> float | None:
    """Max |value| within [t_start, t_end], preferring the target point's source."""
    if not force_samples:
        return None
    in_window = [s for s in force_samples if t_start - 1e-9 <= s["t"] <= t_end + 1e-9]
    if not in_window:
        return None
    relevant = [s for s in in_window if point_id and point_id in str(s.get("source_id", ""))]
    pool = relevant or in_window
    return max(abs(s["value"]) for s in pool)


def build_steps(
    plan: GuidancePlan,
    events: list[dict[str, Any]],
    force_samples: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Derive labeled steps from raw events + the guidance plan."""
    force_samples = force_samples or []
    steps: list[dict[str, Any]] = []
    corrected: set[str] = set()
    open_step: dict[str, Any] | None = None

    for ev in sorted(events, key=lambda e: e["t"]):
        etype = ev["type"]
        sid = ev.get("step_id")

        if etype == "step_start":
            open_step = {"step_id": sid, "t_start": ev["t"]}
        elif etype == "correction":
            corrected.add(sid)
        elif etype in _TERMINAL:
            t_start = open_step["t_start"] if open_step and open_step["step_id"] == sid else ev["t"]
            outcome = "corrected" if sid in corrected else _TERMINAL[etype]
            pstep = plan.step(sid)
            rec: dict[str, Any] = {
                "step_id": sid,
                "instruction": pstep.instruction if pstep else "",
                "t_start": round(t_start, 3),
                "t_end": round(ev["t"], 3),
                "outcome": outcome,
            }
            # Peak force is meaningful only for force_threshold criteria.
            if pstep and pstep.success_criterion.get("type") == "force_threshold":
                peak = _compute_peak_force(
                    pstep.target.get("point_id"), t_start, ev["t"], force_samples
                )
                if peak is not None:
                    rec["peak_force_n"] = round(peak, 3)
            steps.append(rec)
            open_step = None

    return steps


def build_episode_from_capture(plan: GuidancePlan, capture: dict[str, Any]) -> dict[str, Any]:
    """Turn a raw capture into a labeled, schema-conforming master episode dict."""
    episode: dict[str, Any] = {
        "episode_id": capture["episode_id"],
        "plan_id": capture["plan_id"],
        "plan_version": capture["plan_version"],
        "meta": capture["meta"],
        "streams": capture.get("streams", {}),
        "steps": build_steps(plan, capture.get("events", []), capture.get("force_samples")),
    }
    if "duration_s" in capture:
        episode["duration_s"] = capture["duration_s"]
    if "events" in capture:
        episode["events"] = capture["events"]
    return episode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Auto-label a raw capture into a master episode.")
    parser.add_argument("plan", help="guidance plan JSON")
    parser.add_argument("capture", help="raw capture JSON")
    parser.add_argument("-o", "--out", help="write episode JSON here (else stdout)")
    args = parser.parse_args(argv)

    plan = GuidancePlan.from_file(args.plan)
    capture = load_json(args.capture)
    episode = build_episode_from_capture(plan, capture)
    text = json.dumps(episode, ensure_ascii=False, indent=2)

    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
        # Validate the freshly written episode against schema + invariants.
        from .validate import validate_episode

        report = validate_episode(args.out, args.plan)
        print(f"Wrote {args.out}")
        print(report)
        return 0 if report.ok else 1

    print(text)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())

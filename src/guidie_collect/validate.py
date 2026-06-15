"""Validate an Episode against its schema AND the cross-contract invariants.

The invariants are where the project's research conclusions become enforceable
rules — most importantly the *force-channel invariant*: a contact-rich insertion
plan that records no force/contact stream produces low-value data, so we flag it.

CLI::

    python -m guidie_collect.validate schema/examples/plug_insertion.episode.json
    python -m guidie_collect.validate <episode.json> --plan <plan.json>
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path

from .episode import Episode
from .guidance import GuidancePlan


@dataclass
class ValidationReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        lines = []
        for e in self.errors:
            lines.append(f"  ERROR  {e}")
        for w in self.warnings:
            lines.append(f"  WARN   {w}")
        if not lines:
            lines.append("  OK")
        return "\n".join(lines)


def _resolve_plan(episode: Episode, episode_path: Path, plan_path: Path | None) -> Path | None:
    if plan_path is not None:
        return plan_path
    # Convention: look next to the episode for "<plan_id>.plan.json".
    candidate = episode_path.parent / f"{episode.plan_id}.plan.json"
    return candidate if candidate.exists() else None


def validate_episode(
    episode_path: str | Path,
    plan_path: str | Path | None = None,
) -> ValidationReport:
    report = ValidationReport()
    episode_path = Path(episode_path)
    episode = Episode.from_file(episode_path)

    # 1. Episode JSON-schema validation.
    report.errors.extend(episode.validate_schema())

    # 2. Resolve + validate the guidance plan (the annotation contract).
    resolved = _resolve_plan(episode, episode_path, Path(plan_path) if plan_path else None)
    if resolved is None or not resolved.exists():
        report.errors.append(
            f"contract: could not resolve guidance plan for plan_id="
            f"'{episode.plan_id}' (pass --plan or place <plan_id>.plan.json beside the episode)"
        )
        return report

    plan = GuidancePlan.from_file(resolved)
    report.errors.extend(plan.validate_schema())

    # 3. plan_id / plan_version consistency.
    if episode.plan_id != plan.plan_id:
        report.errors.append(
            f"contract: episode.plan_id '{episode.plan_id}' != plan.plan_id '{plan.plan_id}'"
        )
    if episode.plan_version != plan.version:
        report.warnings.append(
            f"contract: episode.plan_version '{episode.plan_version}' != plan.version "
            f"'{plan.version}' (version drift)"
        )

    # 4. Every episode step must exist in the plan.
    for st in episode.steps:
        if plan.step(st.step_id) is None:
            report.errors.append(f"contract: step '{st.step_id}' not defined in guidance plan")

    # 5. Temporal sanity.
    for st in episode.steps:
        if not (st.t_start < st.t_end):
            report.errors.append(f"time: step '{st.step_id}' requires t_start < t_end")
        if episode.duration_s is not None and st.t_end > episode.duration_s + 1e-6:
            report.errors.append(
                f"time: step '{st.step_id}' t_end {st.t_end} exceeds duration {episode.duration_s}"
            )

    # 6. Non-overlap, except explicit retries flagged 'corrected'.
    ordered = sorted(episode.steps, key=lambda s: s.t_start)
    for prev, cur in zip(ordered, ordered[1:]):
        if cur.t_start < prev.t_end - 1e-6 and cur.outcome != "corrected":
            report.warnings.append(
                f"time: steps '{prev.step_id}' and '{cur.step_id}' overlap "
                f"(mark a retry as outcome='corrected' if intentional)"
            )

    # 7. FORCE-CHANNEL INVARIANT — the moat, enforced.
    if plan.requires_force and not episode.has_force_stream:
        report.warnings.append(
            "force: plan has force_threshold/click_detected steps but the episode "
            "records no 'force' stream — this data is LOW VALUE for contact-rich "
            "insertion (see docs/05_DATA_SPEC.md invariant 4)"
        )

    # 8. Governance: consent chain is mandatory for sellable data.
    if not episode.meta.get("consent_ref"):
        report.errors.append("governance: meta.consent_ref is required (consent chain)")

    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a G&C episode.")
    parser.add_argument("episode", help="path to an episode JSON file")
    parser.add_argument("--plan", help="path to the guidance plan JSON (optional)")
    args = parser.parse_args(argv)

    report = validate_episode(args.episode, args.plan)
    print(f"Validating {args.episode}")
    print(report)
    return 0 if report.ok else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())

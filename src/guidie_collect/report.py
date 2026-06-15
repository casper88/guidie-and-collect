"""Dataset QA / statistics report.

Scans a set of master episodes against their guidance plan and produces a quality
scorecard. The headline metric is **force coverage** — the fraction of
force-threshold steps that actually carry a measured peak force. This turns the
project's moat ("force/contact is what makes contact-rich insertion data
valuable", docs/01) into a number you can track across heterogeneous sites and
show to a buyer.

Also reports validity (via the cross-contract validator), outcome distribution
(success / fail / corrected), missing-channel flags, and language/task coverage.

CLI::

    python -m guidie_collect.report <plan.json> <episode.json> [<episode.json> ...]
    python -m guidie_collect.report <plan.json> <dir-with-*.episode.json>
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .episode import Episode
from .guidance import GuidancePlan
from .validate import validate_episode

_OUTCOMES = ("success", "fail", "corrected")


@dataclass
class EpisodeStat:
    episode_id: str
    path: str
    valid: bool
    n_warnings: int
    n_steps: int
    has_force: bool
    force_steps: int      # steps whose plan criterion is force_threshold
    force_covered: int    # ...of those, how many carry a peak_force_n


@dataclass
class DatasetReport:
    plan_id: str
    total_episodes: int = 0
    valid_episodes: int = 0
    episodes_with_warnings: int = 0
    total_steps: int = 0
    outcomes: dict[str, int] = field(default_factory=lambda: {k: 0 for k in _OUTCOMES})
    force_threshold_steps: int = 0
    force_covered_steps: int = 0
    distinct_tasks: int = 0
    episodes: list[EpisodeStat] = field(default_factory=list)

    @property
    def force_coverage(self) -> float | None:
        if self.force_threshold_steps == 0:
            return None
        return round(self.force_covered_steps / self.force_threshold_steps, 4)

    @property
    def validity_rate(self) -> float | None:
        if self.total_episodes == 0:
            return None
        return round(self.valid_episodes / self.total_episodes, 4)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["force_coverage"] = self.force_coverage
        d["validity_rate"] = self.validity_rate
        return d

    def render(self) -> str:
        fc = "n/a" if self.force_coverage is None else f"{self.force_coverage:.0%}"
        vr = "n/a" if self.validity_rate is None else f"{self.validity_rate:.0%}"
        lines = [
            f"Dataset QA — plan '{self.plan_id}'",
            f"  episodes        : {self.total_episodes} ({self.valid_episodes} valid, {vr})",
            f"  with warnings   : {self.episodes_with_warnings}",
            f"  steps           : {self.total_steps}  "
            f"(success {self.outcomes['success']}, fail {self.outcomes['fail']}, "
            f"corrected {self.outcomes['corrected']})",
            f"  force coverage  : {fc}  "
            f"({self.force_covered_steps}/{self.force_threshold_steps} force-threshold steps)",
            f"  distinct tasks  : {self.distinct_tasks}",
        ]
        return "\n".join(lines)


def _resolve_episode_paths(paths: list[str]) -> list[Path]:
    resolved: list[Path] = []
    for p in paths:
        path = Path(p)
        if path.is_dir():
            resolved.extend(sorted(path.glob("*.episode.json")))
        else:
            resolved.append(path)
    return resolved


def scan(plan_path: str | Path, episode_paths: list[str]) -> DatasetReport:
    plan = GuidancePlan.from_file(plan_path)
    report = DatasetReport(plan_id=plan.plan_id)
    tasks: set[str] = set()

    for ep_path in _resolve_episode_paths(episode_paths):
        episode = Episode.from_file(ep_path)
        vres = validate_episode(ep_path, plan_path)

        force_steps = 0
        force_covered = 0
        for st in episode.steps:
            report.total_steps += 1
            if st.outcome in report.outcomes:
                report.outcomes[st.outcome] += 1
            tasks.add(st.instruction)
            pstep = plan.step(st.step_id)
            if pstep and pstep.success_criterion.get("type") == "force_threshold":
                force_steps += 1
                if st.peak_force_n is not None:
                    force_covered += 1

        report.total_episodes += 1
        if vres.ok:
            report.valid_episodes += 1
        if vres.warnings:
            report.episodes_with_warnings += 1
        report.force_threshold_steps += force_steps
        report.force_covered_steps += force_covered
        report.episodes.append(
            EpisodeStat(
                episode_id=episode.episode_id,
                path=str(ep_path),
                valid=vres.ok,
                n_warnings=len(vres.warnings),
                n_steps=len(episode.steps),
                has_force=episode.has_force_stream,
                force_steps=force_steps,
                force_covered=force_covered,
            )
        )

    report.distinct_tasks = len(tasks)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Dataset QA / stats report.")
    parser.add_argument("plan", help="guidance plan JSON")
    parser.add_argument("episodes", nargs="+", help="episode JSON files or a directory")
    parser.add_argument("--json", action="store_true", help="emit JSON instead of text")
    args = parser.parse_args(argv)

    report = scan(args.plan, args.episodes)
    if args.json:
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(report.render())
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())

"""JSON schema loading and validation helpers.

Schemas live in the repo-level ``schema/`` directory. We resolve them relative to
this file so the package works whether installed or run from a checkout.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# src/guidie_collect/schema.py -> repo root is three parents up.
_REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = _REPO_ROOT / "schema"

GUIDANCE_PLAN_SCHEMA = SCHEMA_DIR / "guidance_plan.schema.json"
EPISODE_SCHEMA = SCHEMA_DIR / "episode.schema.json"


def load_json(path: str | Path) -> dict[str, Any]:
    """Load a JSON file into a dict."""
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def validate_against_schema(instance: dict[str, Any], schema_path: str | Path) -> list[str]:
    """Validate ``instance`` against the JSON schema at ``schema_path``.

    Returns a list of human-readable error strings (empty if valid). Uses
    ``jsonschema`` if available; otherwise returns a single soft-warning string
    so the rest of the pipeline (cross-contract invariants) can still run.
    """
    schema = load_json(schema_path)
    try:
        import jsonschema  # type: ignore
    except ImportError:  # pragma: no cover - exercised only without the dep
        return ["[warn] jsonschema not installed; skipped JSON-schema validation"]

    validator = jsonschema.Draft202012Validator(schema)
    errors = []
    for err in sorted(validator.iter_errors(instance), key=lambda e: list(e.path)):
        loc = "/".join(str(p) for p in err.path) or "<root>"
        errors.append(f"schema: {loc}: {err.message}")
    return errors

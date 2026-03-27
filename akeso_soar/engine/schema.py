"""Playbook JSON Schema loading and validation."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema

_SCHEMA_PATH = Path(__file__).resolve().parent.parent.parent / "schemas" / "playbook.schema.json"
_schema: dict | None = None


def _get_schema() -> dict:
    global _schema
    if _schema is None:
        _schema = json.loads(_SCHEMA_PATH.read_text())
    return _schema


class PlaybookValidationError:
    def __init__(self, message: str, path: str = "", step_id: str = ""):
        self.message = message
        self.path = path
        self.step_id = step_id

    def to_dict(self) -> dict:
        d: dict = {"message": self.message}
        if self.path:
            d["path"] = self.path
        if self.step_id:
            d["step_id"] = self.step_id
        return d


def validate_playbook_dict(data: dict) -> list[PlaybookValidationError]:
    """Validate a parsed playbook dict against the JSON Schema.

    Returns a list of errors (empty if valid).
    """
    errors: list[PlaybookValidationError] = []
    schema = _get_schema()

    validator = jsonschema.Draft202012Validator(schema)
    for err in validator.iter_errors(data):
        path = ".".join(str(p) for p in err.absolute_path)

        # Try to extract step_id for step-level errors
        step_id = ""
        path_list = list(err.absolute_path)
        if len(path_list) >= 2 and path_list[0] == "steps":
            idx = path_list[1]
            steps = data.get("steps", [])
            if isinstance(idx, int) and idx < len(steps):
                step_id = steps[idx].get("id", f"step[{idx}]")

        errors.append(PlaybookValidationError(
            message=err.message,
            path=path,
            step_id=step_id,
        ))

    # Additional semantic checks beyond JSON Schema
    if not errors:
        errors.extend(_check_step_references(data))

    return errors


def _check_step_references(data: dict) -> list[PlaybookValidationError]:
    """Check that on_success/on_failure/condition branches reference valid step IDs."""
    errors: list[PlaybookValidationError] = []
    steps = data.get("steps", [])
    step_ids = {s["id"] for s in steps}

    for step in steps:
        sid = step.get("id", "?")

        for field in ("on_success", "on_failure"):
            ref = step.get(field)
            if ref and ref != "abort" and ref not in step_ids:
                errors.append(PlaybookValidationError(
                    message=f"Step '{sid}' references unknown step '{ref}' in {field}",
                    path=f"steps.{sid}.{field}",
                    step_id=sid,
                ))

        if step.get("type") == "condition":
            branches = step.get("condition", {}).get("branches", {})
            for branch_key, target in branches.items():
                if target not in step_ids:
                    errors.append(PlaybookValidationError(
                        message=f"Condition '{sid}' branch '{branch_key}' references unknown step '{target}'",
                        path=f"steps.{sid}.condition.branches.{branch_key}",
                        step_id=sid,
                    ))

        if step.get("type") == "human_task":
            on_timeout = step.get("human_task", {}).get("on_timeout")
            if on_timeout and on_timeout not in step_ids:
                errors.append(PlaybookValidationError(
                    message=f"Human task '{sid}' on_timeout references unknown step '{on_timeout}'",
                    path=f"steps.{sid}.human_task.on_timeout",
                    step_id=sid,
                ))

    # Check for duplicate step IDs
    seen: set[str] = set()
    for step in steps:
        sid = step.get("id", "")
        if sid in seen:
            errors.append(PlaybookValidationError(
                message=f"Duplicate step ID '{sid}'",
                path=f"steps.{sid}",
                step_id=sid,
            ))
        seen.add(sid)

    return errors

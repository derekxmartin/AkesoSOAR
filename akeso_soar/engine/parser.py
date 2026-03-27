"""YAML playbook parser — loads YAML and validates against schema."""

from __future__ import annotations

import yaml

from akeso_soar.engine.schema import PlaybookValidationError, validate_playbook_dict


class ParseResult:
    def __init__(self, data: dict | None, errors: list[PlaybookValidationError]):
        self.data = data
        self.errors = errors

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

    def error_dicts(self) -> list[dict]:
        return [e.to_dict() for e in self.errors]


def parse_playbook_yaml(yaml_str: str) -> ParseResult:
    """Parse a YAML string into a playbook dict and validate it.

    Returns a ParseResult with the parsed data and any validation errors.
    """
    try:
        data = yaml.safe_load(yaml_str)
    except yaml.YAMLError as e:
        return ParseResult(None, [PlaybookValidationError(
            message=f"YAML parse error: {e}",
        )])

    if not isinstance(data, dict):
        return ParseResult(None, [PlaybookValidationError(
            message="Playbook must be a YAML mapping (object), got " + type(data).__name__,
        )])

    errors = validate_playbook_dict(data)
    return ParseResult(data if not errors else None, errors)

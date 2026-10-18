"""Offline regression checks for the playbook input boundary."""
import copy

import pytest
import yaml

from akeso_soar.engine.parser import parse_playbook_yaml
from akeso_soar.engine.condition_evaluator import resolve_branch
from akeso_soar.engine.variable_resolver import resolve_params


@pytest.fixture
def playbook():
    return {
        "name": "Synthetic alert triage",
        "trigger": {"type": "manual"},
        "steps": [
            {"id": "enrich", "name": "Mock enrichment", "type": "action",
             "action": {"connector": "demo", "operation": "lookup"},
             "on_success": "review"},
            {"id": "review", "name": "Review context", "type": "transform",
             "transform": {"expression": "{{ alert.severity }}", "output_var": "severity"}},
        ],
    }


def test_valid_synthetic_playbook_round_trip(playbook):
    result = parse_playbook_yaml(yaml.safe_dump(playbook))
    assert result.is_valid
    assert result.data == playbook


@pytest.mark.parametrize("payload", ["", "[]", "42", "steps: [", "!!python/object/apply:os.system ['echo unsafe']"])
def test_rejects_non_mapping_malformed_and_unsafe_yaml(payload):
    result = parse_playbook_yaml(payload)
    assert not result.is_valid
    assert result.data is None
    assert result.error_dicts()


def test_rejects_missing_target_with_step_context(playbook):
    playbook["steps"][0]["on_success"] = "missing"
    result = parse_playbook_yaml(yaml.safe_dump(playbook))
    assert not result.is_valid
    assert any(e.step_id == "enrich" and "missing" in e.message for e in result.errors)


def test_rejects_duplicate_step_ids(playbook):
    playbook["steps"].append(copy.deepcopy(playbook["steps"][0]))
    result = parse_playbook_yaml(yaml.safe_dump(playbook))
    assert not result.is_valid
    assert any("Duplicate step ID" in e.message for e in result.errors)


def test_rejects_action_without_connector_configuration(playbook):
    del playbook["steps"][0]["action"]
    assert not parse_playbook_yaml(yaml.safe_dump(playbook)).is_valid


def test_synthetic_triage_branches_and_parameter_resolution():
    context = {"alert": {"severity": "high", "host": "demo-host"}}
    branches = {"true": "review", "false": "close"}
    assert resolve_branch("alert.severity == 'high'", branches, context) == "review"
    assert resolve_branch("alert.severity == 'low'", branches, context) == "close"
    assert resolve_params({"host": "{{ alert.host }}", "attempts": 1}, context) == {
        "host": "demo-host", "attempts": 1,
    }

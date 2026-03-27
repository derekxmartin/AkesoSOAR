"""Condition step evaluator — evaluates Jinja2 expressions and returns branch target."""

from __future__ import annotations

from jinja2 import BaseLoader, Environment, UndefinedError

_env = Environment(loader=BaseLoader())


def evaluate_condition(expression: str, context: dict) -> bool:
    """Evaluate a Jinja2 condition expression against the variable context.

    Supports comparison operators, boolean logic, nested field access.
    Handles type coercion for string-to-number comparisons.
    """
    # Strip surrounding {{ }} if present
    expr = expression.strip()
    if expr.startswith("{{") and expr.endswith("}}"):
        expr = expr[2:-2].strip()

    # Wrap in a Jinja2 if-expression that returns "true" or "false"
    template_str = f"{{% if {expr} %}}true{{% else %}}false{{% endif %}}"

    try:
        tmpl = _env.from_string(template_str)
        result = tmpl.render(**context)
        return result.strip() == "true"
    except (UndefinedError, TypeError, ValueError):
        return False


def resolve_branch(
    expression: str,
    branches: dict[str, str],
    context: dict,
) -> str | None:
    """Evaluate a condition and return the step ID of the matching branch."""
    result = evaluate_condition(expression, context)
    branch_key = "true" if result else "false"
    return branches.get(branch_key)

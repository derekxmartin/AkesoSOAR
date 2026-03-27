"""Jinja2 variable resolution for playbook step parameters."""

from __future__ import annotations

from jinja2 import BaseLoader, Environment, UndefinedError

_env = Environment(loader=BaseLoader())


def resolve_string(template_str: str, context: dict) -> str:
    """Resolve Jinja2 template tags in a string against the variable context."""
    if "{{" not in template_str and "{%" not in template_str:
        return template_str
    try:
        tmpl = _env.from_string(template_str)
        return tmpl.render(**context)
    except UndefinedError:
        return template_str


def resolve_params(params: dict, context: dict) -> dict:
    """Recursively resolve Jinja2 templates in a params dict."""
    resolved = {}
    for key, value in params.items():
        if isinstance(value, str):
            resolved[key] = resolve_string(value, context)
        elif isinstance(value, dict):
            resolved[key] = resolve_params(value, context)
        elif isinstance(value, list):
            resolved[key] = [
                resolve_string(v, context) if isinstance(v, str) else v
                for v in value
            ]
        else:
            resolved[key] = value
    return resolved

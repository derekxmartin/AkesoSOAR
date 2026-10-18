# AkesoSOAR

A security orchestration, automation, and response proof of concept. It explores alert intake, YAML playbooks, analyst review tasks, role-based access, and a React operations dashboard.

**Current boundary:** the playbook executor's action adapter in `akeso_soar/engine/executor.py` returns registered test results or a response marked `mock: true`. A successful playbook action is not evidence that an endpoint was isolated, a real ticket was created, or another security product was changed. The project is for development and controlled demonstrations.

## Architecture

| Area | Source | Responsibility |
|---|---|---|
| API and services | `akeso_soar/api/`, `akeso_soar/services/` | Alerts, users, playbooks, review tasks, and audit records |
| Playbook engine | `akeso_soar/engine/` | YAML validation, branching, variables, retries, and execution |
| Persistence | `akeso_soar/models/`, `alembic/` | SQLAlchemy models and PostgreSQL migrations |
| Dashboard | `dashboard/` | React, TypeScript, and Vite frontend |

## Start with the offline checks

Use Python 3.12 and Node 24. From the repository root:

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
python -m pytest -q
cd dashboard
npm ci
npm run build
```

On Windows, activate the environment with `.venv\Scripts\Activate.ps1`. The Python tests exercise synthetic playbook parsing, invalid input, step references, branching, and parameter substitution. They do not require credentials or live connectors.

## Small walkthrough

Run `python -m pytest tests/test_playbook_validation.py -v` from the root. The synthetic triage playbook moves from mock enrichment to review; a high-severity alert selects the review branch. The same suite verifies that malformed YAML, unsafe YAML object tags, duplicate steps, and missing step targets are rejected. Passing these checks demonstrates the parser and routing boundary, not execution against an external system.

The full service additionally needs PostgreSQL, an application configuration derived from `.env.example`, and migrations via `alembic upgrade head`. Review configuration and seed data before starting a local instance with `uvicorn akeso_soar.app:app --host 127.0.0.1 --port 8000`. The example database password and signing/encryption values are placeholders: replace them locally and never commit a populated environment file. Do not expose a default development instance to the internet.

## Status and limits

The CI workflow runs the offline Python checks and dashboard production build. Database migrations, authentication flows, persisted execution, human-task scheduling, and connector integration need separate end-to-end validation. The existing `REQUIREMENTS.md` is a design roadmap, not a list of independently verified capabilities. There is no production support commitment or validated release artifact.

## Licensing and contributions

No project-wide license has been selected for the original code in this repository. Public visibility does not grant a general reuse or redistribution license. Ask the repository owner about intended use; dependencies keep their own terms. See [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md).

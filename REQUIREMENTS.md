# AkesoSOAR — Requirements Document v1.0

**A Proof-of-Concept Security Orchestration, Automation, and Response Platform**

Version 1.0 — Initial Requirements + Implementation Phases | March 2026

> Python 3.12 · FastAPI · PostgreSQL · React 18 · Playwright
> The orchestration brain that ties the Akeso portfolio together

---

# PART I: REQUIREMENTS & ARCHITECTURE

---

## 1. Executive Summary

AkesoSOAR is a proof-of-concept Security Orchestration, Automation, and Response platform that fills the final architectural gap in the Akeso security portfolio. Where AkesoSIEM detects threats, AkesoSOAR decides what to do about them and coordinates the response across every product in the portfolio.

The core problem AkesoSOAR addresses is the disconnect between detection and action. In real-world SOCs, detection rules fire alerts, but the response — triaging, enriching, deciding, and executing containment or remediation actions — is a manual, multi-tool, multi-tab process that depends on institutional knowledge locked inside senior analysts' heads. L3 analysts spend the majority of their time not writing detection rules, but building and maintaining *use cases*: formal, documented, lifecycle-managed response plans that define what data sources are required, what detection logic triggers them, what enrichment and investigation steps follow, and what response actions execute across which products. These use cases have owners, maturity states, review cadences, associated diagrams, and tuning parameters. They are the atomic unit of SOC operations, and no product in the current Akeso portfolio manages them.

AkesoSOAR introduces three capabilities that do not exist elsewhere in the portfolio:

1. **Use Case Lifecycle Management.** A use case is a first-class entity with a formal schema: name, description, MITRE ATT&CK mapping, required data sources, detection logic reference (pointer to a Sigma rule in AkesoSIEM), enrichment steps, response actions, owner, review cadence, maturity state (Draft → Testing → Production → Deprecated), and associated documentation including flow diagrams. AkesoSOAR provides CRUD operations, versioning, state machine transitions, and audit history for use cases.

2. **Playbook Engine.** Playbooks are directed acyclic graphs (DAGs) of executable steps that automate the enrichment-decision-response pipeline. Each step is either an *action* (call an external API — AkesoEDR isolate host, AkesoFW block IP, AkesoDLP quarantine file, AkesoSIEM create case), a *condition* (branch on a field value or threshold), a *human task* (pause and wait for analyst approval), or a *transform* (reshape data between steps). Playbooks are defined in YAML, validated against a schema, and executed by a DAG executor that handles parallelism, error handling, retries, timeouts, and rollback. A visual editor in the React dashboard provides drag-and-drop playbook authoring.

3. **Cross-Product Orchestration.** AkesoSOAR is the only component that holds API connectors to every other Akeso product. When a playbook step says "isolate endpoint X," AkesoSOAR calls AkesoEDR's gRPC API. When it says "block IP Y at the firewall," it calls AkesoFW's REST API. When it says "create a case in the SIEM," it calls AkesoSIEM's REST API. This hub-and-spoke integration model means response logic is defined once in a playbook and executed across the portfolio without any product needing to know about any other product directly.

The technology choice is Python + FastAPI for the server, PostgreSQL for persistent state (use cases, playbook definitions, execution history, audit logs), and React for the dashboard. Python is the natural fit because SOAR platforms live in the automation and integration layer — they call APIs, parse JSON, evaluate conditions, and orchestrate workflows. Performance-sensitive packet processing (NDR) and kernel-level hooking (EDR/DLP) justified C/C++ and Go elsewhere in the portfolio; orchestration does not. Python also aligns with the real-world SOAR ecosystem: Splunk SOAR playbooks are Python scripts, Cortex XSOAR uses Python for integrations, and most SOC automation tooling is Python-native.

This document follows the same two-part format as the rest of the Akeso portfolio. Part I captures requirements and architecture. Part II breaks implementation into phased tasks sized for Claude Code sessions.

---

## 2. Project Goals & Non-Goals

### 2.1 Goals

- Build a working SOAR platform that ingests alerts from AkesoSIEM, evaluates them against use case definitions, and executes playbooks that coordinate response actions across the Akeso portfolio.
- Implement a use case lifecycle management system where use cases are first-class entities with formal schemas, versioning, maturity state machines, owner assignment, review cadences, and audit trails.
- Provide a DAG-based playbook engine that executes YAML-defined playbooks with support for parallel branches, conditional logic, human approval gates, error handling, retries, timeouts, and rollback.
- Build API connectors (integrations) for every Akeso product: AkesoEDR (gRPC), AkesoAV (via EDR), AkesoDLP (gRPC), AkesoSIEM (REST), AkesoNDR (gRPC), AkesoFW (REST), AkesoC2 (REST — for red team simulation scenarios).
- Expose a React dashboard with: use case management views (CRUD, lifecycle visualization, dependency graphs), a visual playbook editor (drag-and-drop DAG builder), playbook execution monitoring (real-time step status, logs), and operational metrics (MTTR, playbook success rates, use case coverage).
- Implement role-based access control (RBAC) with JWT + TOTP MFA, consistent with AkesoSIEM's authentication model.
- Generate structured audit logs for every use case change, playbook execution, and response action for compliance and post-incident review.

### 2.2 Non-Goals

- AkesoSOAR is not a SIEM. It does not ingest raw logs, store events in Elasticsearch, or evaluate Sigma rules. Detection stays in AkesoSIEM. AkesoSOAR consumes *alerts* that AkesoSIEM has already produced.
- AkesoSOAR is not a case management system. AkesoSIEM already has built-in case management. AkesoSOAR may create or update cases in AkesoSIEM via API, but it does not duplicate that functionality.
- AkesoSOAR does not implement threat intelligence platform (TIP) functionality. It may consume enrichment from external TIP APIs as playbook steps, but it does not manage indicator feeds, scoring, or lifecycle.
- Production-grade high availability, horizontal scaling, multi-tenancy, and enterprise SSO (SAML/OIDC) are out of scope for this PoC.
- AI/ML-driven autonomous triage or dynamic playbook generation are out of scope. Playbooks are manually authored (with the visual editor) and deterministic. This is a deliberate design choice: the PoC demonstrates the orchestration model, not the AI augmentation layer.

---

## 3. System Architecture

### 3.1 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        AkesoSOAR Platform                          │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │  Alert       │  │  Use Case    │  │  Playbook Engine         │  │
│  │  Ingestion   │──│  Manager     │──│  ┌────────────────────┐  │  │
│  │  (webhook +  │  │  (lifecycle, │  │  │  DAG Executor      │  │  │
│  │   polling)   │  │   versioning,│  │  │  (parallel, retry, │  │  │
│  │              │  │   matching)  │  │  │   rollback, gates) │  │  │
│  └──────────────┘  └──────────────┘  │  └────────────────────┘  │  │
│                                       │  ┌────────────────────┐  │  │
│  ┌──────────────┐  ┌──────────────┐  │  │  Action Registry   │  │  │
│  │  React       │  │  REST API    │  │  │  (connectors to    │  │  │
│  │  Dashboard   │──│  (FastAPI)   │──│  │   all Akeso        │  │  │
│  │              │  │              │  │  │   products)         │  │  │
│  └──────────────┘  └──────────────┘  │  └────────────────────┘  │  │
│                                       └──────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  PostgreSQL (use cases, playbooks, executions, audit logs)   │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
        │              │              │              │
        ▼              ▼              ▼              ▼
   AkesoSIEM      AkesoEDR       AkesoFW       AkesoNDR
   (alerts,       (isolate,      (block IP,    (pcap,
    cases)         collect)       allow)        query)
                      │                            │
                      ▼                            │
                   AkesoAV                         │
                   (scan,                          │
                    quarantine)                    │
                      │                            │
                      ▼                            ▼
                   AkesoDLP                    AkesoC2
                   (quarantine,                (red team
                    policy update)              simulation)
```

### 3.2 Component Table

| Component | Language | Role | Key Dependencies |
|-----------|----------|------|------------------|
| API Server | Python 3.12 | REST API, authentication, RBAC, WebSocket for real-time updates | FastAPI, Uvicorn, Pydantic v2, python-jose (JWT), pyotp (TOTP) |
| Use Case Manager | Python 3.12 | Use case CRUD, versioning, state machine, matching engine | SQLAlchemy 2.0 (async), Alembic |
| Playbook Engine | Python 3.12 | YAML parsing, DAG validation, step execution, parallel orchestration | PyYAML, jsonschema, asyncio, graphlib (stdlib topological sort) |
| Action Registry | Python 3.12 | Connector framework, action definitions, credential management | httpx (async HTTP), grpcio (gRPC clients), cryptography (Fernet for secrets) |
| PostgreSQL | — | Persistent storage for all state | PostgreSQL 16, asyncpg |
| React Dashboard | TypeScript/React 18 | Use case management, visual playbook editor, execution monitoring | Vite, TanStack Query, ReactFlow (DAG editor), Tailwind CSS, shadcn/ui |
| E2E Tests | TypeScript | Full workflow testing | Playwright |

### 3.3 Data Flow

1. **Alert Ingestion.** AkesoSIEM fires alerts via webhook (HTTP POST to `/api/v1/alerts/ingest`) or AkesoSOAR polls AkesoSIEM's alert API on a configurable interval. Each alert is a JSON payload conforming to AkesoSIEM's alert schema (ECS-normalized fields plus Sigma rule metadata).

2. **Use Case Matching.** The Use Case Manager evaluates incoming alerts against active use cases. Matching is based on configurable criteria: Sigma rule ID, MITRE technique ID, severity threshold, data source type, or custom field conditions. A single alert can match multiple use cases (e.g., a brute-force alert matches both the "AD Brute Force Response" use case and the "Compromised Account Containment" use case).

3. **Playbook Triggering.** Each use case references one or more playbooks. When a use case matches, its associated playbooks are queued for execution. The playbook engine creates an *execution instance* — a record of this specific run with its own state, logs, and timeline.

4. **DAG Execution.** The playbook engine resolves the DAG, identifies root nodes (steps with no dependencies), and begins parallel execution. Each step invokes an action from the Action Registry. The executor handles: step success → advance to dependent steps; step failure → retry (if configured) or branch to error handler; human gate → pause execution, notify analyst, wait for approval; condition → evaluate expression, follow matching branch.

5. **Response Actions.** Action steps call Akeso product APIs via the connector framework. Each connector is a Python class that implements a standard interface (`execute(params) -> ActionResult`). Connectors handle authentication, request formation, response parsing, and error mapping.

6. **Completion.** When all branches of the DAG complete (or fail), the execution instance is finalized with a terminal state (Completed, Failed, Partially Failed, Cancelled). Metrics are recorded. If the playbook is associated with an AkesoSIEM case, the case is updated with the response summary.

---

## 4. Data Models

### 4.1 Use Case Schema

```yaml
use_case:
  id: uuid
  name: string                          # "AD Brute Force Detection & Response"
  description: text                     # Detailed narrative description
  version: integer                      # Auto-incremented on each edit
  status: enum                          # Draft | Testing | Production | Deprecated
  severity: enum                        # Critical | High | Medium | Low | Informational
  owner: uuid                           # Reference to user
  created_at: timestamp
  updated_at: timestamp
  review_cadence_days: integer          # e.g., 90 (quarterly review)
  last_reviewed_at: timestamp
  next_review_at: timestamp             # Computed: last_reviewed_at + review_cadence_days

  # MITRE ATT&CK Mapping
  mitre:
    tactics: [string]                   # ["TA0006"]  (Credential Access)
    techniques: [string]                # ["T1110", "T1110.001", "T1110.003"]
    data_sources: [string]              # ["DS0002"]  (User Account)

  # Detection Binding
  detection:
    sigma_rule_ids: [string]            # References to Sigma rules in AkesoSIEM
    siem_alert_query: string            # Optional: custom AkesoSIEM query filter
    severity_threshold: enum            # Minimum alert severity to trigger
    data_sources_required:              # What telemetry must be flowing for this use case to work
      - source: string                  # "windows_security"
        event_ids: [integer]            # [4625, 4624, 4768, 4771]
        description: string             # "Windows Security Event Log — logon events"
      - source: string                  # "akeso_edr"
        event_types: [string]           # ["process_create", "network_connect"]

  # Response Binding
  response:
    playbook_ids: [uuid]                # Playbooks to execute when this use case triggers
    escalation_policy: string           # "auto" | "manual" | "conditional"
    notification_channels: [string]     # ["slack:#soc-alerts", "email:oncall@corp.com"]

  # Documentation
  documentation:
    summary: text                       # One-paragraph executive summary
    investigation_guide: text           # Markdown: step-by-step for analysts
    false_positive_guidance: text       # Known FP scenarios and tuning advice
    references: [string]                # URLs to external references
    diagrams: [uuid]                    # References to uploaded diagram files
    change_log: [object]                # Array of {version, timestamp, author, description}
```

### 4.2 Playbook Schema (YAML)

```yaml
playbook:
  id: uuid
  name: string                          # "Brute Force — Enrichment & Containment"
  description: text
  version: integer
  enabled: boolean
  trigger:
    type: enum                          # "alert" | "manual" | "scheduled"
    conditions:                         # For alert-triggered playbooks
      sigma_rule_id: string
      severity_gte: string
      custom_filter: string             # JSONPath expression on alert payload

  # Variables available to all steps
  variables:
    alert: object                       # Injected at runtime from the triggering alert
    config: object                      # Injected from playbook configuration

  steps:
    - id: string                        # "enrich_ip"
      name: string                      # "Enrich Source IP"
      type: enum                        # "action" | "condition" | "human_task" | "transform" | "parallel"
      action:                           # Only for type=action
        connector: string               # "akeso_siem" | "akeso_edr" | "akeso_fw" | "virustotal"
        operation: string               # "lookup_ip" | "isolate_host" | "block_ip"
        params:                         # Key-value pairs, supports Jinja2 templating
          ip: "{{ alert.source.ip }}"
      on_success: string                # Next step ID
      on_failure: string                # Error handler step ID or "abort"
      timeout_seconds: integer          # Max execution time for this step
      retry:
        max_attempts: integer
        backoff_seconds: integer

    - id: string                        # "check_threshold"
      name: string                      # "Check Failed Login Count"
      type: "condition"
      condition:
        expression: "{{ steps.enrich_ip.result.failed_count > 10 }}"
        branches:
          "true": "isolate_host"        # Step ID if condition is true
          "false": "log_and_close"      # Step ID if condition is false

    - id: string                        # "approve_isolation"
      name: string                      # "Analyst Approval for Isolation"
      type: "human_task"
      human_task:
        prompt: "Approve isolating {{ alert.host.name }}?"
        assignee_role: "soc_l2"         # RBAC role that can approve
        timeout_hours: 4                # Auto-escalate if no response
        on_timeout: "escalate_to_l3"    # Step ID on timeout
      on_success: "isolate_host"

    - id: string                        # "parallel_enrich"
      name: string                      # "Parallel Enrichment"
      type: "parallel"
      parallel:
        branches:
          - steps: ["enrich_ip", "enrich_user"]
          - steps: ["check_asset_criticality"]
        join: "all"                     # "all" (wait for all) or "any" (first to complete)
      on_success: "evaluate_risk"
```

### 4.3 Execution Instance Schema

```yaml
execution:
  id: uuid
  playbook_id: uuid
  playbook_version: integer             # Snapshot of which version ran
  trigger_alert_id: string              # The alert that triggered this execution
  use_case_id: uuid                     # Which use case matched
  status: enum                          # Queued | Running | Paused | Completed | Failed | Cancelled
  started_at: timestamp
  completed_at: timestamp
  duration_ms: integer

  step_results:                         # One entry per step executed
    - step_id: string
      status: enum                      # Pending | Running | Success | Failed | Skipped | Waiting
      started_at: timestamp
      completed_at: timestamp
      duration_ms: integer
      input: object                     # Resolved params sent to the action
      output: object                    # Result returned by the action
      error: string                     # Error message if failed
      retry_count: integer

  audit_trail:                          # Immutable log of every state change
    - timestamp: timestamp
      event_type: string                # "step_started" | "step_completed" | "human_approved" | ...
      step_id: string
      actor: string                     # "system" or user ID
      details: object
```

### 4.4 Connector Interface

Every Akeso product connector implements a standard Python interface:

```python
class AkesoConnector(ABC):
    """Base class for all Akeso product connectors."""

    @abstractmethod
    async def connect(self, config: ConnectorConfig) -> None:
        """Establish connection and authenticate."""

    @abstractmethod
    async def execute(self, operation: str, params: dict) -> ActionResult:
        """Execute a named operation with given parameters."""

    @abstractmethod
    async def health_check(self) -> HealthStatus:
        """Verify connectivity and authentication."""

    @abstractmethod
    def list_operations(self) -> list[OperationSpec]:
        """Return available operations with their parameter schemas."""
```

Each connector supports the following operations:

| Connector | Transport | Operations |
|-----------|-----------|------------|
| `akeso_siem` | REST (httpx) | `create_case`, `update_case`, `add_case_note`, `search_alerts`, `get_alert`, `create_alert_tag` |
| `akeso_edr` | gRPC (grpcio) | `isolate_host`, `unisolate_host`, `collect_artifacts`, `kill_process`, `get_host_info`, `list_alerts` |
| `akeso_av` | gRPC (via EDR) | `scan_file`, `scan_host`, `quarantine_file`, `get_scan_result` |
| `akeso_dlp` | gRPC (grpcio) | `quarantine_file`, `update_policy`, `get_incidents`, `release_file` |
| `akeso_ndr` | gRPC (grpcio) | `query_flows`, `get_connection_info`, `export_pcap`, `get_anomalies` |
| `akeso_fw` | REST (httpx) | `block_ip`, `unblock_ip`, `block_port`, `add_rule`, `remove_rule`, `get_rules` |
| `akeso_c2` | REST (httpx) | `list_implants`, `task_implant`, `get_task_result` (for red team simulation) |
| `generic_http` | REST (httpx) | `get`, `post`, `put`, `delete` (for external APIs like VirusTotal, AbuseIPDB) |

---

## 5. Use Case Lifecycle Management

### 5.1 State Machine

```
                ┌──────────────────────────────────────────┐
                │                                          │
                ▼                                          │
┌─────────┐  create  ┌─────────┐  promote  ┌──────────┐  │
│  (new)   │────────▶│  Draft  │─────────▶│ Testing  │   │
└─────────┘          └─────────┘          └──────────┘   │
                          │                    │          │
                          │ archive            │ promote  │ demote
                          │                    ▼          │
                          │              ┌────────────┐   │
                          │              │ Production │───┘
                          │              └────────────┘
                          │                    │
                          ▼                    │ deprecate
                    ┌────────────┐             │
                    │ Deprecated │◀────────────┘
                    └────────────┘
```

**State Transitions:**

| From | To | Transition | Requirements |
|------|----|-----------|--------------|
| (new) | Draft | `create` | Name, description, owner, at least one detection binding |
| Draft | Testing | `promote` | All required data sources documented, at least one playbook linked, investigation guide written |
| Testing | Production | `promote` | Playbook tested successfully (≥1 execution with Completed status), false positive guidance documented, review cadence set |
| Production | Testing | `demote` | Reason required (audit logged) |
| Production | Deprecated | `deprecate` | Reason required, linked playbooks disabled |
| Draft | Deprecated | `archive` | No active playbook executions |

Every transition is audit-logged with timestamp, actor, reason, and before/after state.

### 5.2 Versioning

Every edit to a use case creates a new version. The version history is immutable — you can view any prior version and diff between versions. The current production version is always the latest version in Production state. When a use case is demoted from Production to Testing, the previous production version remains accessible for rollback.

### 5.3 Review Cadence

Use cases in Production state have a mandatory review cadence (default: 90 days). The system tracks `last_reviewed_at` and computes `next_review_at`. When a review is overdue, the dashboard highlights it and optionally sends a notification to the owner. A review is recorded by an authorized user confirming the use case is still valid, optionally updating thresholds or documentation.

### 5.4 Data Source Dependency Tracking

Each use case declares the data sources it requires. The system can cross-reference these against AkesoSIEM's active ingestion sources to determine whether a use case is *fully operational* (all data sources flowing), *partially operational* (some missing), or *non-operational* (critical sources missing). This is surfaced on the dashboard as a health indicator per use case.

---

## 6. Playbook Engine Architecture

### 6.1 DAG Execution Model

Playbooks are YAML files that define a directed acyclic graph of steps. The engine uses Python's `graphlib.TopologicalSorter` (stdlib, Python 3.9+) to resolve execution order and identify parallelizable branches.

**Execution lifecycle:**

1. **Parse.** YAML is loaded and validated against the playbook JSON schema.
2. **Resolve.** Variables are initialized from the triggering alert payload and playbook config. Jinja2 templates in step parameters are resolved against the variable context.
3. **Plan.** The DAG is topologically sorted. Steps with no dependencies are identified as root nodes.
4. **Execute.** Root nodes execute concurrently via `asyncio.gather()`. As each step completes, its dependents become eligible. The executor maintains a `step_results` dict that grows as steps complete, making their outputs available to downstream steps via Jinja2 references like `{{ steps.enrich_ip.result.reputation }}`.
5. **Gate.** Human task steps pause execution and create a pending approval record. The WebSocket layer pushes a notification to connected dashboard clients. When an authorized user approves or rejects, execution resumes.
6. **Finalize.** When all steps are terminal (success, failed, or skipped), the execution instance is marked complete and metrics are recorded.

### 6.2 Error Handling

Each step can define:

- **Retry policy.** `max_attempts` and `backoff_seconds` (exponential backoff). Failed steps are retried up to the limit before being marked as permanently failed.
- **On-failure branch.** A step ID to jump to on failure (e.g., a notification step that alerts the team).
- **Timeout.** If a step exceeds `timeout_seconds`, it is cancelled and treated as a failure.
- **Rollback.** Steps can optionally define a `rollback_action` — an action to execute if a downstream step fails. For example, if "isolate host" succeeds but "update SIEM case" fails, the rollback might "unisolate host." Rollback is best-effort, not transactional.

### 6.3 Playbook Validation

Before a playbook can be activated, the engine validates:

- YAML conforms to the playbook JSON schema.
- The step graph is acyclic (no cycles detected by topological sort).
- All referenced connectors exist in the Action Registry.
- All referenced operations exist on their respective connectors.
- Jinja2 template expressions parse without errors.
- Human task steps have valid assignee roles that exist in RBAC.
- No orphan steps (steps not reachable from any root).

Validation errors are returned as structured diagnostics with line numbers and suggestions.

---

## 7. Dashboard Requirements

### 7.1 Authentication

Consistent with AkesoSIEM: JWT access tokens (15-minute expiry) + refresh tokens (7-day expiry) + TOTP MFA. Shared RBAC model with roles: Admin, SOC Manager, SOC Analyst (L1/L2/L3), Read Only.

### 7.2 Use Case Management Views

| View | Description |
|------|-------------|
| **Use Case List** | Table with columns: name, status (color-coded badge), severity, owner, MITRE technique, data source health, review status, last triggered. Filterable by status, severity, owner, MITRE tactic. Sortable by any column. |
| **Use Case Detail** | Full use case schema rendered as a structured form. Tabs: Overview, Detection Binding, Response Binding, Documentation, Version History, Audit Log, Execution History. |
| **Use Case Editor** | Form-based editor for creating/editing use cases. MITRE ATT&CK technique picker (searchable dropdown with tactic grouping). Data source selector (populated from AkesoSIEM's configured sources). Playbook linker (searchable dropdown of available playbooks). |
| **Use Case Board** | Kanban-style board with columns for each status (Draft, Testing, Production, Deprecated). Drag-and-drop to transition with confirmation dialog and required reason field. |
| **Use Case Coverage Matrix** | Heatmap grid: MITRE ATT&CK tactics (columns) × techniques (rows). Cells colored by coverage: green (Production use case exists), yellow (Testing/Draft), red (no coverage). Click a cell to see linked use cases. |

### 7.3 Playbook Views

| View | Description |
|------|-------------|
| **Playbook List** | Table with: name, version, enabled/disabled toggle, trigger type, last executed, success rate (last 30 days), linked use cases. |
| **Visual Playbook Editor** | ReactFlow-based DAG canvas. Node types: Action (blue), Condition (yellow diamond), Human Task (orange), Transform (gray), Parallel (purple). Drag nodes from a palette, connect with edges, configure each node via a side panel. Real-time validation: invalid edges (cycles) shown in red, missing parameters highlighted. Export to YAML, import from YAML. |
| **Playbook Execution View** | Real-time execution visualization on the DAG canvas. Nodes light up as they execute: gray (pending), blue (running), green (success), red (failed), orange (waiting for human). Step detail panel shows input, output, duration, errors. WebSocket-driven — no polling. |
| **Execution History** | Table of all past executions with: playbook name, trigger alert, use case, status, duration, started_at. Click to open the execution view with the final DAG state. |

### 7.4 Operational Dashboards

| Dashboard | Metrics |
|-----------|---------|
| **SOC Overview** | Open alerts (by severity), active playbook executions, pending human tasks, MTTR (mean time to respond), MTTD (mean time to detect — pulled from SIEM), use case coverage percentage. |
| **Playbook Performance** | Execution count (daily/weekly), success/failure rate, average duration, most-triggered playbooks, slowest steps, most-failed steps. |
| **Use Case Health** | Use cases by status (pie chart), overdue reviews, data source health (operational/partial/non-operational), recently triggered, coverage gaps (MITRE heatmap summary). |

### 7.5 Global Search & Command Palette

Cmd+K command palette (consistent with AkesoSIEM). Search across use cases, playbooks, executions, and alerts. Actions: navigate to entity, trigger manual playbook run, create new use case.

---

## 8. Integration Test Scenarios

These scenarios validate end-to-end functionality across AkesoSOAR and the Akeso portfolio:

| # | Scenario | Products Involved | Expected Outcome |
|---|----------|-------------------|------------------|
| 1 | AkesoSIEM fires brute-force alert → AkesoSOAR matches "AD Brute Force Response" use case → playbook enriches source IP, checks threshold, isolates host via AkesoEDR, blocks IP via AkesoFW, creates SIEM case | SIEM, SOAR, EDR, FW | Host isolated, IP blocked, case created with full timeline |
| 2 | AkesoDLP detects sensitive file exfiltration → SIEM alert → SOAR matches "Data Exfiltration Response" use case → playbook quarantines file via DLP, isolates host via EDR, exports network flows via NDR | SIEM, SOAR, DLP, EDR, NDR | File quarantined, host isolated, PCAP exported, case enriched |
| 3 | Playbook hits human approval gate → analyst approves via dashboard → execution resumes | SOAR | Execution pauses, notification sent, approval recorded, execution completes |
| 4 | Playbook step fails (connector timeout) → retry policy activates → retries exhaust → error handler notifies team | SOAR | Retry logged, error handler executed, execution marked Partially Failed |
| 5 | Use case promoted from Draft → Testing → Production with all validation gates | SOAR | State transitions logged, validation enforced at each gate |
| 6 | Use case coverage matrix shows gap for T1059 (Command and Scripting Interpreter) → analyst creates new use case and playbook to fill gap | SOAR, SIEM | New use case in Draft, linked playbook created, coverage matrix updated |
| 7 | Scheduled playbook runs nightly vulnerability scan summary → enriches with AkesoEDR host inventory → generates report | SOAR, EDR | Execution completes on schedule, report generated |
| 8 | Rollback scenario: isolate host succeeds, but subsequent SIEM case creation fails → rollback unisolates host | SOAR, EDR, SIEM | Host unisolated, execution marked Failed with rollback record |
| 9 | Parallel enrichment: IP reputation, user account lookup, and asset criticality check run concurrently → all complete → risk score computed | SOAR | All three branches complete, risk score reflects all inputs |
| 10 | Manual playbook triggered by analyst from dashboard for ad-hoc investigation | SOAR | Playbook executes without alert trigger, results visible in execution history |
| 11 | Red team simulation: AkesoC2 implant detected by EDR → SIEM alert → SOAR playbook queries C2 server for implant details → coordinates response | SIEM, SOAR, EDR, C2 | Full kill chain response executed, C2 context enriches the case |

---

## 9. Feature Priority Matrix

| Priority | Feature | Rationale |
|----------|---------|-----------|
| P0 (Must) | Use case CRUD with status lifecycle | Core value proposition — this is the gap we're filling |
| P0 (Must) | Playbook YAML schema + DAG executor | Without execution, use cases are just documentation |
| P0 (Must) | AkesoSIEM connector (alert ingestion + case creation) | Primary integration — SIEM is the alert source |
| P0 (Must) | AkesoEDR connector (isolate/unisolate host) | Most common response action |
| P0 (Must) | AkesoFW connector (block/unblock IP) | Second most common response action |
| P0 (Must) | REST API with JWT + TOTP MFA auth | Security baseline consistent with portfolio |
| P0 (Must) | React dashboard: use case list, detail, editor | Primary analyst interface |
| P1 (Should) | Visual playbook editor (ReactFlow) | Major portfolio differentiator but complex |
| P1 (Should) | Real-time execution visualization (WebSocket) | Makes the PoC dramatically more impressive |
| P1 (Should) | Human approval gates in playbooks | Differentiates from pure automation |
| P1 (Should) | Use case coverage matrix (MITRE heatmap) | High-impact dashboard widget |
| P1 (Should) | AkesoDLP connector | Completes the endpoint response trio |
| P1 (Should) | AkesoNDR connector | Network context enrichment |
| P2 (Nice) | AkesoC2 connector (red team simulation) | Novel but niche |
| P2 (Nice) | Playbook rollback actions | Complex error handling — impressive but rare |
| P2 (Nice) | Scheduled playbook triggers | Useful but less visually impactful |
| P2 (Nice) | Use case Kanban board view | Nice UX but list view is sufficient |
| P2 (Nice) | Global search / command palette | Consistent with SIEM but additive |

---

## 10. Development Environment

| Aspect | Specification |
|--------|--------------|
| Python | 3.12+ |
| Package Manager | pip + requirements.txt (dev and prod separated) |
| Framework | FastAPI 0.110+ with Pydantic v2 |
| Database | PostgreSQL 16 with asyncpg driver, SQLAlchemy 2.0 async |
| Migrations | Alembic |
| Frontend | React 18, TypeScript 5, Vite, TanStack Query, ReactFlow, Tailwind CSS, shadcn/ui |
| Testing | pytest + pytest-asyncio (backend), Playwright (E2E), Vitest (frontend unit) |
| Linting | ruff (Python), ESLint + Prettier (TypeScript) |
| WebSocket | FastAPI WebSocket endpoints, frontend via native WebSocket API |
| Templating | Jinja2 (for playbook variable resolution) |
| Container | Docker Compose for local dev (PostgreSQL, API server, frontend dev server) |

---

## 11. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| DAG executor complexity (parallel branches, retries, rollback) | Core engine becomes fragile | Build incrementally: linear first, then branching, then parallel, then rollback. Extensive unit tests at each stage. |
| ReactFlow learning curve for visual editor | Playbook editor becomes the bottleneck | Start with read-only DAG visualization (Phase 8), add editing in Phase 9. ReactFlow has good docs and examples. |
| Connector proliferation (7 products × multiple operations) | Large surface area for bugs | Standard connector interface + shared test harness. Mock connectors for unit testing, real connectors for integration tests. |
| Playbook YAML schema complexity | Authoring errors frustrate users | Rich validation with line-number diagnostics. Visual editor reduces manual YAML editing. Ship example playbooks as templates. |
| Human approval gates require real-time notification | WebSocket reliability, UX for pending tasks | Fallback to polling if WebSocket disconnects. Timeout-based escalation ensures tasks don't hang indefinitely. |
| Scope creep toward TIP/case management features | Duplicates SIEM functionality | Strict non-goals. Use case manager links to SIEM cases but doesn't replicate them. |

---

# PART II: PHASED IMPLEMENTATION TASKS

All tasks are designed for sequential Claude Code sessions, fed phase-by-phase. Task IDs follow the SOAR- prefix. Complexity ratings: S (< 2hrs), M (2–4hrs), L (4–8hrs), XL (8+ hrs).

---

## Phase 1: Project Scaffolding & Database

**Goal:** Repository structure, Docker Compose for PostgreSQL, SQLAlchemy models, Alembic migrations, and the FastAPI application shell.

| ID | Task | Files | Acceptance Criteria | Est. |
|----|------|-------|---------------------|------|
| SOAR-P1-T1 | Initialize Python project: `pyproject.toml` or `requirements.txt`, directory structure (`akeso_soar/api/`, `akeso_soar/engine/`, `akeso_soar/connectors/`, `akeso_soar/models/`), `.env.example`, `docker-compose.yml` with PostgreSQL 16, ruff config. | `pyproject.toml`, `docker-compose.yml`, `.env.example`, `ruff.toml`, directory tree | `docker compose up -d` starts PostgreSQL. `ruff check .` passes. Python imports resolve. | S |
| SOAR-P1-T2 | SQLAlchemy 2.0 async models for: `User`, `UseCase`, `UseCaseVersion`, `Playbook`, `PlaybookVersion`, `Execution`, `StepResult`, `AuditLog`, `Connector`, `HumanTask`. All with UUID primary keys, timestamps, proper foreign keys and indexes. | `akeso_soar/models/*.py` | Models import without error. Relationships defined (UseCase → PlaybookVersion, Execution → StepResult). Enum types for status fields. | M |
| SOAR-P1-T3 | Alembic setup with async support. Initial migration creates all tables. Seed migration inserts default admin user and default connector entries for all Akeso products. | `alembic/`, `alembic.ini`, `akeso_soar/db.py` | `alembic upgrade head` creates all tables in PostgreSQL. `alembic downgrade base` cleanly drops them. Seed data present after upgrade. | M |
| SOAR-P1-T4 | FastAPI application shell: app factory pattern, CORS middleware, health check endpoint (`GET /api/v1/health`), database session dependency injection, structured logging with `structlog`. | `akeso_soar/app.py`, `akeso_soar/dependencies.py`, `akeso_soar/logging.py` | `uvicorn akeso_soar.app:create_app --factory` starts cleanly. Health endpoint returns `{"status": "ok", "database": "connected"}`. Structured JSON logs on stdout. | M |

---

## Phase 2: Authentication & RBAC

**Goal:** JWT + TOTP MFA authentication system and role-based access control, consistent with AkesoSIEM's auth model.

| ID | Task | Files | Acceptance Criteria | Est. |
|----|------|-------|---------------------|------|
| SOAR-P2-T1 | Auth endpoints: `POST /api/v1/auth/login` (username + password → JWT pair), `POST /api/v1/auth/refresh` (refresh token → new access token), `POST /api/v1/auth/mfa/setup` (generate TOTP secret + QR URI), `POST /api/v1/auth/mfa/verify` (validate TOTP code). Password hashing with bcrypt. | `akeso_soar/api/auth.py`, `akeso_soar/services/auth.py` | Login returns access + refresh tokens. Refresh rotates tokens. MFA setup returns valid TOTP URI. MFA verify accepts correct code, rejects wrong code. Passwords bcrypt-hashed in DB. | L |
| SOAR-P2-T2 | RBAC middleware: role-based route guards via FastAPI dependencies. Roles: `admin`, `soc_manager`, `soc_l3`, `soc_l2`, `soc_l1`, `read_only`. Permission matrix: admin (all), soc_manager (manage use cases + playbooks), soc_l3 (edit use cases + playbooks + approve human tasks), soc_l2 (edit playbooks + approve human tasks), soc_l1 (view + trigger manual playbooks), read_only (view only). | `akeso_soar/api/rbac.py`, `akeso_soar/models/permissions.py` | Protected endpoints reject unauthenticated requests (401). Unauthorized role gets 403. Admin can access everything. L1 cannot edit use cases. | M |
| SOAR-P2-T3 | User management endpoints: `GET /api/v1/users`, `POST /api/v1/users`, `PATCH /api/v1/users/{id}`, `DELETE /api/v1/users/{id}`. Admin-only for create/delete, self-edit for profile. | `akeso_soar/api/users.py` | CRUD works. Non-admin cannot create users. Users can update own password. Deleted user's tokens are invalidated. | M |

---

## Phase 3: Use Case Manager — Core CRUD

**Goal:** Full CRUD for use cases with versioning, state machine transitions, and audit logging.

| ID | Task | Files | Acceptance Criteria | Est. |
|----|------|-------|---------------------|------|
| SOAR-P3-T1 | Use case CRUD endpoints: `POST /api/v1/use-cases`, `GET /api/v1/use-cases` (paginated, filterable by status/severity/owner/mitre_tactic), `GET /api/v1/use-cases/{id}`, `PATCH /api/v1/use-cases/{id}`, `DELETE /api/v1/use-cases/{id}` (soft delete). Every edit creates a new `UseCaseVersion` row. | `akeso_soar/api/use_cases.py`, `akeso_soar/services/use_case_service.py` | Create returns 201 with version 1. Edit returns updated use case with incremented version. List supports `?status=Production&severity=High&page=1&limit=20`. Version history accessible via `GET /api/v1/use-cases/{id}/versions`. Soft delete sets `deleted_at`. | L |
| SOAR-P3-T2 | State machine transitions: `POST /api/v1/use-cases/{id}/transition` with body `{"to_status": "Testing", "reason": "Ready for playbook testing"}`. Validates transition is legal per state machine (Section 5.1). Validates promotion gates (e.g., Draft → Testing requires playbook linked). Records transition in audit log. | `akeso_soar/services/use_case_lifecycle.py` | Legal transitions succeed. Illegal transitions return 400 with explanation. Promotion gates enforced (Draft → Testing fails if no playbook linked). Audit log entry created for every transition. | M |
| SOAR-P3-T3 | Use case version diffing: `GET /api/v1/use-cases/{id}/diff?v1=3&v2=5` returns a structured diff showing which fields changed between versions. | `akeso_soar/services/use_case_diff.py` | Diff correctly identifies changed fields. Nested object diffs (e.g., MITRE mapping changes) are granular. Returns empty diff for identical versions. | M |
| SOAR-P3-T4 | Audit log service: generic audit logger that records all entity changes (use cases, playbooks, executions) with timestamp, actor, entity type, entity ID, action, before/after state. `GET /api/v1/audit-log` with filters by entity type, entity ID, actor, date range. | `akeso_soar/services/audit_service.py`, `akeso_soar/api/audit.py` | Audit entries created automatically on use case CRUD and transitions. Query endpoint returns paginated, filtered results. Before/after states are JSON snapshots. | M |

---

## Phase 4: Use Case Manager — Advanced Features

**Goal:** Review cadence tracking, data source dependency checking, MITRE coverage matrix, and use case–playbook linking.

| ID | Task | Files | Acceptance Criteria | Est. |
|----|------|-------|---------------------|------|
| SOAR-P4-T1 | Review cadence system: scheduled check (configurable interval, default hourly) identifies use cases where `next_review_at < now()`. Marks them as overdue. `POST /api/v1/use-cases/{id}/review` records a review with optional notes. Resets `next_review_at`. | `akeso_soar/services/review_scheduler.py` | Overdue use cases flagged. Review endpoint records review in audit log. `next_review_at` correctly computed. `GET /api/v1/use-cases?overdue=true` returns only overdue use cases. | M |
| SOAR-P4-T2 | Data source health tracking: `GET /api/v1/use-cases/{id}/health` cross-references the use case's `data_sources_required` against AkesoSIEM's active ingestion sources (via SIEM connector). Returns `operational` / `partial` / `non-operational` with details on which sources are missing. | `akeso_soar/services/data_source_health.py` | Health endpoint returns correct status. Mock SIEM connector returns configurable source list. Missing sources listed in response. | M |
| SOAR-P4-T3 | MITRE ATT&CK coverage API: `GET /api/v1/coverage/mitre` returns a matrix of tactic × technique with coverage status derived from all use cases. Each cell includes: technique ID, name, coverage status (covered/partial/gap), linked use case IDs. | `akeso_soar/api/coverage.py`, `akeso_soar/services/mitre_coverage.py` | Matrix correctly reflects use case MITRE mappings. Adding a use case for T1110 turns that cell from gap to covered. Endpoint returns full matrix in a format suitable for heatmap rendering. | L |
| SOAR-P4-T4 | Use case ↔ playbook linking: `POST /api/v1/use-cases/{id}/playbooks` (link), `DELETE /api/v1/use-cases/{id}/playbooks/{playbook_id}` (unlink). When a use case is deprecated, its linked playbooks are automatically disabled. | `akeso_soar/services/use_case_playbook_link.py` | Link and unlink work. Deprecating a use case disables linked playbooks. Use case detail includes linked playbook summaries. Playbook detail includes linked use case summaries. | S |

---

## Phase 5: Playbook Engine — YAML Schema & Linear Execution

**Goal:** Playbook YAML parsing, validation, and linear (non-branching) execution with the DAG executor.

| ID | Task | Files | Acceptance Criteria | Est. |
|----|------|-------|---------------------|------|
| SOAR-P5-T1 | Playbook YAML schema definition (JSON Schema) and parser. Validates structure, step types, required fields. Returns structured errors with step IDs and field paths on validation failure. | `akeso_soar/engine/schema.py`, `akeso_soar/engine/parser.py`, `schemas/playbook.schema.json` | Valid YAML passes validation. Invalid YAML returns errors with step ID and field path. Schema covers all step types from Section 4.2. | M |
| SOAR-P5-T2 | Playbook CRUD endpoints: `POST /api/v1/playbooks` (upload YAML + metadata), `GET /api/v1/playbooks`, `GET /api/v1/playbooks/{id}`, `PATCH /api/v1/playbooks/{id}`, `DELETE /api/v1/playbooks/{id}`. Versioning on edit. Enable/disable toggle. | `akeso_soar/api/playbooks.py`, `akeso_soar/services/playbook_service.py` | CRUD works. YAML validated on create/update. Version incremented on edit. Disabled playbooks not triggered by alerts. | M |
| SOAR-P5-T3 | DAG executor — linear execution path. Takes a parsed playbook and an alert payload, resolves Jinja2 variables, executes steps sequentially. Each step calls a mock action and records the result. Execution instance created in DB with step-by-step results. | `akeso_soar/engine/executor.py`, `akeso_soar/engine/variable_resolver.py` | Linear playbook (A → B → C) executes all steps. Jinja2 templates resolve correctly (e.g., `{{ alert.source.ip }}`). Step results recorded with status, duration, input/output. Execution instance has correct terminal status. | L |
| SOAR-P5-T4 | Execution API: `POST /api/v1/playbooks/{id}/execute` (manual trigger with alert payload), `GET /api/v1/executions` (list), `GET /api/v1/executions/{id}` (detail with step results), `POST /api/v1/executions/{id}/cancel` (abort running execution). | `akeso_soar/api/executions.py` | Manual trigger starts execution. List/detail return execution state and step results. Cancel aborts running execution gracefully. | M |

---

## Phase 6: Playbook Engine — Branching, Parallelism & Error Handling

**Goal:** Conditional branches, parallel step execution, retry policies, timeouts, and rollback.

| ID | Task | Files | Acceptance Criteria | Est. |
|----|------|-------|---------------------|------|
| SOAR-P6-T1 | Condition step execution: evaluate Jinja2 expression against variable context, follow matching branch. Supports comparison operators, boolean logic, and nested field access. | `akeso_soar/engine/condition_evaluator.py` | Condition `{{ steps.enrich.result.score > 7 }}` correctly branches. Both true and false paths tested. Complex expressions with `and`/`or` work. Type coercion handles string-to-int comparisons. | M |
| SOAR-P6-T2 | Parallel step execution: `type: parallel` steps fork into concurrent branches via `asyncio.gather()`. Supports `join: "all"` (wait for all branches) and `join: "any"` (proceed when first branch completes, cancel others). Branch results merged into variable context. | `akeso_soar/engine/parallel_executor.py` | Parallel branches execute concurrently (verified by timing — parallel is faster than sequential). `join: "all"` waits for all. `join: "any"` proceeds on first completion. Branch results available downstream. | L |
| SOAR-P6-T3 | Retry policies: exponential backoff retry for failed steps. Configurable `max_attempts` and `backoff_seconds`. Retry count recorded in step result. After exhausting retries, step is permanently failed and triggers `on_failure` branch. | `akeso_soar/engine/retry_handler.py` | Step retried correct number of times. Backoff timing approximately correct (within 10% tolerance). After max retries, on_failure branch executes. Retry count in step result. | M |
| SOAR-P6-T4 | Step timeouts: if a step exceeds `timeout_seconds`, it is cancelled via `asyncio.wait_for()` and treated as a failure. Timeout recorded as the failure reason. | Update `akeso_soar/engine/executor.py` | Slow mock action (sleep 10s) with 2s timeout is cancelled after ~2s. Failure reason is "timeout". On_failure branch executes. | S |
| SOAR-P6-T5 | Rollback actions: steps can define `rollback_action` (connector + operation + params). If a downstream step fails and the playbook's `rollback_on_failure` flag is true, the executor walks back the completed steps in reverse order and executes their rollback actions. Best-effort — rollback failures are logged but do not halt the rollback chain. | `akeso_soar/engine/rollback_handler.py` | Rollback executes in reverse order. Rollback action results logged. Rollback failure doesn't prevent other rollbacks. Execution status reflects rollback outcome. | L |

---

## Phase 7: Connector Framework & Akeso Product Integrations

**Goal:** Connector base class, credential management, and connectors for all Akeso products.

| ID | Task | Files | Acceptance Criteria | Est. |
|----|------|-------|---------------------|------|
| SOAR-P7-T1 | Connector framework: base class (`AkesoConnector`), connector registry (discover and load connectors by name), credential storage (Fernet-encrypted secrets in PostgreSQL), health check infrastructure. `GET /api/v1/connectors` lists all registered connectors with health status. | `akeso_soar/connectors/base.py`, `akeso_soar/connectors/registry.py`, `akeso_soar/connectors/credentials.py`, `akeso_soar/api/connectors.py` | Registry discovers all connector classes. Health check endpoint returns status per connector. Credentials stored encrypted, decrypted only at execution time. | L |
| SOAR-P7-T2 | AkesoSIEM connector: REST client using httpx. Operations: `create_case`, `update_case`, `add_case_note`, `search_alerts`, `get_alert`, `create_alert_tag`. Mock mode for testing (returns realistic fake data). | `akeso_soar/connectors/akeso_siem.py` | All 6 operations work in mock mode. Real mode sends correct HTTP requests (verified by httpx mock). Error mapping: SIEM 404 → ActionResult(success=False, error="case_not_found"). | M |
| SOAR-P7-T3 | AkesoEDR connector: gRPC client using grpcio. Operations: `isolate_host`, `unisolate_host`, `collect_artifacts`, `kill_process`, `get_host_info`, `list_alerts`. Protobuf message definitions. Mock mode. | `akeso_soar/connectors/akeso_edr.py`, `protos/edr.proto` | All 6 operations work in mock mode. Protobuf messages compile. gRPC channel configuration correct. Connection timeout handled gracefully. | M |
| SOAR-P7-T4 | AkesoFW connector: REST client. Operations: `block_ip`, `unblock_ip`, `block_port`, `add_rule`, `remove_rule`, `get_rules`. Mock mode. | `akeso_soar/connectors/akeso_fw.py` | All 6 operations work in mock mode. IP validation on block/unblock. Rule format matches AkesoFW's YAML rule schema. | M |
| SOAR-P7-T5 | AkesoDLP connector: gRPC client. Operations: `quarantine_file`, `update_policy`, `get_incidents`, `release_file`. AkesoNDR connector: gRPC client. Operations: `query_flows`, `get_connection_info`, `export_pcap`, `get_anomalies`. Both with mock mode. | `akeso_soar/connectors/akeso_dlp.py`, `akeso_soar/connectors/akeso_ndr.py`, `protos/dlp.proto`, `protos/ndr.proto` | All operations work in mock mode for both connectors. Protobuf messages compile. | M |
| SOAR-P7-T6 | AkesoC2 connector: REST client. Operations: `list_implants`, `task_implant`, `get_task_result`. Generic HTTP connector: configurable REST client for external APIs (VirusTotal, AbuseIPDB). Both with mock mode. | `akeso_soar/connectors/akeso_c2.py`, `akeso_soar/connectors/generic_http.py` | C2 operations work in mock mode. Generic HTTP connector supports configurable base URL, auth header, and custom request templates. | M |

---

## Phase 8: Alert Ingestion & Use Case Matching

**Goal:** Webhook and polling-based alert ingestion from AkesoSIEM, use case matching engine, and automatic playbook triggering.

| ID | Task | Files | Acceptance Criteria | Est. |
|----|------|-------|---------------------|------|
| SOAR-P8-T1 | Alert ingestion webhook: `POST /api/v1/alerts/ingest` accepts AkesoSIEM alert payloads. Validates payload against expected schema. Stores alert in PostgreSQL. Returns 202 Accepted. Rate limiting (configurable, default 100/min). | `akeso_soar/api/alerts.py`, `akeso_soar/services/alert_ingestion.py` | Valid alert payload returns 202. Invalid payload returns 400 with details. Alert stored in DB. Rate limit enforced (429 on exceed). | M |
| SOAR-P8-T2 | Alert polling service: background task (asyncio) polls AkesoSIEM's alert API at configurable interval (default 30s). Deduplicates alerts by SIEM alert ID. Uses SIEM connector from Phase 7. | `akeso_soar/services/alert_poller.py` | Poller fetches new alerts at configured interval. Duplicate alerts not re-ingested. Poller handles SIEM connectivity failure gracefully (logs error, retries on next interval). | M |
| SOAR-P8-T3 | Use case matching engine: evaluates each incoming alert against all active (Production) use cases. Matching criteria: Sigma rule ID match, MITRE technique overlap, severity ≥ threshold, custom field conditions (JSONPath expressions). Returns list of matched use cases. | `akeso_soar/engine/use_case_matcher.py` | Alert with Sigma rule ID matching a use case triggers a match. Alert with severity below threshold does not match. MITRE technique overlap correctly evaluated. Custom JSONPath conditions work. | L |
| SOAR-P8-T4 | Automatic playbook triggering: when a use case matches, queue its linked playbooks for execution. Deduplication: don't re-trigger the same playbook for the same alert within a configurable cooldown window (default 5 minutes). Wire together: alert ingestion → use case matching → playbook triggering → DAG execution. | `akeso_soar/services/playbook_trigger.py` | End-to-end: POST alert → use case matches → playbook executes → execution instance created. Cooldown prevents duplicate triggers. Multiple use cases can match same alert. | L |

---

## Phase 9: React Dashboard — Foundation & Use Case Views

**Goal:** React app scaffolding, authentication UI, and use case management views.

| ID | Task | Files | Acceptance Criteria | Est. |
|----|------|-------|---------------------|------|
| SOAR-P9-T1 | React app scaffolding: Vite + React 18 + TypeScript. Tailwind CSS + shadcn/ui. TanStack Query for API data fetching. React Router for navigation. Auth context with JWT token management. Login page with username/password + TOTP input. | `dashboard/` directory scaffold | `npm run dev` starts dev server. Login page renders. Login flow: credentials → MFA → token stored → redirect to dashboard. Logout clears tokens. | M |
| SOAR-P9-T2 | App shell: sidebar navigation (Use Cases, Playbooks, Executions, Connectors, Dashboard, Settings), top bar with user info and logout, main content area. Responsive: sidebar collapses on mobile. | `dashboard/src/components/AppShell.tsx`, `dashboard/src/components/Sidebar.tsx` | All nav items render and route correctly. Sidebar collapse works. Active nav item highlighted. | M |
| SOAR-P9-T3 | Use Case List view: paginated table with columns (name, status badge, severity badge, owner, MITRE techniques, data source health indicator, review status, last triggered). Filter bar: status, severity, owner, MITRE tactic dropdowns. Sort by any column. Click row to navigate to detail. | `dashboard/src/pages/UseCases.tsx`, `dashboard/src/components/UseCaseTable.tsx` | Table renders with real data from API. Filters update query params and refetch. Pagination works. Sort indicators visible. Status badges color-coded (Draft=gray, Testing=yellow, Production=green, Deprecated=red). | L |
| SOAR-P9-T4 | Use Case Detail view: tabbed layout — Overview (rendered schema), Detection Binding (Sigma rule refs, data sources), Response Binding (linked playbooks), Documentation (markdown rendered), Version History (timeline), Audit Log (table), Execution History (table of playbook runs triggered by this use case). Edit button opens Use Case Editor. | `dashboard/src/pages/UseCaseDetail.tsx` | All tabs render correct data. Markdown rendered safely (DOMPurify). Version history shows diffs on click. Audit log paginated. Edit button navigates to editor with pre-filled form. | L |
| SOAR-P9-T5 | Use Case Editor: form with sections matching schema. MITRE ATT&CK technique picker (searchable, grouped by tactic). Data source selector. Playbook linker. Markdown editor for documentation fields. Save validates and creates new version. State transition buttons with confirmation dialog and reason field. | `dashboard/src/pages/UseCaseEditor.tsx`, `dashboard/src/components/MitrePicker.tsx` | Create new use case works end-to-end. Edit existing use case creates new version. MITRE picker searchable and shows technique descriptions. State transition enforces gates (shows error if requirements not met). | XL |

---

## Phase 10: React Dashboard — Playbook Views & Visual Editor

**Goal:** Playbook list, visual DAG editor using ReactFlow, and read-only execution visualization.

| ID | Task | Files | Acceptance Criteria | Est. |
|----|------|-------|---------------------|------|
| SOAR-P10-T1 | Playbook List view: table with name, version, enabled toggle, trigger type, last executed, success rate (sparkline or percentage), linked use cases. Enable/disable toggle calls API. Click row to navigate to detail. | `dashboard/src/pages/Playbooks.tsx` | Table renders. Enable/disable toggle works (optimistic update + API call). Success rate calculated from execution history. | M |
| SOAR-P10-T2 | Visual Playbook Editor — read-only DAG rendering: take a playbook's step definitions, render as a ReactFlow DAG. Node types: Action (blue rounded rect), Condition (yellow diamond), Human Task (orange rounded rect), Transform (gray rounded rect), Parallel (purple container). Edges show flow direction. Node click opens detail panel. | `dashboard/src/components/PlaybookGraph.tsx`, `dashboard/src/components/nodes/*.tsx` | Playbook YAML correctly rendered as visual DAG. All 5 node types have distinct visual styles. Edges render correctly including conditional branches (labeled true/false). Detail panel shows step configuration. | L |
| SOAR-P10-T3 | Visual Playbook Editor — interactive editing: drag nodes from a palette onto the canvas, connect with edges, configure via side panel. Add/remove steps. Edit step parameters. Validate DAG in real-time (cycle detection → red edges, missing params → yellow warning). Export to YAML. Import from YAML. | `dashboard/src/components/PlaybookEditor.tsx`, `dashboard/src/components/StepConfigPanel.tsx` | Drag-and-drop node creation works. Edge connection works. Side panel shows correct config fields per step type. Cycle detection highlights invalid edges. Export produces valid YAML. Import renders correctly. | XL |
| SOAR-P10-T4 | Execution Visualization: real-time execution view on the DAG canvas. WebSocket connection receives step state updates. Nodes animate: gray (pending), pulsing blue (running), green (success), red (failed), orange (waiting for human). Step detail panel shows live input/output/logs. Human task nodes show approve/reject buttons for authorized users. | `dashboard/src/pages/ExecutionView.tsx`, `dashboard/src/hooks/useExecutionWebSocket.ts` | WebSocket receives updates. Nodes change color in real-time. Step detail updates live. Human task approval via dashboard triggers execution resumption. Execution timeline shows duration per step. | XL |

---

## Phase 11: Human Approval Gates & WebSocket Infrastructure

**Goal:** Human task workflow (pause → notify → approve/reject → resume) and WebSocket real-time updates.

| ID | Task | Files | Acceptance Criteria | Est. |
|----|------|-------|---------------------|------|
| SOAR-P11-T1 | WebSocket infrastructure: FastAPI WebSocket endpoint at `/ws`. Authentication via token query param. Rooms: per-execution (receive step updates), global (receive new alerts, new human tasks). Connection management (track active connections, clean up on disconnect). | `akeso_soar/api/websocket.py`, `akeso_soar/services/ws_manager.py` | WebSocket connects with valid token. Invalid token rejected. Messages broadcast to correct room. Disconnect handled cleanly. Multiple concurrent connections work. | L |
| SOAR-P11-T2 | Human task service: when executor hits a `human_task` step, create a `HumanTask` record (pending), pause execution, broadcast notification via WebSocket. Endpoints: `GET /api/v1/human-tasks` (list pending, filtered by assignee role), `POST /api/v1/human-tasks/{id}/approve`, `POST /api/v1/human-tasks/{id}/reject` (with reason). On approve → resume execution. On reject → follow on_failure branch. On timeout → follow on_timeout branch. | `akeso_soar/services/human_task_service.py`, `akeso_soar/api/human_tasks.py` | Task created when executor hits human_task step. WebSocket notification sent. Approve resumes execution on success path. Reject follows failure path. Timeout (simulated with short duration) follows timeout path. Only authorized roles can approve. | L |
| SOAR-P11-T3 | Dashboard notification center: bell icon in top bar with unread count badge. Dropdown shows recent notifications (new human tasks, execution failures, overdue reviews). Click notification navigates to relevant entity. Notifications received via WebSocket. | `dashboard/src/components/NotificationCenter.tsx` | Unread count updates in real-time. Notification list shows correct items. Click navigates correctly. Mark-as-read works. | M |

---

## Phase 12: Operational Dashboards & Metrics

**Goal:** SOC overview dashboard, playbook performance metrics, and use case health dashboard.

| ID | Task | Files | Acceptance Criteria | Est. |
|----|------|-------|---------------------|------|
| SOAR-P12-T1 | Metrics aggregation service: compute and cache (PostgreSQL materialized view or in-memory with periodic refresh) key metrics: MTTR (from execution start to completion), playbook success rate (last 7/30 days), execution count by day, use case coverage percentage, pending human tasks count, overdue reviews count. API: `GET /api/v1/metrics/overview`, `GET /api/v1/metrics/playbooks`, `GET /api/v1/metrics/use-cases`. | `akeso_soar/services/metrics_service.py`, `akeso_soar/api/metrics.py` | Metrics endpoints return correct computed values. MTTR calculated correctly. Success rate handles zero-execution case. Metrics refresh on configurable interval. | L |
| SOAR-P12-T2 | SOC Overview dashboard page: card grid at top (open alerts, active executions, pending human tasks, MTTR, coverage %). Alerts by severity bar chart. Execution trend line chart (daily, last 30 days). Recent executions table. Recent human tasks requiring attention. | `dashboard/src/pages/Dashboard.tsx` | Dashboard renders with real data. Charts render correctly (Recharts). Cards show correct numbers. Auto-refreshes via TanStack Query refetch interval. | L |
| SOAR-P12-T3 | MITRE ATT&CK Coverage heatmap: interactive grid. Tactics as columns, techniques as rows. Cell color: green (Production use case), yellow (Testing/Draft), red (gap). Click cell to see linked use cases. Tooltip shows technique name and description. | `dashboard/src/components/MitreCoverageMap.tsx` | Heatmap renders with correct colors based on use case data. Click opens detail popover. Tooltip shows technique info. Responsive (horizontal scroll on mobile). | L |
| SOAR-P12-T4 | Use Case Kanban board: columns for Draft, Testing, Production, Deprecated. Cards show use case name, severity badge, owner avatar. Drag-and-drop between columns triggers state transition (with confirmation dialog and reason field). | `dashboard/src/pages/UseCaseBoard.tsx` | Kanban renders with correct column grouping. Drag-and-drop works. Transition validation enforced (invalid drops rejected with toast message). Confirmation dialog captures reason. | M |

---

## Phase 13: Global Search, Command Palette & Polish

**Goal:** Cross-entity search, keyboard-driven command palette, and UX polish across the dashboard.

| ID | Task | Files | Acceptance Criteria | Est. |
|----|------|-------|---------------------|------|
| SOAR-P13-T1 | Global search API: `GET /api/v1/search?q=brute+force` searches across use cases (name, description), playbooks (name), executions (alert ID), and connectors (name). Returns unified result list with entity type, name, ID, and relevance snippet. PostgreSQL full-text search (`tsvector/tsquery`). | `akeso_soar/api/search.py`, `akeso_soar/services/search_service.py` | Search returns results across all entity types. Relevance ranking reasonable. Partial match works (e.g., "brute" matches "Brute Force"). Results include entity type for routing. | M |
| SOAR-P13-T2 | Command palette (Cmd+K): overlay modal with search input. Results grouped by entity type. Keyboard navigation (arrow keys + Enter). Actions: navigate to entity, trigger manual playbook, create new use case, quick-toggle playbook enable/disable. | `dashboard/src/components/CommandPalette.tsx` | Cmd+K opens palette. Typing filters results in real-time. Arrow keys navigate, Enter selects. Esc closes. Actions execute correctly. Debounced API calls (300ms). | M |
| SOAR-P13-T3 | Dashboard polish: loading skeletons on all data-fetching views, error boundaries with retry buttons, empty states with helpful messages (e.g., "No use cases yet — create your first one"), toast notifications for success/error on mutations, responsive breakpoints verified on all views. | Multiple dashboard files | No raw loading spinners — skeletons match layout. Error boundaries catch and display errors with retry. Empty states guide user. Toasts appear on create/edit/delete/transition. All views usable at 375px width. | M |

---

## Phase 14: Example Content & Seed Data

**Goal:** Ship the platform with example use cases, playbooks, and seed data that demonstrate the full feature set.

| ID | Task | Files | Acceptance Criteria | Est. |
|----|------|-------|---------------------|------|
| SOAR-P14-T1 | Example use cases (5): "AD Brute Force Detection & Response" (Production), "Sensitive Data Exfiltration" (Production), "Suspicious PowerShell Execution" (Testing), "Lateral Movement via PsExec" (Draft), "Compromised Account Containment" (Production). Each fully populated with MITRE mapping, data sources, documentation, and linked playbooks. | `seeds/use_cases/*.yaml` | All 5 use cases load via seed script. Different statuses represented. MITRE mappings correct. Documentation fields populated with realistic content. | M |
| SOAR-P14-T2 | Example playbooks (3): "Brute Force — Enrichment & Containment" (linear: enrich IP → check threshold → isolate host → block IP → create case), "Data Exfiltration — Parallel Investigation" (parallel enrichment branches + human approval gate), "Lateral Movement — Full Kill Chain" (condition branches + rollback). All valid YAML with realistic step configurations. | `seeds/playbooks/*.yaml` | All 3 playbooks pass schema validation. DAG renders correctly in visual editor. Cover all step types (action, condition, human_task, parallel, transform). Demonstrate retry, timeout, and rollback configurations. | L |
| SOAR-P14-T3 | Seed script: populates database with example use cases, playbooks, a set of mock alerts (10), connector configurations, and admin + analyst users. Runnable via `python -m akeso_soar.seeds.load`. Idempotent (safe to run multiple times). | `akeso_soar/seeds/load.py` | Seed script completes without error. All example data present in database. Re-running doesn't duplicate data. Dashboard shows populated views. | M |

---

## Phase 15: End-to-End Tests & Documentation

**Goal:** Playwright E2E tests covering critical workflows, API integration tests, and project documentation.

| ID | Task | Files | Acceptance Criteria | Est. |
|----|------|-------|---------------------|------|
| SOAR-P15-T1 | API integration tests: test the full alert → use case match → playbook trigger → execution lifecycle using pytest + httpx test client. Cover: alert ingestion, use case CRUD and transitions, playbook CRUD and execution, human task approve/reject, connector mock calls. | `tests/integration/test_*.py` | All integration tests pass. Coverage of core workflows: alert-to-execution pipeline, use case lifecycle, playbook execution with branches/parallel/retry. Tests use real PostgreSQL (Docker) not SQLite. | L |
| SOAR-P15-T2 | Playwright E2E tests (5 scenarios): (1) Login → navigate to use case list → create new use case → promote to Testing. (2) Open visual playbook editor → add nodes → connect → save → verify YAML. (3) Trigger manual playbook execution → watch real-time visualization → verify completion. (4) Dashboard loads with metrics → verify chart rendering. (5) Command palette → search → navigate to entity. | `tests/e2e/test_*.spec.ts` | All 5 E2E tests pass in headless Chromium. Tests run against seeded database. Screenshots captured on failure. CI-compatible (no GUI required). | L |
| SOAR-P15-T3 | Project documentation: `README.md` with architecture overview, quickstart (Docker Compose), development setup, API reference overview (link to auto-generated FastAPI docs at `/docs`), playbook authoring guide (YAML schema with examples), use case management guide, connector development guide. | `README.md`, `docs/playbook-authoring.md`, `docs/use-case-guide.md`, `docs/connector-dev.md` | README covers quickstart in under 5 minutes. Playbook authoring guide walks through creating a custom playbook. Connector dev guide shows how to add a new integration. All docs accurate and tested. | L |

---

## Phase Summary

| Phase | Description | Tasks | Depends On | Est. Sessions |
|-------|-------------|-------|------------|---------------|
| 1 | Project Scaffolding & Database | 4 | — | 1–2 |
| 2 | Authentication & RBAC | 3 | Phase 1 | 1–2 |
| 3 | Use Case Manager — Core CRUD | 4 | Phase 2 | 2–3 |
| 4 | Use Case Manager — Advanced | 4 | Phase 3 | 2 |
| 5 | Playbook Engine — YAML & Linear Execution | 4 | Phase 1 | 2–3 |
| 6 | Playbook Engine — Branching & Parallelism | 5 | Phase 5 | 3–4 |
| 7 | Connector Framework & Integrations | 6 | Phase 1 | 2–3 |
| 8 | Alert Ingestion & Use Case Matching | 4 | Phases 3, 5, 7 | 2–3 |
| 9 | React Dashboard — Foundation & Use Cases | 5 | Phases 2, 3, 4 | 3–4 |
| 10 | React Dashboard — Playbook & Visual Editor | 4 | Phases 5, 9 | 3–5 |
| 11 | Human Approval Gates & WebSocket | 3 | Phases 6, 10 | 2–3 |
| 12 | Operational Dashboards & Metrics | 4 | Phases 8, 9 | 2–3 |
| 13 | Global Search & Polish | 3 | Phase 9 | 1–2 |
| 14 | Example Content & Seed Data | 3 | Phases 3, 5, 7 | 1–2 |
| 15 | End-to-End Tests & Documentation | 3 | All phases | 2–3 |
| **Total** | | **59 tasks** | | **27–42 sessions** |

---

## Code Conventions

- **Python:** ruff for linting and formatting. Type hints on all function signatures. Pydantic v2 models for all API request/response schemas. Async throughout (async def, await, asyncpg). Docstrings on all public functions and classes.
- **TypeScript/React:** ESLint + Prettier. Strict TypeScript (`strict: true`). Functional components with hooks. TanStack Query for all API calls (no raw fetch). shadcn/ui components preferred over custom implementations.
- **Testing:** pytest + pytest-asyncio for backend. Vitest for frontend unit tests. Playwright for E2E. Test file naming: `test_<module>.py` (Python), `<Component>.test.tsx` (React), `<feature>.spec.ts` (Playwright).
- **API Design:** RESTful with consistent patterns. Paginated list endpoints use `?page=1&limit=20`. Filter params use `?status=Production&severity=High`. All endpoints return JSON. Errors return `{"detail": "message", "code": "ERROR_CODE"}`.
- **Git:** Conventional commits (`feat:`, `fix:`, `test:`, `docs:`). One commit per task minimum.
- **Secrets:** Never committed. `.env` for local dev. Fernet-encrypted connector credentials in PostgreSQL.

---

## v2 Roadmap (Post-Launch)

Features deferred from v1 that would enhance AkesoSOAR in future iterations:

- **Threat intelligence enrichment:** native TIP integration (MISP, OpenCTI) as first-class connectors with IOC matching and feed ingestion.
- **Playbook marketplace:** export/import playbooks as shareable packages with versioned dependencies on connectors and use cases.
- **AI-assisted triage:** LLM integration for alert summarization, playbook suggestion, and automated investigation narratives in case notes.
- **Scheduled playbooks:** cron-based triggers for recurring tasks (nightly vulnerability summary, weekly compliance checks).
- **SLA tracking:** define response time SLAs per severity level, track compliance, alert on breaches.
- **Multi-tenancy:** environment-scoped data isolation for MSSPs managing multiple clients.
- **Slack/Teams integration:** bidirectional bot for human task approval, alert notifications, and use case review reminders.
- **Playbook analytics:** identify bottleneck steps, suggest optimization (e.g., "this enrichment step adds 15s and never changes the outcome — consider removing it").
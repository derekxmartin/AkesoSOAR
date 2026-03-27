"""initial_schema

Revision ID: b9cc93673767
Revises:
Create Date: 2026-03-27 14:26:14.941725

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b9cc93673767"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- Enum types ---
    userrole = sa.Enum("admin", "soc_manager", "soc_l3", "soc_l2", "soc_l1", "read_only", name="userrole")
    usecasestatus = sa.Enum("draft", "testing", "production", "deprecated", name="usecasestatus")
    severity = sa.Enum("critical", "high", "medium", "low", "informational", name="severity")
    escalationpolicy = sa.Enum("auto", "manual", "conditional", name="escalationpolicy")
    playbooktriggertype = sa.Enum("alert", "manual", "scheduled", name="playbooktriggertype")
    executionstatus = sa.Enum("queued", "running", "paused", "completed", "failed", "cancelled", name="executionstatus")
    stepstatus = sa.Enum("pending", "running", "success", "failed", "skipped", "waiting", name="stepstatus")
    connectortype = sa.Enum("rest", "grpc", name="connectortype")
    humantaskstatus = sa.Enum("pending", "approved", "rejected", "timed_out", "escalated", name="humantaskstatus")

    # --- users ---
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("username", sa.String(150), unique=True, nullable=False),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("role", userrole, nullable=False, server_default="read_only"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("mfa_secret", sa.String(255), nullable=True),
        sa.Column("mfa_enabled", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_username", "users", ["username"])
    op.create_index("ix_users_email", "users", ["email"])

    # --- use_cases ---
    op.create_table(
        "use_cases",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("status", usecasestatus, nullable=False, server_default="draft"),
        sa.Column("severity", severity, nullable=False, server_default="medium"),
        sa.Column("owner_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("review_cadence_days", sa.Integer, nullable=False, server_default="90"),
        sa.Column("last_reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_review_at", sa.DateTime(timezone=True), nullable=True),
        # MITRE
        sa.Column("mitre_tactics", ARRAY(sa.String), nullable=False, server_default="{}"),
        sa.Column("mitre_techniques", ARRAY(sa.String), nullable=False, server_default="{}"),
        sa.Column("mitre_data_sources", ARRAY(sa.String), nullable=False, server_default="{}"),
        # Detection
        sa.Column("sigma_rule_ids", ARRAY(sa.String), nullable=False, server_default="{}"),
        sa.Column("siem_alert_query", sa.Text, nullable=True),
        sa.Column("severity_threshold", severity, nullable=True),
        sa.Column("data_sources_required", JSONB, nullable=True),
        # Response
        sa.Column("escalation_policy", escalationpolicy, nullable=False, server_default="manual"),
        sa.Column("notification_channels", ARRAY(sa.String), nullable=False, server_default="{}"),
        # Documentation
        sa.Column("summary", sa.Text, nullable=False, server_default=""),
        sa.Column("investigation_guide", sa.Text, nullable=False, server_default=""),
        sa.Column("false_positive_guidance", sa.Text, nullable=False, server_default=""),
        sa.Column("references", ARRAY(sa.String), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_use_cases_name", "use_cases", ["name"])
    op.create_index("ix_use_cases_owner_id", "use_cases", ["owner_id"])

    # --- use_case_versions ---
    op.create_table(
        "use_case_versions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("use_case_id", UUID(as_uuid=True), sa.ForeignKey("use_cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("snapshot", JSONB, nullable=False),
        sa.Column("changed_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("change_description", sa.Text, nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_use_case_versions_use_case_id", "use_case_versions", ["use_case_id"])

    # --- playbooks ---
    op.create_table(
        "playbooks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("trigger_type", playbooktriggertype, nullable=False, server_default="alert"),
        sa.Column("trigger_conditions", JSONB, nullable=True),
        sa.Column("definition", JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_playbooks_name", "playbooks", ["name"])

    # --- playbook_versions ---
    op.create_table(
        "playbook_versions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("playbook_id", UUID(as_uuid=True), sa.ForeignKey("playbooks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("definition", JSONB, nullable=False),
        sa.Column("changed_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("change_description", sa.Text, nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_playbook_versions_playbook_id", "playbook_versions", ["playbook_id"])

    # --- use_case_playbooks (association) ---
    op.create_table(
        "use_case_playbooks",
        sa.Column("use_case_id", UUID(as_uuid=True), sa.ForeignKey("use_cases.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("playbook_id", UUID(as_uuid=True), sa.ForeignKey("playbooks.id", ondelete="CASCADE"), primary_key=True),
    )

    # --- executions ---
    op.create_table(
        "executions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("playbook_id", UUID(as_uuid=True), sa.ForeignKey("playbooks.id"), nullable=False),
        sa.Column("playbook_version", sa.Integer, nullable=False),
        sa.Column("trigger_alert_id", sa.String(255), nullable=True),
        sa.Column("use_case_id", UUID(as_uuid=True), sa.ForeignKey("use_cases.id"), nullable=True),
        sa.Column("status", executionstatus, nullable=False, server_default="queued"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_executions_playbook_id", "executions", ["playbook_id"])
    op.create_index("ix_executions_use_case_id", "executions", ["use_case_id"])
    op.create_index("ix_executions_trigger_alert_id", "executions", ["trigger_alert_id"])

    # --- step_results ---
    op.create_table(
        "step_results",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("execution_id", UUID(as_uuid=True), sa.ForeignKey("executions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("step_id", sa.String(255), nullable=False),
        sa.Column("status", stepstatus, nullable=False, server_default="pending"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer, nullable=True),
        sa.Column("input_data", JSONB, nullable=True),
        sa.Column("output_data", JSONB, nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("retry_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_step_results_execution_id", "step_results", ["execution_id"])

    # --- audit_logs ---
    op.create_table(
        "audit_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("actor", sa.String(255), nullable=False, server_default="system"),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(100), nullable=False),
        sa.Column("resource_id", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        sa.Column("details", JSONB, nullable=True),
        sa.Column("before_state", JSONB, nullable=True),
        sa.Column("after_state", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_event_type", "audit_logs", ["event_type"])
    op.create_index("ix_audit_logs_resource_type", "audit_logs", ["resource_type"])
    op.create_index("ix_audit_logs_resource_id", "audit_logs", ["resource_id"])

    # --- connectors ---
    op.create_table(
        "connectors",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), unique=True, nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        sa.Column("connector_type", connectortype, nullable=False),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("config", JSONB, nullable=False, server_default="{}"),
        sa.Column("credentials_encrypted", sa.Text, nullable=True),
        sa.Column("operations", JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_connectors_name", "connectors", ["name"])

    # --- human_tasks ---
    op.create_table(
        "human_tasks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("execution_id", UUID(as_uuid=True), sa.ForeignKey("executions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("step_id", sa.String(255), nullable=False),
        sa.Column("prompt", sa.Text, nullable=False),
        sa.Column("assignee_role", sa.String(50), nullable=False),
        sa.Column("status", humantaskstatus, nullable=False, server_default="pending"),
        sa.Column("timeout_hours", sa.Integer, nullable=False, server_default="4"),
        sa.Column("resolved_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("resolution_note", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_human_tasks_execution_id", "human_tasks", ["execution_id"])

    # --- alerts ---
    op.create_table(
        "alerts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("external_id", sa.String(255), unique=True, nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        sa.Column("severity", severity, nullable=False, server_default="medium"),
        sa.Column("sigma_rule_id", sa.String(255), nullable=True),
        sa.Column("source", sa.String(100), nullable=False, server_default="akeso_siem"),
        sa.Column("raw_payload", JSONB, nullable=False, server_default="{}"),
        sa.Column("status", sa.String(50), nullable=False, server_default="new"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_alerts_external_id", "alerts", ["external_id"])
    op.create_index("ix_alerts_sigma_rule_id", "alerts", ["sigma_rule_id"])


def downgrade() -> None:
    op.drop_table("alerts")
    op.drop_table("human_tasks")
    op.drop_table("connectors")
    op.drop_table("audit_logs")
    op.drop_table("step_results")
    op.drop_table("executions")
    op.drop_table("use_case_playbooks")
    op.drop_table("playbook_versions")
    op.drop_table("playbooks")
    op.drop_table("use_case_versions")
    op.drop_table("use_cases")
    op.drop_table("users")

    # Drop enum types
    for name in [
        "humantaskstatus", "connectortype", "stepstatus", "executionstatus",
        "playbooktriggertype", "escalationpolicy", "severity", "usecasestatus", "userrole",
    ]:
        sa.Enum(name=name).drop(op.get_bind(), checkfirst=True)

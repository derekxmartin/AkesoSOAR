"""Execution and StepResult models for playbook runs."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from akeso_soar.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from akeso_soar.models.enums import ExecutionStatus, StepStatus


class Execution(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "executions"

    playbook_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("playbooks.id"), nullable=False, index=True
    )
    playbook_version: Mapped[int] = mapped_column(Integer, nullable=False)
    trigger_alert_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    use_case_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("use_cases.id"), nullable=True, index=True
    )
    status: Mapped[ExecutionStatus] = mapped_column(nullable=False, default=ExecutionStatus.QUEUED)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    playbook: Mapped[Playbook] = relationship(back_populates="executions")  # noqa: F821
    step_results: Mapped[list[StepResult]] = relationship(
        back_populates="execution", lazy="selectin", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Execution {self.id} playbook={self.playbook_id} status={self.status.value}>"


class StepResult(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "step_results"

    execution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("executions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    step_id: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[StepStatus] = mapped_column(nullable=False, default=StepStatus.PENDING)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    input_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    output_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relationships
    execution: Mapped[Execution] = relationship(back_populates="step_results")

    def __repr__(self) -> str:
        return f"<StepResult {self.step_id} status={self.status.value}>"

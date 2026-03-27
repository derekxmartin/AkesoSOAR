"""Use Case and Use Case Version models."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from akeso_soar.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from akeso_soar.models.enums import EscalationPolicy, Severity, UseCaseStatus


class UseCase(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "use_cases"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[UseCaseStatus] = mapped_column(nullable=False, default=UseCaseStatus.DRAFT)
    severity: Mapped[Severity] = mapped_column(nullable=False, default=Severity.MEDIUM)

    # Ownership & review
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    review_cadence_days: Mapped[int] = mapped_column(Integer, nullable=False, default=90)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_review_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # MITRE ATT&CK mapping
    mitre_tactics: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    mitre_techniques: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    mitre_data_sources: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)

    # Detection binding
    sigma_rule_ids: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    siem_alert_query: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity_threshold: Mapped[Severity | None] = mapped_column(nullable=True)
    data_sources_required: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Response binding
    escalation_policy: Mapped[EscalationPolicy] = mapped_column(nullable=False, default=EscalationPolicy.MANUAL)
    notification_channels: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)

    # Documentation
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    investigation_guide: Mapped[str] = mapped_column(Text, nullable=False, default="")
    false_positive_guidance: Mapped[str] = mapped_column(Text, nullable=False, default="")
    references: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)

    # Relationships
    owner_user: Mapped[User] = relationship(back_populates="owned_use_cases", lazy="selectin")  # noqa: F821
    versions: Mapped[list[UseCaseVersion]] = relationship(back_populates="use_case", lazy="selectin")
    playbook_links: Mapped[list[UseCasePlaybook]] = relationship(back_populates="use_case", lazy="selectin")  # noqa: F821

    def __repr__(self) -> str:
        return f"<UseCase {self.name} v{self.version} ({self.status.value})>"


class UseCaseVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "use_case_versions"

    use_case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("use_cases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    changed_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    change_description: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # Relationships
    use_case: Mapped[UseCase] = relationship(back_populates="versions")

    def __repr__(self) -> str:
        return f"<UseCaseVersion use_case={self.use_case_id} v{self.version}>"

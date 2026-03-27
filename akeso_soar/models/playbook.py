"""Playbook and Playbook Version models."""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from akeso_soar.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from akeso_soar.models.enums import PlaybookTriggerType


class Playbook(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "playbooks"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    trigger_type: Mapped[PlaybookTriggerType] = mapped_column(nullable=False, default=PlaybookTriggerType.ALERT)
    trigger_conditions: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # The full DAG definition as YAML-parsed JSON
    definition: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Relationships
    versions: Mapped[list[PlaybookVersion]] = relationship(back_populates="playbook", lazy="selectin")
    executions: Mapped[list[Execution]] = relationship(back_populates="playbook", lazy="selectin")  # noqa: F821
    use_case_links: Mapped[list[UseCasePlaybook]] = relationship(back_populates="playbook", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Playbook {self.name} v{self.version} enabled={self.enabled}>"


class PlaybookVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "playbook_versions"

    playbook_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("playbooks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    definition: Mapped[dict] = mapped_column(JSONB, nullable=False)
    changed_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    change_description: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # Relationships
    playbook: Mapped[Playbook] = relationship(back_populates="versions")

    def __repr__(self) -> str:
        return f"<PlaybookVersion playbook={self.playbook_id} v{self.version}>"


class UseCasePlaybook(Base):
    """Association table linking use cases to playbooks."""

    __tablename__ = "use_case_playbooks"

    use_case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("use_cases.id", ondelete="CASCADE"), primary_key=True
    )
    playbook_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("playbooks.id", ondelete="CASCADE"), primary_key=True
    )

    use_case: Mapped[UseCase] = relationship(back_populates="playbook_links")  # noqa: F821
    playbook: Mapped[Playbook] = relationship(back_populates="use_case_links")

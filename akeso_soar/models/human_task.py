"""Human task model for playbook approval gates."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from akeso_soar.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from akeso_soar.models.enums import HumanTaskStatus


class HumanTask(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "human_tasks"

    execution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("executions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    step_id: Mapped[str] = mapped_column(String(255), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    assignee_role: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[HumanTaskStatus] = mapped_column(nullable=False, default=HumanTaskStatus.PENDING)
    timeout_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=4)

    # Resolution
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<HumanTask step={self.step_id} status={self.status.value}>"

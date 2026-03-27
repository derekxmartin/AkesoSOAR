"""Alert model for ingested SIEM alerts."""

from __future__ import annotations

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from akeso_soar.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from akeso_soar.models.enums import Severity


class Alert(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "alerts"

    external_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True, unique=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    severity: Mapped[Severity] = mapped_column(nullable=False, default=Severity.MEDIUM)
    sigma_rule_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    source: Mapped[str] = mapped_column(String(100), nullable=False, default="akeso_siem")
    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="new")

    def __repr__(self) -> str:
        return f"<Alert {self.external_id} severity={self.severity.value}>"

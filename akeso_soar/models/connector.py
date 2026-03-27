"""Connector model for Akeso product integrations."""

from __future__ import annotations

from sqlalchemy import Boolean, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from akeso_soar.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from akeso_soar.models.enums import ConnectorType


class Connector(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "connectors"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    connector_type: Mapped[ConnectorType] = mapped_column(nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Connection configuration (host, port, etc.) — non-secret
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Encrypted credentials blob (Fernet-encrypted JSON)
    credentials_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Available operations metadata
    operations: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    def __repr__(self) -> str:
        return f"<Connector {self.name} ({self.connector_type.value}) enabled={self.enabled}>"

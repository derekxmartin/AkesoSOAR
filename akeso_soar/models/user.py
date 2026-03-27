"""User model for authentication and RBAC."""

from __future__ import annotations

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from akeso_soar.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from akeso_soar.models.enums import UserRole


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(150), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(nullable=False, default=UserRole.READ_ONLY)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # MFA
    mfa_secret: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    owned_use_cases: Mapped[list[UseCase]] = relationship(back_populates="owner_user", lazy="selectin")  # noqa: F821
    audit_logs: Mapped[list[AuditLog]] = relationship(back_populates="user", lazy="selectin")  # noqa: F821

    def __repr__(self) -> str:
        return f"<User {self.username} ({self.role.value})>"

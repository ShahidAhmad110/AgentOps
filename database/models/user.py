from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import Boolean, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base, SoftDeleteMixin, TimestampMixin


class User(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"
    __table_args__ = (Index("ix_users_role_org", "role", "organization_id"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    username: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="user", index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    organization_id: Mapped[UUID | None] = mapped_column(ForeignKey("organizations.id"), nullable=True, index=True)

    organization: Mapped["Organization | None"] = relationship(back_populates="users")

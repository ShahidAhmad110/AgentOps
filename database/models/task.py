from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base, SoftDeleteMixin, TimestampMixin


TASK_STATUSES = {"TODO", "IN_PROGRESS", "BLOCKED", "COMPLETED", "CANCELLED"}


class Task(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "tasks"
    __table_args__ = (
        CheckConstraint(
            "status IN ('TODO', 'IN_PROGRESS', 'BLOCKED', 'COMPLETED', 'CANCELLED')",
            name="ck_tasks_status",
        ),
        Index("ix_tasks_organization_status", "organization_id", "status"),
        Index("ix_tasks_organization_assignee", "organization_id", "assignee_id"),
        Index("ix_tasks_due_date", "due_date"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    assignee_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="TODO", index=True)
    priority: Mapped[str | None] = mapped_column(String(32), nullable=True)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    comments: Mapped[list["TaskComment"]] = relationship(
        back_populates="task", cascade="all, delete-orphan", order_by="TaskComment.created_at"
    )


class TaskComment(Base, TimestampMixin):
    __tablename__ = "task_comments"
    __table_args__ = (Index("ix_task_comments_task_created", "task_id", "created_at"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    task_id: Mapped[UUID] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    author_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    task: Mapped[Task] = relationship(back_populates="comments")

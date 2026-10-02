from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.task import Task

logger = logging.getLogger("agentops.workers.task")


class TaskWorkerScheduler:
    """Background task scheduler for maintenance and execution state checks."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def scan_overdue_tasks(self) -> int:
        """Identifies tasks that have passed their due date and remain uncompleted."""
        now = datetime.now(timezone.utc)
        stmt = (
            select(Task)
            .where(
                Task.due_date < now,
                Task.status.notin_(["COMPLETED", "CANCELLED"]),
            )
        )
        result = await self.session.execute(stmt)
        overdue_tasks = list(result.scalars().all())
        if overdue_tasks:
            logger.info(f"Found {len(overdue_tasks)} overdue tasks requiring attention.")
        return len(overdue_tasks)

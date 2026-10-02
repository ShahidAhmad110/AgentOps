from __future__ import annotations

import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.document import Document
from database.models.agent_execution import AgentRun

logger = logging.getLogger("agentops.workers.maintenance")


class MaintenanceWorker:
    """Maintenance tasks including storage verification and execution hygiene."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def check_storage_hygiene(self) -> dict[str, int]:
        """Audits database document records count and agent runs."""
        doc_stmt = select(Document)
        doc_result = await self.session.execute(doc_stmt)
        total_docs = len(doc_result.scalars().all())

        exec_stmt = select(AgentRun)
        exec_result = await self.session.execute(exec_stmt)
        total_execs = len(exec_result.scalars().all())

        stats = {"total_documents": total_docs, "total_executions": total_execs}
        logger.info(f"Maintenance hygiene check complete: {stats}")
        return stats

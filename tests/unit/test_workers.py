from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from workers.document_worker.processor import DocumentWorkerProcessor
from workers.maintenance.cleanup import MaintenanceWorker
from workers.task_worker.scheduler import TaskWorkerScheduler
from database.models.document import Document


@pytest.mark.asyncio
async def test_task_worker_scheduler_overdue() -> None:
    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    session.execute.return_value = mock_result

    scheduler = TaskWorkerScheduler(session)
    count = await scheduler.scan_overdue_tasks()
    assert count == 0
    assert session.execute.called


@pytest.mark.asyncio
async def test_maintenance_worker_hygiene() -> None:
    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    session.execute.return_value = mock_result

    worker = MaintenanceWorker(session)
    stats = await worker.check_storage_hygiene()
    assert stats["total_documents"] == 0
    assert stats["total_executions"] == 0


@pytest.mark.asyncio
async def test_document_worker_processor_nonexistent() -> None:
    session = AsyncMock()
    processor = DocumentWorkerProcessor(session)
    processor.repository.get = AsyncMock(return_value=None)

    with pytest.raises(ValueError, match="not found"):
        from uuid import uuid4
        await processor.process_document(uuid4())

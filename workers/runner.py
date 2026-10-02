from __future__ import annotations

import asyncio
import logging
import signal
import sys

from backend.core.config import get_settings
from database.connection.session import session_factory
from workers.document_worker.processor import DocumentWorkerProcessor
from workers.maintenance.cleanup import MaintenanceWorker
from workers.task_worker.scheduler import TaskWorkerScheduler

logging.basicConfig(
    level=getattr(logging, get_settings().log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("agentops.workers.runner")


class WorkerRunner:
    def __init__(self, poll_interval: float = 5.0) -> None:
        self.poll_interval = poll_interval
        self.running = True

    def stop(self) -> None:
        logger.info("Worker runner stopping gracefully...")
        self.running = False

    async def run_loop(self) -> None:
        logger.info("AgentOps Background Worker daemon started.")
        while self.running:
            try:
                async with session_factory() as session:
                    doc_processor = DocumentWorkerProcessor(session)
                    processed = await doc_processor.process_pending_documents(batch_size=5)
                    if processed:
                        logger.info(f"Worker processed {processed} pending documents.")

                    task_scheduler = TaskWorkerScheduler(session)
                    await task_scheduler.scan_overdue_tasks()

                    maintenance = MaintenanceWorker(session)
                    await maintenance.check_storage_hygiene()

            except Exception as exc:
                logger.error(f"Error during worker loop iteration: {exc}", exc_info=True)

            try:
                await asyncio.sleep(self.poll_interval)
            except asyncio.CancelledError:
                break


def main() -> None:
    runner = WorkerRunner()

    def handle_signal(*_: object) -> None:
        runner.stop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, handle_signal)
        except (AttributeError, ValueError):
            pass

    try:
        asyncio.run(runner.run_loop())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Worker runner terminated.")


if __name__ == "__main__":
    main()

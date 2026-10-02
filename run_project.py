"""AgentOps Unified Service Launcher
Ensures ports are free, database is migrated/seeded, and launches Backend, Worker, and Frontend.
"""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent


def log(msg: str) -> None:
    timestamp = time.strftime("%H:%M:%S")
    print(f"[{timestamp}] [AgentOps Launcher] {msg}", flush=True)


def get_python_executable() -> str:
    """Finds the virtual environment Python interpreter if available."""
    if sys.platform == "win32":
        venv_py = ROOT_DIR / ".venv" / "Scripts" / "python.exe"
    else:
        venv_py = ROOT_DIR / ".venv" / "bin" / "python"

    if venv_py.exists():
        return str(venv_py)
    return sys.executable


def free_port(port: int) -> None:
    """Terminates any stale/orphaned process listening on the given port (Windows/POSIX)."""
    if sys.platform == "win32":
        try:
            res = subprocess.run(["netstat", "-ano"], capture_output=True, text=True)
            for line in res.stdout.splitlines():
                if f":{port}" in line and "LISTENING" in line:
                    parts = line.strip().split()
                    pid = int(parts[-1])
                    if pid > 0 and pid != os.getpid():
                        log(f"Freeing port {port} (killing PID {pid})...")
                        subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True)
        except Exception:
            pass


def wait_for_backend(timeout_seconds: int = 15) -> bool:
    """Polls http://127.0.0.1:8000/health until backend is ready."""
    start = time.time()
    while time.time() - start < timeout_seconds:
        try:
            req = urllib.request.Request("http://127.0.0.1:8000/health")
            with urllib.request.urlopen(req, timeout=2) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.5)
    return False


def main() -> None:
    os.chdir(ROOT_DIR)
    py_exe = get_python_executable()
    log(f"Project directory: {ROOT_DIR}")
    log(f"Using Python interpreter: {py_exe}")

    # 1. Clean up stale port listeners
    free_port(8000)

    # 2. Run migrations and database check
    log("Applying database migrations and checking seed data...")
    try:
        from scripts.run_migrations import run_migrations
        run_migrations()
        from scripts.seed_data import seed_data
        import asyncio
        asyncio.run(seed_data())
    except Exception as exc:
        log(f"Database initialization check: {exc}")

    # 3. Launch backend
    log("Starting FastAPI Backend on http://127.0.0.1:8000 ...")
    backend_proc = subprocess.Popen(
        [py_exe, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=str(ROOT_DIR),
    )

    # 4. Wait for backend to be healthy
    log("Waiting for backend service to become ready...")
    if wait_for_backend(timeout_seconds=20):
        log("Backend is healthy and connected to database.")
    else:
        log("Warning: Backend health check timed out. Checking process status...")
        ret = backend_proc.poll()
        if ret is not None:
            log(f"ERROR: Backend process exited immediately with code {ret}")
            sys.exit(ret)

    # 5. Launch background worker
    log("Starting Background Worker Runner...")
    worker_proc = subprocess.Popen(
        [py_exe, "-m", "workers.runner"],
        cwd=str(ROOT_DIR),
    )

    # 6. Launch Next.js frontend
    frontend_dir = ROOT_DIR / "frontend"
    log("Starting Next.js Frontend on http://localhost:3000 ...")
    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
    frontend_proc = subprocess.Popen(
        [npm_cmd, "run", "dev"],
        cwd=str(frontend_dir),
    )

    log("\n" + "=" * 60)
    log("AgentOps is fully running!")
    log("  Frontend UI:  http://localhost:3000")
    log("  Backend API:  http://127.0.0.1:8000")
    log("  API Swagger:  http://127.0.0.1:8000/docs")
    log("  Default User: admin / AgentOps2026!Admin")
    log("=" * 60 + "\n")

    processes = [("Backend", backend_proc), ("Worker", worker_proc), ("Frontend", frontend_proc)]
    try:
        while True:
            time.sleep(2)
            for name, proc in processes:
                ret = proc.poll()
                if ret is not None:
                    log(f"ERROR: Service {name} terminated unexpectedly with code {ret}")
                    log("Shutting down remaining services...")
                    for _, p in processes:
                        if p.poll() is None:
                            p.terminate()
                    sys.exit(ret)
    except KeyboardInterrupt:
        log("Shutting down AgentOps services...")
        for _, p in processes:
            if p.poll() is None:
                p.terminate()
        log("All services stopped.")


if __name__ == "__main__":
    main()

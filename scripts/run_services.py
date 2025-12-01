#!/usr/bin/env python3
"""Launch the four microservices listed in the README and stream their logs.

Usage:
    python scripts/run_services.py

Optional env vars:
    KM_PYTHON       Absolute path to the interpreter used to run each service
                    (defaults to ./venv/bin/python3 when present, otherwise the
                    interpreter executing this script).
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import threading
from pathlib import Path
from typing import List, Sequence

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VENV_PYTHON = ROOT / "venv" / "bin" / "python3"

SERVICES: Sequence[tuple[str, List[str]]] = (
    ("pymupdf_service", ["microservices/pymupdf_service/main.py"]),
    ("chunking_service", ["microservices/chunking_service/main.py"]),
    ("openai_embedding_client_service", ["microservices/openai_embedding_client_service/main.py"]),
    ("openai_llm_client_service", ["microservices/openai_llm_client_service/main.py"]),
    ("mineru_service", ["microservices/mineru_service/main.py"]),
)


def resolve_python() -> str:
    explicit = os.getenv("KM_PYTHON")
    if explicit:
        return explicit
    if DEFAULT_VENV_PYTHON.exists():
        return str(DEFAULT_VENV_PYTHON)
    # Fallback to the interpreter running this helper
    return sys.executable


def stream_output(name: str, process: subprocess.Popen[str]) -> None:
    prefix = f"[{name}] "
    if not process.stdout:
        return
    for line in process.stdout:
        print(f"{prefix}{line.rstrip()}", flush=True)


def start_services(python_bin: str) -> List[subprocess.Popen[str]]:
    processes: List[subprocess.Popen[str]] = []
    for name, args in SERVICES:
        cmd = [python_bin, *args]
        process = subprocess.Popen(
            cmd,
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        thread = threading.Thread(target=stream_output, args=(name, process), daemon=True)
        thread.start()
        processes.append(process)
        print(f"Started {name} (pid={process.pid})", flush=True)
    return processes


def terminate_process(process: subprocess.Popen[str], graceful_timeout: float = 5.0) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=graceful_timeout)
    except subprocess.TimeoutExpired:
        process.kill()


def shutdown(processes: Sequence[subprocess.Popen[str]]) -> None:
    for process in processes:
        terminate_process(process)


def main() -> None:
    python_bin = resolve_python()
    print(f"Using interpreter: {python_bin}")
    processes = start_services(python_bin)

    terminate_event = threading.Event()

    def handle_signal(signum, _frame):
        print(f"Received signal {signum}, shutting down services...", flush=True)
        terminate_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, handle_signal)

    try:
        while not terminate_event.is_set():
            # Poll child processes; exit if any one ends unexpectedly.
            for process, (name, _) in zip(processes, SERVICES):
                retcode = process.poll()
                if retcode is not None:
                    print(f"{name} exited with code {retcode}, stopping remaining services.")
                    terminate_event.set()
                    break
            terminate_event.wait(timeout=1.0)
    finally:
        shutdown(processes)
        print("All services stopped.")


if __name__ == "__main__":
    main()

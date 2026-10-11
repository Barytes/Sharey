import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from sharey.server import create_app

ROOT = Path(__file__).resolve().parents[1]
CONFIG = {
    "projects": {
        "demo": {"goal": "Compare measurements", "token": "demo-secret"},
        "other": {"goal": "Other research", "token": "other-secret"},
    }
}
AUTH = {"Authorization": "Bearer demo-secret"}


@pytest.fixture
def api(tmp_path):
    with TestClient(create_app(tmp_path / "data", CONFIG)) as client:
        yield client


class LiveService:
    def __init__(self, root):
        self.root = root
        self.data = root / "data"
        self.config = root / "server.json"
        self.config.write_text(json.dumps(CONFIG))
        self.process = None
        self.log = None
        self.url = ""

    def start(self, extra_env=None):
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        self.url = f"http://127.0.0.1:{port}"
        self.log = (self.root / "server.log").open("ab")
        self.process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "sharey.cli",
                "serve",
                "--config",
                str(self.config),
                "--data-dir",
                str(self.data),
                "--port",
                str(port),
            ],
            cwd=self.root,
            env={**os.environ, **(extra_env or {})},
            stdout=self.log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                raise AssertionError((self.root / "server.log").read_text())
            try:
                if httpx.get(self.url + "/health", timeout=0.2).status_code == 200:
                    return self
            except httpx.HTTPError:
                pass
            time.sleep(0.03)
        raise AssertionError("Service did not become ready")

    def stop(self, kill=False):
        import signal

        if self.process and self.process.poll() is None:
            os.killpg(self.process.pid, signal.SIGKILL if kill else signal.SIGTERM)
            self.process.wait(timeout=10)
        if self.log:
            self.log.close()


@pytest.fixture
def service(tmp_path):
    server = LiveService(tmp_path)
    try:
        yield server.start()
    finally:
        server.stop()


@pytest.fixture
def cli():
    def run(server, workspace, *args, token="demo-secret", extra_env=None):
        env = {
            **os.environ,
            "SHAREY_URL": server.url,
            "SHAREY_PROJECT": "demo",
            "SHAREY_TOKEN": token,
            **(extra_env or {}),
        }
        return subprocess.run(
            [sys.executable, "-m", "sharey.cli", *args],
            cwd=workspace,
            env=env,
            capture_output=True,
            text=True,
            timeout=20,
        )

    return run

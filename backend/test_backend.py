#!/usr/bin/env python
"""Quick backend startup test."""
import json
import socket
import sys
import subprocess
import time
import urllib.request
import urllib.error
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

print("=" * 60)
print("Testing FastAPI Backend Startup")
print("=" * 60)

def _get_json(url: str, timeout: int = 5) -> tuple[int, dict]:
    response = urllib.request.urlopen(url, timeout=timeout)
    return response.status, json.loads(response.read().decode())


def _post_json(url: str, payload: dict, timeout: int = 5) -> tuple[int, dict]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        response = urllib.request.urlopen(request, timeout=timeout)
        return response.status, json.loads(response.read().decode())
    except urllib.error.HTTPError as error:
        body = error.read().decode()
        parsed = json.loads(body) if body else {}
        return error.code, parsed


proc = None
failed = False
messages: list[str] = []
port = 8001


def _reserve_port() -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    chosen = sock.getsockname()[1]
    sock.close()
    return chosen


def _wait_for_health(url: str, proc: subprocess.Popen, timeout_seconds: int = 120) -> tuple[int, dict]:
    deadline = time.time() + timeout_seconds
    last_error: Exception | None = None
    while time.time() < deadline:
        if proc.poll() is not None:
            stderr_text = proc.stderr.read() if proc.stderr else ""
            raise RuntimeError(f"Backend process exited early. stderr={stderr_text}")
        try:
            return _get_json(url, timeout=5)
        except Exception as error:
            last_error = error
            time.sleep(1)
    if last_error is None:
        raise RuntimeError("Timed out waiting for backend health")
    raise last_error


try:
    port = _reserve_port()
    print(f"\n1. Starting FastAPI server on port {port}...")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.api.main:app", "--host", "127.0.0.1", "--port", str(port)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    print("   Waiting for server initialization...")

    print("\n2. Testing /health...")
    status, health = _wait_for_health(
        f"http://127.0.0.1:{port}/health",
        proc=proc,
        timeout_seconds=120,
    )
    if status != 200 or health.get("status") != "ok":
        failed = True
        messages.append(f"/health expected 200+ok, got status={status}, body={health}")

    print("3. Testing /api/team/test/profile...")
    status, profile = _get_json(f"http://127.0.0.1:{port}/api/team/test/profile", timeout=20)
    if status != 200 or "team_id" not in profile:
        failed = True
        messages.append(f"/api/team/test/profile expected 200 with team_id, got status={status}, body={profile}")

    print("4. Testing /api/coach-qa missing-match behavior...")
    status, qa = _post_json(
        f"http://127.0.0.1:{port}/api/coach-qa",
        {"match_id": "missing-match", "question": "why?"},
        timeout=20,
    )
    if status != 404:
        failed = True
        messages.append(f"/api/coach-qa expected 404 for missing match, got status={status}, body={qa}")

except Exception as error:
    failed = True
    messages.append(f"Unexpected test failure: {error}")
finally:
    print("\n5. Shutting down test server...")
    if proc is not None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

if failed:
    print("\nBackend verification failed:")
    for msg in messages:
        print(f"- {msg}")
    print("=" * 60)
    sys.exit(1)

print("\nBackend verification complete")
print("=" * 60)

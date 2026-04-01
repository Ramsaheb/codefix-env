import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parent
PYTHON = sys.executable

IMAGE = os.getenv("PREDEPLOY_IMAGE", "codefix-env:predeploy")
CONTAINER = os.getenv("PREDEPLOY_CONTAINER", "codefix-env-predeploy")
PORT = int(os.getenv("PREDEPLOY_PORT", "7860"))
BASE_URL = f"http://127.0.0.1:{PORT}"


class StepFailed(RuntimeError):
    pass


def run_command(title: str, command: list[str], env: dict | None = None, required: bool = True) -> int:
    print(f"\n==> {title}")
    print("$", " ".join(command))

    process = subprocess.run(command, cwd=ROOT, env=env, check=False)
    if required and process.returncode != 0:
        raise StepFailed(f"{title} failed with exit code {process.returncode}")

    return process.returncode


def wait_for_health(timeout_seconds: int = 45) -> None:
    print(f"\n==> Waiting for container health at {BASE_URL}/health")
    start = time.time()

    while time.time() - start <= timeout_seconds:
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=3)
            if response.status_code == 200:
                print("Health endpoint is ready")
                return
        except requests.RequestException:
            pass

        time.sleep(1)

    raise StepFailed("Container health check timed out")


def run_api_smoke_checks() -> None:
    print("\n==> API smoke checks")

    ready_response = requests.get(f"{BASE_URL}/ready", timeout=10)
    if ready_response.status_code != 200:
        raise StepFailed(f"/ready failed with {ready_response.status_code}")

    payload = ready_response.json()
    tasks = set(payload.get("tasks", []))
    required_tasks = {"easy", "medium", "hard", "expert", "nightmare"}
    if not required_tasks.issubset(tasks):
        raise StepFailed(f"/ready missing tasks. expected={sorted(required_tasks)} got={sorted(tasks)}")

    easy_reset = requests.post(f"{BASE_URL}/reset", json={"task": "easy"}, timeout=10)
    if easy_reset.status_code != 200:
        raise StepFailed(f"easy /reset failed with {easy_reset.status_code}")

    easy_session = easy_reset.json().get("session_id", "")
    easy_step = requests.post(
        f"{BASE_URL}/step",
        json={"session_id": easy_session, "action": "fix_syntax"},
        timeout=10,
    )
    if easy_step.status_code != 200:
        raise StepFailed(f"easy /step failed with {easy_step.status_code}")

    nightmare_reset = requests.post(f"{BASE_URL}/reset", json={"task": "nightmare"}, timeout=10)
    if nightmare_reset.status_code != 200:
        raise StepFailed(f"nightmare /reset failed with {nightmare_reset.status_code}")

    nightmare_session = nightmare_reset.json().get("session_id", "")
    first = requests.post(
        f"{BASE_URL}/step",
        json={"session_id": nightmare_session, "action": "fix_syntax"},
        timeout=10,
    )
    second = requests.post(
        f"{BASE_URL}/step",
        json={"session_id": nightmare_session, "action": "fix_logic"},
        timeout=10,
    )

    if first.status_code != 200 or second.status_code != 200:
        raise StepFailed("nightmare flow /step checks failed")

    if not second.json().get("done", False):
        raise StepFailed("nightmare flow did not converge as expected")

    print("API smoke checks passed")


def run_inference_smoke() -> None:
    print("\n==> Inference smoke (deterministic fallback policy)")
    env = os.environ.copy()
    env["API_BASE_URL"] = BASE_URL
    env["USE_LLM_POLICY"] = "false"
    env["HF_TOKEN"] = ""
    run_command("inference.py smoke", [PYTHON, "inference.py"], env=env, required=True)


def main() -> int:
    if shutil.which("docker") is None:
        print("docker command not found in PATH")
        return 1

    container_started = False
    try:
        run_command("Unit and API tests", [PYTHON, "-m", "pytest", "-q"]) 
        run_command("Benchmark", [PYTHON, "benchmark.py"])

        run_command("Remove existing predeploy container (if any)", ["docker", "rm", "-f", CONTAINER], required=False)
        run_command("Docker build", ["docker", "build", "-t", IMAGE, "."])
        run_command(
            "Start container",
            [
                "docker",
                "run",
                "--rm",
                "-d",
                "-p",
                f"{PORT}:7860",
                "--name",
                CONTAINER,
                IMAGE,
            ],
        )
        container_started = True

        wait_for_health()
        run_api_smoke_checks()
        run_inference_smoke()

        print("\nAll predeploy checks passed")
        return 0
    except StepFailed as exc:
        print(f"\nPredeploy checks failed: {exc}")
        return 1
    finally:
        if container_started:
            run_command("Stop container", ["docker", "stop", CONTAINER], required=False)


if __name__ == "__main__":
    raise SystemExit(main())
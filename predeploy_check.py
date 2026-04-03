"""
Pre-deploy validation script.

Runs unit tests, benchmark, Docker build/run, API smoke checks,
and inference smoke against a local container.
"""

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


def run_command(
    title: str,
    command: list[str],
    env: dict | None = None,
    required: bool = True,
) -> int:
    print(f"\n==> {title}")
    print("$", " ".join(command))
    process = subprocess.run(command, cwd=ROOT, env=env, check=False)
    if required and process.returncode != 0:
        raise StepFailed(f"{title} failed with exit code {process.returncode}")
    return process.returncode


def wait_for_health(timeout_seconds: int = 60) -> None:
    print(f"\n==> Waiting for container health at {BASE_URL}/health")
    start = time.time()
    while time.time() - start <= timeout_seconds:
        try:
            resp = requests.get(f"{BASE_URL}/health", timeout=3)
            if resp.status_code == 200:
                print("Health endpoint is ready")
                return
        except requests.RequestException:
            pass
        time.sleep(1)
    raise StepFailed("Container health check timed out")


def run_api_smoke_checks() -> None:
    print("\n==> API smoke checks")

    # Schema endpoint
    schema_resp = requests.get(f"{BASE_URL}/schema", timeout=10)
    if schema_resp.status_code != 200:
        raise StepFailed(f"/schema failed with {schema_resp.status_code}")
    schema = schema_resp.json()
    if "action" not in schema or "observation" not in schema:
        raise StepFailed("/schema missing action or observation keys")

    # Reset
    reset_resp = requests.post(
        f"{BASE_URL}/reset", json={"task": "easy"}, timeout=10
    )
    if reset_resp.status_code != 200:
        raise StepFailed(f"/reset failed with {reset_resp.status_code}")
    reset_data = reset_resp.json()
    if "observation" not in reset_data:
        raise StepFailed("/reset response missing 'observation'")

    # Step
    step_resp = requests.post(
        f"{BASE_URL}/step",
        json={"action": {"action": "fix_syntax"}},
        timeout=10,
    )
    if step_resp.status_code != 200:
        raise StepFailed(f"/step failed with {step_resp.status_code}")
    step_data = step_resp.json()
    if "observation" not in step_data or "done" not in step_data:
        raise StepFailed("/step response missing required keys")

    # Nightmare multi-step
    reset2 = requests.post(
        f"{BASE_URL}/reset", json={"task": "nightmare"}, timeout=10
    )
    if reset2.status_code != 200:
        raise StepFailed(f"nightmare /reset failed with {reset2.status_code}")

    s1 = requests.post(
        f"{BASE_URL}/step",
        json={"action": {"action": "fix_syntax"}},
        timeout=10,
    )
    s2 = requests.post(
        f"{BASE_URL}/step",
        json={"action": {"action": "fix_logic"}},
        timeout=10,
    )
    if s1.status_code != 200 or s2.status_code != 200:
        raise StepFailed("nightmare /step checks failed")

    print("API smoke checks passed")


def run_inference_smoke() -> None:
    print("\n==> Inference smoke (deterministic fallback policy)")
    env = os.environ.copy()
    env["API_BASE_URL"] = BASE_URL
    env["USE_LLM_POLICY"] = "false"
    env["HF_TOKEN"] = ""
    env["OPENAI_API_KEY"] = ""
    run_command("inference.py smoke", [PYTHON, "inference.py"], env=env, required=True)


def main() -> int:
    if shutil.which("docker") is None:
        print("docker command not found in PATH")
        return 1

    container_started = False
    try:
        run_command("Unit tests", [PYTHON, "-m", "pytest", "-q"])
        run_command("Benchmark", [PYTHON, "benchmark.py"])
        run_command(
            "Remove existing container",
            ["docker", "rm", "-f", CONTAINER],
            required=False,
        )
        run_command("Docker build", ["docker", "build", "-t", IMAGE, "."])
        run_command(
            "Start container",
            [
                "docker", "run", "--rm", "-d",
                "-p", f"{PORT}:7860",
                "--name", CONTAINER,
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
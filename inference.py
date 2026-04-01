import os
import time
from typing import Dict

import requests


API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:7860").rstrip("/")
MODEL_NAME = os.getenv("MODEL_NAME", "demo-rule-agent")
HF_TOKEN = os.getenv("HF_TOKEN", "")
TASK_NAME = os.getenv("TASK_NAME", "easy")
MAX_STEPS = int(os.getenv("MAX_STEPS", "8"))


def choose_action(state: Dict[str, object]) -> str:
    code = str(state.get("code", ""))
    error = str(state.get("error", ""))

    if "SyntaxError" in error or 'print("Hello' in code or "if a > b\n" in code:
        return "fix_syntax"

    if "a-b" in code or "a - b" in code:
        return "fix_logic"

    return "noop"


def main() -> None:
    headers = {}
    if HF_TOKEN:
        headers["Authorization"] = f"Bearer {HF_TOKEN}"

    print(f"Starting demo inference with model: {MODEL_NAME}")

    reset_resp = requests.post(
        f"{API_BASE_URL}/reset",
        json={"task": TASK_NAME},
        headers=headers,
        timeout=20,
    )
    reset_resp.raise_for_status()

    state = reset_resp.json()["state"]
    done = False
    step = 0

    while not done and step < MAX_STEPS:
        action = choose_action(state)
        step_resp = requests.post(
            f"{API_BASE_URL}/step",
            json={"action": action},
            headers=headers,
            timeout=20,
        )
        step_resp.raise_for_status()

        payload = step_resp.json()
        state = payload["state"]
        done = bool(payload["done"])
        step += 1

        print(
            f"step={step} action={action} reward={payload['reward']} "
            f"score={payload['score']} done={done}"
        )

        time.sleep(0.1)


if __name__ == "__main__":
    main()
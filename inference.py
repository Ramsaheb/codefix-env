"""
inference.py — OpenEnv Hackathon inference script for CodeFixEnv.

Environment variables:
    API_BASE_URL   The API endpoint for the LLM.
    MODEL_NAME     The model identifier to use for inference.
    HF_TOKEN       Your Hugging Face / API key.
    ENV_API_BASE_URL  The environment server URL (default: http://localhost:7860).

STDOUT FORMAT:
    [START] task=<task_name> env=<benchmark> model=<model_name>
    [STEP]  step=<n> action=<action_str> reward=<0.00> done=<true|false> error=<msg|null>
    [END]   success=<true|false> steps=<n> score=<score> rewards=<r1,r2,...,rn>
"""

import os
import re
import time
from typing import Dict, List, Optional

from openai import OpenAI
import requests


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1").rstrip("/")
ENV_API_BASE_URL = os.getenv("ENV_API_BASE_URL", "http://localhost:7860").rstrip("/")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY", "")
BENCHMARK = os.getenv("BENCHMARK", "codefix-env")
LOCAL_IMAGE_NAME = os.getenv("LOCAL_IMAGE_NAME", "")
MAX_STEPS = int(os.getenv("MAX_STEPS", "8"))
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "20"))
USE_LLM_POLICY = os.getenv("USE_LLM_POLICY", "true").strip().lower() in {"1", "true", "yes"}
MAX_LLM_RETRIES = int(os.getenv("MAX_LLM_RETRIES", "2"))

# All tasks to evaluate — at least 3 required by the validator
ALL_TASKS: List[str] = ["easy", "medium", "hard", "expert", "nightmare"]

SYSTEM_PROMPT = (
    "You are a deterministic code-fixing policy. Return exactly one action and nothing else. "
    "Allowed actions: fix_syntax, fix_logic, noop, replace_line:<line_no>:<new_code>, "
    "insert_line:<line_no>:<new_code>, replace_range:<start_line>:<end_line>:<new_code>, "
    "append_line:<new_code>, delete_line:<line_no>, replace_text:<old_text>:<new_text>, "
    "rewrite_code:<new_code>."
)

VALID_ACTION_PATTERN = re.compile(
    r"^(fix_syntax|fix_logic|noop|replace_line:[^:\n]+:.+|insert_line:[^:\n]+:.+|replace_range:[^:\n]+:[^:\n]+:[\s\S]*|append_line:.+|delete_line:[^:\n]+|replace_text:[^:\n]+:.+|rewrite_code:[\s\S]+)$"
)


# ---------------------------------------------------------------------------
# Score clamping — scores must be strictly in (0, 1)
# ---------------------------------------------------------------------------
def _clamp_score(score: float) -> float:
    """Clamp score to strictly (0, 1) — never exactly 0.0 or 1.0."""
    return round(min(max(float(score), 0.01), 0.99), 4)


# ---------------------------------------------------------------------------
# Deterministic fallback policy
# ---------------------------------------------------------------------------
def choose_action(state: Dict[str, object]) -> str:
    """Deterministic fallback policy when LLM is unavailable."""
    code = str(state.get("code", ""))
    error = str(state.get("error", ""))

    if "SyntaxError" in error or 'print("Hello' in code or "if a > b\n" in code:
        return "fix_syntax"

    if (
        "a-b" in code
        or "a - b" in code
        or "b-a" in code
        or "b - a" in code
        or "total = a - b" in code
    ):
        return "fix_logic"

    return "noop"


# ---------------------------------------------------------------------------
# Action normalisation
# ---------------------------------------------------------------------------
def _normalize_action(raw_action: str) -> str:
    action = raw_action.strip().strip("`")
    if VALID_ACTION_PATTERN.match(action):
        return action

    for line in raw_action.splitlines():
        candidate = line.strip().strip("`")
        if VALID_ACTION_PATTERN.match(candidate):
            return candidate

    return "noop"


def _has_explicit_noop(raw_action: str) -> bool:
    action = raw_action.strip().strip("`")
    if action == "noop":
        return True

    for line in raw_action.splitlines():
        if line.strip().strip("`") == "noop":
            return True

    return False


# ---------------------------------------------------------------------------
# Logging helpers — strict stdout format
# ---------------------------------------------------------------------------
def _safe_field(value: object) -> str:
    return str(value).replace("\r", "\\r").replace("\n", "\\n")


def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    done_text = str(done).lower()
    error_text = "null" if not error else _safe_field(error)
    print(
        f"[STEP] step={step} action={_safe_field(action)} reward={reward:.2f} done={done_text} error={error_text}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float, rewards: list[float]) -> None:
    """Emit the [END] line including the mandatory score= field."""
    score = _clamp_score(score)
    rewards_text = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} score={score:.4f} rewards={rewards_text}",
        flush=True,
    )


def log_error(message: str) -> None:
    print(f"[ERROR] {message}", flush=True)


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------
def _build_endpoint_candidates(base_url: str) -> tuple[list[str], list[str]]:
    base = base_url.rstrip("/")

    reset_candidates: list[str] = []
    step_candidates: list[str] = []

    if base.endswith("/reset"):
        root = base[: -len("/reset")]
        reset_candidates.append(base)
        step_candidates.append(f"{root}/step")
    elif base.endswith("/step"):
        root = base[: -len("/step")]
        step_candidates.append(base)
        reset_candidates.append(f"{root}/reset")
    else:
        reset_candidates.extend([f"{base}/reset", f"{base}/api/reset"])
        step_candidates.extend([f"{base}/step", f"{base}/api/step"])

    return reset_candidates, step_candidates


def _post_with_fallback(
    urls: list[str],
    *,
    json_payload: Dict[str, object],
    headers: Dict[str, str],
    timeout: int,
) -> tuple[requests.Response, str]:
    last_error: Optional[Exception] = None

    for url in urls:
        try:
            response = requests.post(url, json=json_payload, headers=headers, timeout=timeout)
            if response.status_code == 404:
                last_error = requests.HTTPError(f"404 for url: {url}")
                continue

            response.raise_for_status()
            return response, url
        except Exception as exc:
            last_error = exc

    if last_error is not None:
        raise last_error

    raise RuntimeError("No API endpoint candidates were available for request")


# ---------------------------------------------------------------------------
# LLM policy
# ---------------------------------------------------------------------------
def choose_action_with_openai(client: OpenAI, state: Dict[str, object]) -> str:
    prompt = (
        f"Task: {state.get('task', '')}\n"
        f"Error: {state.get('error', '')}\n"
        f"Step count: {state.get('step_count', 0)}\n"
        f"History: {state.get('history', [])}\n"
        f"Code:\n{state.get('code', '')}\n\n"
        "Return exactly one valid action."
    )

    for _ in range(max(1, MAX_LLM_RETRIES)):
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            max_tokens=40,
        )

        content = completion.choices[0].message.content or ""
        action = _normalize_action(content)
        if action != "noop":
            return action

        if _has_explicit_noop(content):
            return action

    return "noop"


# ---------------------------------------------------------------------------
# Single-task runner
# ---------------------------------------------------------------------------
def run_single_task(
    task_name: str,
    reset_urls: list[str],
    step_urls: list[str],
    headers: Dict[str, str],
    client: Optional[OpenAI],
) -> None:
    """Run one task, emitting [START] / [STEP]* / [END] to stdout."""
    rewards: list[float] = []
    steps_taken = 0
    success = False
    score = 0.001  # default — strictly > 0

    log_start(task=task_name, env=BENCHMARK, model=MODEL_NAME)

    try:
        reset_resp, selected_reset_url = _post_with_fallback(
            reset_urls,
            json_payload={"task": task_name},
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )

        if selected_reset_url.endswith("/reset"):
            selected_step_url = f"{selected_reset_url[: -len('/reset')]}/step"
            local_step_urls = list(step_urls)
            if selected_step_url in local_step_urls:
                local_step_urls.remove(selected_step_url)
            local_step_urls.insert(0, selected_step_url)
        else:
            local_step_urls = list(step_urls)

        reset_payload = reset_resp.json()
        session_id = reset_payload["session_id"]
        state = reset_payload["state"]
        done = False
        score = _clamp_score(float(state.get("score", 0.001)))

        while not done and steps_taken < MAX_STEPS:
            if client is not None:
                try:
                    action = choose_action_with_openai(client, state)
                except Exception:
                    action = choose_action(state)
            else:
                action = choose_action(state)

            step_resp, _selected_step_url = _post_with_fallback(
                local_step_urls,
                json_payload={"session_id": session_id, "action": action},
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            )

            payload = step_resp.json()
            state = payload["state"]
            done = bool(payload["done"])
            reward = float(payload.get("reward", 0.0))
            score = _clamp_score(float(payload.get("score", score)))
            steps_taken += 1
            rewards.append(reward)

            error_text = state.get("error")
            log_step(
                step=steps_taken,
                action=action,
                reward=reward,
                done=done,
                error=str(error_text) if error_text else None,
            )

            time.sleep(0.1)

        success = bool(done and score >= 0.99)

    except Exception as exc:
        success = False
        log_error(f"inference_failed={exc.__class__.__name__}: {exc}")
    finally:
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)


# ---------------------------------------------------------------------------
# Main — iterate over ALL tasks
# ---------------------------------------------------------------------------
def main() -> None:
    headers = {"Content-Type": "application/json"}

    client = None
    if USE_LLM_POLICY and API_BASE_URL and API_KEY:
        client = OpenAI(api_key=API_KEY, base_url=API_BASE_URL)

    reset_urls, step_urls = _build_endpoint_candidates(ENV_API_BASE_URL)

    for task_name in ALL_TASKS:
        run_single_task(
            task_name=task_name,
            reset_urls=reset_urls,
            step_urls=step_urls,
            headers=headers,
            client=client,
        )


if __name__ == "__main__":
    main()
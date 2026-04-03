"""
Baseline inference script for CodeFixEnv.

Uses the OpenAI client for LLM calls and interacts with the CodeFixEnv
HTTP API (``/reset``, ``/step``) deployed on Hugging Face Spaces or locally.

Environment variables (mandatory):
    API_BASE_URL   – URL of the CodeFixEnv server (e.g. https://<space>.hf.space)
    MODEL_NAME     – Model identifier for the LLM
    HF_TOKEN       – Hugging Face / API key

Emits structured stdout logs in [START], [STEP], [END] format as required
by the hackathon evaluation harness.
"""

import asyncio
import os
import re
from typing import Any, Dict, List

import httpx
from openai import OpenAI

# ---------------------------------------------------------------------------
# Configuration from environment variables
# ---------------------------------------------------------------------------

API_BASE_URL: str = os.getenv("API_BASE_URL", "http://localhost:7860").rstrip("/")
MODEL_NAME: str = os.getenv("MODEL_NAME", "demo-rule-agent")
HF_TOKEN: str = os.getenv("HF_TOKEN", "")
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")

TASKS: List[str] = [
    t.strip()
    for t in os.getenv("TASKS", "easy,medium,hard").split(",")
    if t.strip()
]
MAX_STEPS: int = int(os.getenv("MAX_STEPS", "8"))
TEMPERATURE: float = float(os.getenv("TEMPERATURE", "0"))
MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "40"))
MAX_TOTAL_REWARD: float = float(os.getenv("MAX_TOTAL_REWARD", "1.0"))
SUCCESS_SCORE_THRESHOLD: float = float(os.getenv("SUCCESS_SCORE_THRESHOLD", "1.0"))

BENCHMARK: str = "CodeFixEnv"

# ---------------------------------------------------------------------------
# System prompt for the LLM policy
# ---------------------------------------------------------------------------

SYSTEM_PROMPT: str = (
    "You are a deterministic code-fixing policy. Return exactly one action "
    "and nothing else.  Allowed actions: fix_syntax, fix_logic, noop, "
    "replace_line:<line_no>:<new_code>, append_line:<new_code>, "
    "delete_line:<line_no>, replace_text:<old_text>:<new_text>."
)

VALID_ACTION_RE = re.compile(
    r"^(fix_syntax|fix_logic|noop"
    r"|replace_line:[^:\n]+:.+"
    r"|append_line:.+"
    r"|delete_line:[^:\n]+"
    r"|replace_text:[^:\n]+:.+)$"
)

# ---------------------------------------------------------------------------
# Deterministic fallback policy (no LLM needed)
# ---------------------------------------------------------------------------


def choose_action_fallback(state: Dict[str, Any]) -> str:
    """Rule-based fallback when LLM is unavailable."""
    code = str(state.get("code", ""))
    error = str(state.get("error", ""))

    if "SyntaxError" in error or 'print("Hello' in code or "if a > b\n" in code:
        return "fix_syntax"

    if any(tok in code for tok in ("a-b", "a - b", "b-a", "b - a")):
        return "fix_logic"

    return "noop"


def _normalise_llm_output(raw: str) -> str:
    """Extract a valid action string from LLM output."""
    cleaned = raw.strip().strip("`")
    if VALID_ACTION_RE.match(cleaned):
        return cleaned
    for line in raw.splitlines():
        candidate = line.strip().strip("`")
        if VALID_ACTION_RE.match(candidate):
            return candidate
    return "noop"


# ---------------------------------------------------------------------------
# LLM policy via OpenAI client
# ---------------------------------------------------------------------------


def get_model_message(
    client: OpenAI,
    step: int,
    state: Dict[str, Any],
    history: List[str],
) -> str:
    """Call the LLM and return a single action string."""
    user_prompt = (
        f"Task: {state.get('task', '')}\n"
        f"Error: {state.get('error', '')}\n"
        f"Step: {step}\n"
        f"History: {history}\n"
        f"Code:\n{state.get('code', '')}\n\n"
        "Return exactly one valid action."
    )
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            stream=False,
        )
        text = (completion.choices[0].message.content or "").strip()
        return _normalise_llm_output(text) if text else "noop"
    except Exception as exc:
        print(f"[DEBUG] Model request failed: {exc}", flush=True)
        return choose_action_fallback(state)


# ---------------------------------------------------------------------------
# Structured logging helpers
# ---------------------------------------------------------------------------


def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(
    step: int,
    action: str,
    reward: float,
    done: bool,
    error: str | None,
) -> None:
    safe_err = "None" if error in (None, "") else str(error).replace("\n", " ").strip()
    print(
        f"[STEP] step={step} action={action} reward={reward:.4f} "
        f"done={done} error={safe_err}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    print(
        f"[END] success={success} steps={steps} score={score:.4f} "
        f"rewards={rewards}",
        flush=True,
    )


# ---------------------------------------------------------------------------
# Environment interaction helpers (HTTP)
# ---------------------------------------------------------------------------


async def env_reset(
    http: httpx.AsyncClient,
    task: str,
) -> Dict[str, Any]:
    """POST /reset and return parsed JSON."""
    resp = await http.post(f"{API_BASE_URL}/reset", json={"task": task}, timeout=30)
    resp.raise_for_status()
    return resp.json()


async def env_step(
    http: httpx.AsyncClient,
    action_str: str,
) -> Dict[str, Any]:
    """POST /step and return parsed JSON."""
    resp = await http.post(
        f"{API_BASE_URL}/step",
        json={"action": {"action": action_str}},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Main inference loop
# ---------------------------------------------------------------------------


async def run_task(
    task_name: str,
    client: OpenAI | None,
    http: httpx.AsyncClient,
) -> tuple[float, int, bool]:
    """Run one full episode for *task_name* and return (score, steps, success)."""

    history: List[str] = []
    rewards: List[float] = []
    steps_taken: int = 0
    score: float = 0.0
    success: bool = False

    log_start(task=task_name, env=BENCHMARK, model=MODEL_NAME)

    try:
        reset_data = await env_reset(http, task_name)
        obs = reset_data.get("observation", {})
        done = reset_data.get("done", False)

        for step in range(1, MAX_STEPS + 1):
            if done:
                break

            # Choose action
            if client is not None:
                action_str = get_model_message(client, step, obs, history)
            else:
                action_str = choose_action_fallback(obs)

            # Execute
            step_data = await env_step(http, action_str)
            obs = step_data.get("observation", {})
            reward = float(step_data.get("reward", 0.0) or 0.0)
            done = bool(step_data.get("done", False))

            rewards.append(reward)
            steps_taken = step
            score = float(obs.get("score", 0.0))

            log_step(
                step=step,
                action=action_str,
                reward=reward,
                done=done,
                error=obs.get("error") or None,
            )

            history.append(f"Step {step}: {action_str!r} -> reward {reward:+.2f}")

            if done:
                break

        # Final score normalisation
        if MAX_TOTAL_REWARD > 0:
            score = min(max(score, 0.0), 1.0)
        success = score >= SUCCESS_SCORE_THRESHOLD

    finally:
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)

    return score, steps_taken, success


async def main() -> None:
    api_key = OPENAI_API_KEY or HF_TOKEN

    # Build OpenAI client for LLM policy (if key available)
    client: OpenAI | None = None
    if api_key:
        client = OpenAI(api_key=api_key, base_url=LLM_BASE_URL)

    scores: List[float] = []

    async with httpx.AsyncClient() as http:
        for task_name in TASKS:
            task_score, _, _ = await run_task(task_name, client, http)
            scores.append(task_score)


if __name__ == "__main__":
    asyncio.run(main())
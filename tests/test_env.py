"""Tests for the CodeFixEnvironment and the OpenEnv HTTP API layer."""

from fastapi.testclient import TestClient

from app import app
from env.environment import CodeFixEnvironment
from models import CodeFixAction


# ---------- direct environment tests ----------


def test_environment_reset_returns_observation():
    env = CodeFixEnvironment()
    obs = env.reset(task="easy")

    assert obs.task == "easy"
    assert obs.code != ""
    assert obs.step_count == 0
    assert obs.history == []
    assert obs.done is False


def test_environment_step_records_history_and_score():
    env = CodeFixEnvironment()
    env.reset(task="medium")
    obs = env.step(CodeFixAction(action="fix_logic"))

    assert obs.step_count == 1
    assert obs.history[-1] == "fix_logic"
    assert isinstance(obs.reward, (int, float))
    assert isinstance(obs.done, bool)


def test_environment_state_property():
    env = CodeFixEnvironment()
    env.reset(task="easy")
    st = env.state
    assert st.task_name == "easy"
    assert st.step_count == 0


# ---------- HTTP API tests ----------


def test_health_endpoint():
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"


def test_reset_and_step_flow():
    client = TestClient(app)

    # Reset
    reset_resp = client.post("/reset", json={"task": "easy"})
    assert reset_resp.status_code == 200
    reset_data = reset_resp.json()
    assert "observation" in reset_data
    assert reset_data["done"] is False

    # Step
    step_resp = client.post(
        "/step",
        json={"action": {"action": "fix_syntax"}},
    )
    assert step_resp.status_code == 200
    step_data = step_resp.json()
    assert "observation" in step_data
    assert "reward" in step_data
    assert "done" in step_data


def test_reset_default_task():
    """POST /reset with empty body should default (no crash)."""
    client = TestClient(app)
    resp = client.post("/reset", json={})
    assert resp.status_code == 200


def test_schema_endpoint():
    client = TestClient(app)
    resp = client.get("/schema")
    assert resp.status_code == 200
    data = resp.json()
    assert "action" in data
    assert "observation" in data


# ---------- task-specific integration tests ----------


def test_easy_task_solves_in_one_step():
    env = CodeFixEnvironment()
    env.reset(task="easy")
    obs = env.step(CodeFixAction(action="fix_syntax"))
    assert obs.done is True
    assert obs.score >= 1.0


def test_hard_task_needs_two_steps():
    env = CodeFixEnvironment()
    env.reset(task="hard")

    obs1 = env.step(CodeFixAction(action="fix_syntax"))
    assert obs1.done is False
    assert 0.3 <= obs1.score < 1.0

    obs2 = env.step(CodeFixAction(action="fix_logic"))
    assert obs2.done is True
    assert obs2.score >= 1.0


def test_nightmare_task_converges():
    env = CodeFixEnvironment()
    env.reset(task="nightmare")

    obs1 = env.step(CodeFixAction(action="fix_syntax"))
    assert obs1.done is False

    obs2 = env.step(CodeFixAction(action="fix_logic"))
    assert obs2.done is True
    assert obs2.score >= 1.0


def test_medium_task_fix_logic():
    env = CodeFixEnvironment()
    env.reset(task="medium")
    obs = env.step(CodeFixAction(action="fix_logic"))
    assert obs.score >= 1.0
    assert obs.done is True


def test_invalid_action_returns_penalty():
    env = CodeFixEnvironment()
    env.reset(task="easy")
    obs = env.step(CodeFixAction(action="unknown_action"))
    assert obs.reward is not None
    assert float(obs.reward) < 0

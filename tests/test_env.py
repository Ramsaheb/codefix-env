from fastapi.testclient import TestClient

from app import app
from env.environment import CodeFixEnv


def test_environment_reset_contains_required_fields():
	demo_env = CodeFixEnv()
	state = demo_env.reset("easy")

	assert state["task"] == "easy"
	assert "code" in state
	assert "error" in state
	assert state["step_count"] == 0
	assert state["history"] == []


def test_environment_step_records_history_and_score():
	demo_env = CodeFixEnv()
	demo_env.reset("medium")
	obs, reward, done, info = demo_env.step("fix_logic")

	assert obs["step_count"] == 1
	assert obs["history"][-1] == "fix_logic"
	assert isinstance(reward, float)
	assert "score" in info
	assert isinstance(done, bool)


def test_api_reset_and_step_flow():
	client = TestClient(app)

	reset_response = client.post("/reset", json={"task": "easy"})
	assert reset_response.status_code == 200

	step_response = client.post("/step", json={"action": "fix_syntax"})
	assert step_response.status_code == 200

	payload = step_response.json()
	assert "state" in payload
	assert "reward" in payload
	assert "done" in payload

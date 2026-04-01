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


def test_health_and_ready_endpoints():
	client = TestClient(app)

	health_response = client.get("/health")
	assert health_response.status_code == 200
	assert health_response.json()["status"] == "ok"

	ready_response = client.get("/ready")
	assert ready_response.status_code == 200
	payload = ready_response.json()
	assert payload["status"] == "ready"
	assert "tasks" in payload
	assert {"easy", "medium", "hard", "expert", "nightmare"}.issubset(set(payload["tasks"]))
	assert "active_sessions" in payload


def test_api_reset_and_step_flow():
	client = TestClient(app)

	reset_response = client.post("/reset", json={"task": "easy"})
	assert reset_response.status_code == 200
	reset_payload = reset_response.json()
	assert "session_id" in reset_payload

	step_response = client.post(
		"/step",
		json={"session_id": reset_payload["session_id"], "action": "fix_syntax"},
	)
	assert step_response.status_code == 200

	payload = step_response.json()
	assert "session_id" in payload
	assert "state" in payload
	assert "reward" in payload
	assert "done" in payload


def test_api_rejects_unknown_task():
	client = TestClient(app)

	response = client.post("/reset", json={"task": "unknown"})
	assert response.status_code == 400


def test_api_rejects_unknown_session():
	client = TestClient(app)

	response = client.post("/step", json={"session_id": "missing-session", "action": "noop"})
	assert response.status_code == 404


def test_session_delete_flow():
	client = TestClient(app)

	reset_response = client.post("/reset", json={"task": "easy"})
	assert reset_response.status_code == 200
	session_id = reset_response.json()["session_id"]

	delete_response = client.delete(f"/session/{session_id}")
	assert delete_response.status_code == 204

	step_response = client.post("/step", json={"session_id": session_id, "action": "noop"})
	assert step_response.status_code == 404


def test_session_isolation_between_clients():
	client = TestClient(app)

	reset_easy = client.post("/reset", json={"task": "easy"}).json()
	reset_medium = client.post("/reset", json={"task": "medium"}).json()

	sid_easy = reset_easy["session_id"]
	sid_medium = reset_medium["session_id"]
	assert sid_easy != sid_medium

	step_easy = client.post("/step", json={"session_id": sid_easy, "action": "fix_syntax"})
	step_medium = client.post("/step", json={"session_id": sid_medium, "action": "fix_logic"})

	assert step_easy.status_code == 200
	assert step_medium.status_code == 200

	easy_task = step_easy.json()["state"]["task"]
	medium_task = step_medium.json()["state"]["task"]
	assert easy_task == "easy"
	assert medium_task == "medium"


def test_hard_task_reaches_done_with_expected_action_sequence():
	client = TestClient(app)
	reset_payload = client.post("/reset", json={"task": "hard"}).json()
	sid = reset_payload["session_id"]

	first = client.post("/step", json={"session_id": sid, "action": "fix_syntax"})
	assert first.status_code == 200
	first_payload = first.json()
	assert first_payload["done"] is False
	assert 0.3 <= first_payload["score"] < 1.0

	second = client.post("/step", json={"session_id": sid, "action": "fix_logic"})
	assert second.status_code == 200
	second_payload = second.json()
	assert second_payload["done"] is True
	assert second_payload["score"] == 1.0

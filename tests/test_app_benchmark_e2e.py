from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import benchmark
from app import app


@pytest.mark.parametrize(
    "task,actions",
    [
        ("easy", ["fix_syntax"]),
        ("medium", ["fix_logic"]),
        ("hard", ["fix_syntax", "fix_logic"]),
        ("expert", ["fix_logic"]),
        ("nightmare", ["fix_syntax", "fix_logic"]),
    ],
)
def test_end_to_end_task_flows_reach_done(task, actions):
    client = TestClient(app)

    reset_payload = client.post("/reset", json={"task": task}).json()
    session_id = reset_payload["session_id"]

    last_payload = None
    for action in actions:
        response = client.post(
            "/step",
            json={"session_id": session_id, "action": action},
        )
        assert response.status_code == 200
        last_payload = response.json()

    assert last_payload is not None
    assert last_payload["done"] is True
    assert last_payload["score"] == 1.0


def test_api_reset_without_payload_uses_default_task():
    client = TestClient(app)

    response = client.post("/reset")

    assert response.status_code == 200
    assert response.json()["state"]["task"] == "easy"


def test_api_step_runtime_error_is_mapped_to_400(monkeypatch):
    client = TestClient(app)

    monkeypatch.setattr(
        "app.session_manager.step",
        lambda _sid, _action: (_ for _ in ()).throw(RuntimeError("bad action")),
    )

    response = client.post("/step", json={"session_id": "sid", "action": "noop"})

    assert response.status_code == 400
    assert response.json()["detail"] == "bad action"


def test_api_delete_unknown_session_returns_404():
    client = TestClient(app)

    response = client.delete("/session/missing-session")

    assert response.status_code == 404


def test_api_returns_json_on_unexpected_exception(monkeypatch):
    client = TestClient(app, raise_server_exceptions=False)

    monkeypatch.setattr(
        "app.session_manager.reset",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("unexpected failure")),
    )

    response = client.post("/reset", json={"task": "easy"})

    assert response.status_code == 500
    assert response.json()["detail"] == "Internal server error"


def test_choose_benchmark_action_paths():
    assert benchmark.choose_benchmark_action({"code": "if a > b\n", "error": ""}) == "fix_syntax"
    assert benchmark.choose_benchmark_action({"code": "return a-b", "error": ""}) == "fix_logic"
    assert benchmark.choose_benchmark_action({"code": "print('ok')", "error": ""}) == "noop"


def test_run_task_benchmark_stops_on_stagnation(monkeypatch):
    class FakeEnv:
        def __init__(self):
            self.state = SimpleNamespace(max_steps=8)

        def reset(self, _task_name):
            return {
                "task": "easy",
                "code": "print(1)",
                "error": "",
                "step_count": 0,
            }

        def step(self, _action):
            return (
                {
                    "task": "easy",
                    "code": "print(1)",
                    "error": "",
                    "step_count": 1,
                    "score": 0.0,
                },
                -0.1,
                False,
                {},
            )

    monkeypatch.setattr(benchmark, "CodeFixEnv", FakeEnv)

    result = benchmark.run_task_benchmark("easy")

    assert result.steps == 2
    assert result.solved is False


@pytest.mark.parametrize(
    "readiness,status_text",
    [
        (90.0, "Strong submission readiness"),
        (70.0, "Good baseline, improve harder tasks"),
        (50.0, "Needs more work before submission"),
    ],
)
def test_print_report_status_messages(capsys, readiness, status_text):
    result = benchmark.BenchmarkResult(
        task="easy",
        solved=True,
        score=1.0,
        steps=1,
        max_steps=4,
        error="",
    )

    benchmark.print_report([result], readiness)
    output = capsys.readouterr().out

    assert "CodeFixEnv Benchmark Results" in output
    assert status_text in output


def test_compute_submission_readiness_empty_list():
    assert benchmark.compute_submission_readiness([]) == 0.0

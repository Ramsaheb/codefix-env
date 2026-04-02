from datetime import datetime, timedelta, timezone

import pytest

import predeploy_check


class FakeResponse:
    def __init__(self, status_code: int, payload: dict | None = None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self) -> dict:
        return self._payload


def test_run_command_raises_when_required_step_fails(monkeypatch):
    class FakeProcess:
        returncode = 3

    monkeypatch.setattr(predeploy_check.subprocess, "run", lambda *args, **kwargs: FakeProcess())

    with pytest.raises(predeploy_check.StepFailed):
        predeploy_check.run_command("failing step", ["python", "-V"], required=True)


def test_run_command_returns_exit_code_when_not_required(monkeypatch):
    class FakeProcess:
        returncode = 7

    monkeypatch.setattr(predeploy_check.subprocess, "run", lambda *args, **kwargs: FakeProcess())

    code = predeploy_check.run_command("optional step", ["python", "-V"], required=False)

    assert code == 7


def test_wait_for_health_retries_until_success(monkeypatch):
    calls = {"count": 0}

    def fake_get(url, timeout):
        calls["count"] += 1
        if calls["count"] == 1:
            raise predeploy_check.requests.RequestException("temporary outage")
        return FakeResponse(200)

    monkeypatch.setattr(predeploy_check.requests, "get", fake_get)
    monkeypatch.setattr(predeploy_check.time, "sleep", lambda _seconds: None)

    predeploy_check.wait_for_health(timeout_seconds=5)

    assert calls["count"] == 2


def test_wait_for_health_times_out(monkeypatch):
    times = iter([0.0, 1.0, 3.0])

    monkeypatch.setattr(predeploy_check.time, "time", lambda: next(times))
    monkeypatch.setattr(predeploy_check.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(
        predeploy_check.requests,
        "get",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(predeploy_check.requests.RequestException("down")),
    )

    with pytest.raises(predeploy_check.StepFailed, match="timed out"):
        predeploy_check.wait_for_health(timeout_seconds=1)


def test_run_api_smoke_checks_success(monkeypatch):
    nightmare_steps = {"count": 0}

    def fake_get(url, timeout):
        assert url.endswith("/ready")
        return FakeResponse(
            200,
            {
                "tasks": ["easy", "medium", "hard", "expert", "nightmare"],
            },
        )

    def fake_post(url, json, timeout):
        if url.endswith("/reset") and json["task"] == "easy":
            return FakeResponse(200, {"session_id": "easy-sid"})

        if url.endswith("/step") and json["session_id"] == "easy-sid":
            return FakeResponse(200, {"done": True})

        if url.endswith("/reset") and json["task"] == "nightmare":
            return FakeResponse(200, {"session_id": "night-sid"})

        if url.endswith("/step") and json["session_id"] == "night-sid":
            nightmare_steps["count"] += 1
            return FakeResponse(200, {"done": nightmare_steps["count"] >= 2})

        raise AssertionError(f"Unexpected call: {url} {json}")

    monkeypatch.setattr(predeploy_check.requests, "get", fake_get)
    monkeypatch.setattr(predeploy_check.requests, "post", fake_post)

    predeploy_check.run_api_smoke_checks()

    assert nightmare_steps["count"] == 2


def test_run_api_smoke_checks_rejects_missing_tasks(monkeypatch):
    monkeypatch.setattr(
        predeploy_check.requests,
        "get",
        lambda *_args, **_kwargs: FakeResponse(200, {"tasks": ["easy"]}),
    )

    with pytest.raises(predeploy_check.StepFailed, match="missing tasks"):
        predeploy_check.run_api_smoke_checks()


def test_run_inference_smoke_sets_expected_environment(monkeypatch):
    captured = {}

    def fake_run_command(title, command, env=None, required=True):
        captured["title"] = title
        captured["command"] = command
        captured["env"] = env
        captured["required"] = required
        return 0

    monkeypatch.setattr(predeploy_check, "run_command", fake_run_command)

    predeploy_check.run_inference_smoke()

    assert captured["title"] == "inference.py smoke"
    assert captured["command"][0] == predeploy_check.PYTHON
    assert captured["env"]["USE_LLM_POLICY"] == "false"
    assert captured["env"]["HF_TOKEN"] == ""


def test_main_returns_1_when_docker_missing(monkeypatch):
    monkeypatch.setattr(predeploy_check.shutil, "which", lambda _name: None)

    assert predeploy_check.main() == 1


def test_main_success_path_runs_cleanup(monkeypatch):
    monkeypatch.setattr(predeploy_check.shutil, "which", lambda _name: "docker")

    titles = []

    def fake_run_command(title, command, env=None, required=True):
        titles.append(title)
        return 0

    monkeypatch.setattr(predeploy_check, "run_command", fake_run_command)
    monkeypatch.setattr(predeploy_check, "wait_for_health", lambda: None)
    monkeypatch.setattr(predeploy_check, "run_api_smoke_checks", lambda: None)
    monkeypatch.setattr(predeploy_check, "run_inference_smoke", lambda: None)

    result = predeploy_check.main()

    assert result == 0
    assert "Start container" in titles
    assert "Stop container" in titles


def test_main_failure_path_stops_container(monkeypatch):
    monkeypatch.setattr(predeploy_check.shutil, "which", lambda _name: "docker")

    titles = []

    def fake_run_command(title, command, env=None, required=True):
        titles.append(title)
        return 0

    monkeypatch.setattr(predeploy_check, "run_command", fake_run_command)
    monkeypatch.setattr(predeploy_check, "wait_for_health", lambda: None)
    monkeypatch.setattr(
        predeploy_check,
        "run_api_smoke_checks",
        lambda: (_ for _ in ()).throw(predeploy_check.StepFailed("boom")),
    )
    monkeypatch.setattr(predeploy_check, "run_inference_smoke", lambda: None)

    result = predeploy_check.main()

    assert result == 1
    assert "Start container" in titles
    assert "Stop container" in titles

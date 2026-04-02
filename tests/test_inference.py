from types import SimpleNamespace

import pytest

import inference


class FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code

    def json(self) -> dict:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class DummyCompletions:
    def __init__(self, outputs: list[str]):
        self.outputs = list(outputs)
        self.calls = 0

    def create(self, **_kwargs):
        index = min(self.calls, len(self.outputs) - 1)
        content = self.outputs[index]
        self.calls += 1
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
        )


class DummyClient:
    def __init__(self, outputs: list[str]):
        completions = DummyCompletions(outputs)
        self.completions = completions
        self.chat = SimpleNamespace(completions=completions)


def test_choose_action_heuristics_cover_syntax_logic_and_noop():
    assert inference.choose_action({"code": 'print("Hello', "error": ""}) == "fix_syntax"
    assert inference.choose_action({"code": "def add(a, b):\n    return a-b", "error": ""}) == "fix_logic"
    assert inference.choose_action({"code": "print('ok')", "error": ""}) == "noop"


def test_normalize_action_handles_multiline_and_invalid_values():
    assert inference._normalize_action("fix_logic") == "fix_logic"
    assert (
        inference._normalize_action("Some text\nappend_line:return a+b\nextra")
        == "append_line:return a+b"
    )
    assert inference._normalize_action("not-an-action") == "noop"


def test_has_explicit_noop_only_for_standalone_noop():
    assert inference._has_explicit_noop("noop")
    assert inference._has_explicit_noop("```\nnoop\n```")
    assert not inference._has_explicit_noop("this mentions noop in text")


def test_choose_action_with_openai_accepts_normalized_reply(monkeypatch):
    monkeypatch.setattr(inference, "MAX_LLM_RETRIES", 2)
    client = DummyClient(["```\nreplace_line:2:return a+b\n```"])

    action = inference.choose_action_with_openai(client, {"task": "hard", "code": "x"})

    assert action == "replace_line:2:return a+b"
    assert client.completions.calls == 1


def test_choose_action_with_openai_retries_then_returns_noop(monkeypatch):
    monkeypatch.setattr(inference, "MAX_LLM_RETRIES", 2)
    client = DummyClient(["invalid output", "still invalid"])

    action = inference.choose_action_with_openai(client, {"task": "easy", "code": "x"})

    assert action == "noop"
    assert client.completions.calls == 2


def test_choose_action_with_openai_accepts_explicit_noop(monkeypatch):
    monkeypatch.setattr(inference, "MAX_LLM_RETRIES", 3)
    client = DummyClient(["analysis text\nnoop\nmore text"])

    action = inference.choose_action_with_openai(client, {"task": "easy", "code": "x"})

    assert action == "noop"
    assert client.completions.calls == 1


def test_main_runs_fallback_policy_end_to_end(monkeypatch):
    monkeypatch.setattr(inference, "API_BASE_URL", "http://fake-api")
    monkeypatch.setattr(inference, "REQUEST_TIMEOUT", 3)
    monkeypatch.setattr(inference, "MAX_STEPS", 5)
    monkeypatch.setattr(inference, "USE_LLM_POLICY", False)
    monkeypatch.setattr(inference, "HF_TOKEN", "")
    monkeypatch.setattr(inference.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(inference, "choose_action", lambda _state: "fix_syntax")

    calls = []
    state_by_step = [
        {
            "task": "easy",
            "code": "print(\"Hello\")",
            "error": "",
            "step_count": 1,
            "history": ["fix_syntax"],
            "score": 0.6,
        },
        {
            "task": "easy",
            "code": "print(\"Hello\")",
            "error": "",
            "step_count": 2,
            "history": ["fix_syntax", "fix_syntax"],
            "score": 1.0,
        },
    ]

    def fake_post(url, json, headers, timeout):
        calls.append((url, json, headers, timeout))

        if url.endswith("/reset"):
            return FakeResponse(
                {
                    "session_id": "sid-1",
                    "state": {
                        "task": "easy",
                        "code": 'print("Hello',
                        "error": "SyntaxError",
                        "step_count": 0,
                        "history": [],
                        "score": 0.0,
                    },
                }
            )

        if url.endswith("/step"):
            index = len([entry for entry in calls if entry[0].endswith("/step")]) - 1
            done = index >= 1
            score = 1.0 if done else 0.6
            return FakeResponse(
                {
                    "state": state_by_step[index],
                    "done": done,
                    "reward": 0.4,
                    "score": score,
                }
            )

        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(inference.requests, "post", fake_post)

    inference.main()

    step_calls = [entry for entry in calls if entry[0].endswith("/step")]
    assert len(step_calls) == 2
    assert all(call[1]["action"] == "fix_syntax" for call in step_calls)


def test_main_falls_back_when_llm_policy_raises(monkeypatch):
    monkeypatch.setattr(inference, "API_BASE_URL", "http://fake-api")
    monkeypatch.setattr(inference, "REQUEST_TIMEOUT", 3)
    monkeypatch.setattr(inference, "MAX_STEPS", 2)
    monkeypatch.setattr(inference, "USE_LLM_POLICY", True)
    monkeypatch.setattr(inference, "HF_TOKEN", "token")
    monkeypatch.setattr(inference, "MODEL_NAME", "demo")
    monkeypatch.setattr(inference, "LLM_BASE_URL", "http://llm")
    monkeypatch.setattr(inference.time, "sleep", lambda _seconds: None)

    monkeypatch.setattr(inference, "OpenAI", lambda **_kwargs: object())
    monkeypatch.setattr(
        inference,
        "choose_action_with_openai",
        lambda _client, _state: (_ for _ in ()).throw(RuntimeError("llm unavailable")),
    )

    fallback_calls = {"count": 0}

    def choose_fallback(_state):
        fallback_calls["count"] += 1
        return "noop"

    monkeypatch.setattr(inference, "choose_action", choose_fallback)

    def fake_post(url, json, headers, timeout):
        if url.endswith("/reset"):
            assert headers.get("Authorization") == "Bearer token"
            return FakeResponse(
                {
                    "session_id": "sid-2",
                    "state": {
                        "task": "easy",
                        "code": "print(1)",
                        "error": "",
                        "step_count": 0,
                        "history": [],
                        "score": 0.0,
                    },
                }
            )

        if url.endswith("/step"):
            assert json["action"] == "noop"
            return FakeResponse(
                {
                    "state": {
                        "task": "easy",
                        "code": "print(1)",
                        "error": "",
                        "step_count": 1,
                        "history": ["noop"],
                        "score": 1.0,
                    },
                    "done": True,
                    "reward": 0.0,
                    "score": 1.0,
                }
            )

        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(inference.requests, "post", fake_post)

    inference.main()

    assert fallback_calls["count"] == 1

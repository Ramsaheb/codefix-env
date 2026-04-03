"""Tests for action parsing, code transformation, and reward computation."""

from env.actions import parse_action
from env.environment import CodeFixEnvironment
from env.logic import apply_action
from env.reward import compute_reward
from models import CodeFixAction


def test_parse_action_supports_append_delete_and_replace_text():
    action, payload = parse_action("append_line:return a + b")
    assert action == "append_line"
    assert payload["new_code"] == "return a + b"

    action, payload = parse_action("delete_line:2")
    assert action == "delete_line"
    assert payload["line_no"] == 2

    action, payload = parse_action("replace_text:a-b:a+b")
    assert action == "replace_text"
    assert payload["old_text"] == "a-b"
    assert payload["new_text"] == "a+b"


def test_parse_action_rejects_invalid_delete_line_value():
    try:
        parse_action("delete_line:abc")
    except ValueError:
        return
    assert False, "Expected ValueError for invalid delete_line input"


def test_apply_action_supports_new_text_operations():
    code = "x = 1\ny = x - 1\n"

    replaced = apply_action(code, "replace_text:x - 1:x + 1")
    assert "x + 1" in replaced

    appended = apply_action(code, "append_line:print(y)")
    assert appended.endswith("print(y)\n")

    deleted = apply_action(code, "delete_line:1")
    assert deleted.startswith("y = x - 1")


def test_compute_reward_adds_bonus_on_improvement():
    reward = compute_reward(
        previous_score=0.3,
        current_score=0.6,
        changed_lines=2,
        action_error="",
        grade_error="",
    )
    assert reward == 0.35


def test_compute_reward_penalizes_no_change_invalid_action():
    reward = compute_reward(
        previous_score=0.3,
        current_score=0.3,
        changed_lines=0,
        action_error="Unsupported action",
        grade_error="",
    )
    assert reward == -0.11


def test_environment_exposes_action_error_in_metadata():
    env = CodeFixEnvironment()
    env.reset(task="easy")
    obs = env.step(CodeFixAction(action="unknown_action"))
    assert obs.metadata.get("action_error")
    assert float(obs.reward) <= -0.1

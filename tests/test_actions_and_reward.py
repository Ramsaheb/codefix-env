from env.actions import parse_action
from env.environment import CodeFixEnv
from env.logic import apply_action
from env.reward import compute_reward


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


def test_parse_action_supports_advanced_multiline_edits():
    action, payload = parse_action("insert_line:2:return a + b")
    assert action == "insert_line"
    assert payload["line_no"] == 2
    assert payload["new_code"] == "return a + b"

    action, payload = parse_action("replace_range:2:3:return a + b\\nprint(a)")
    assert action == "replace_range"
    assert payload["start_line"] == 2
    assert payload["end_line"] == 3
    assert payload["new_code"] == "return a + b\nprint(a)"

    action, payload = parse_action("rewrite_code:def add(a, b):\\n    return a + b")
    assert action == "rewrite_code"
    assert "return a + b" in payload["new_code"]


def test_apply_action_supports_insert_replace_range_and_rewrite_code():
    code = "def add(a, b):\n    total = a - b\n    return total\n"

    inserted = apply_action(code, "insert_line:2:# robust fix below")
    assert inserted.splitlines()[1] == "# robust fix below"

    replaced = apply_action(
        code,
        "replace_range:2:3:    total = a + b\\n    return total",
    )
    assert "total = a + b" in replaced
    assert "return total" in replaced

    rewritten = apply_action(
        code,
        "rewrite_code:def add(a, b):\\n    return a + b",
    )
    assert rewritten == "def add(a, b):\n    return a + b"


def test_fix_logic_handles_additive_intent_functions_with_complex_body():
    code = (
        "def synthesize(a, b, c):\n"
        "    result = a - b\n"
        "    if result > 0:\n"
        "        return result - c\n"
        "    return b - a\n"
    )

    updated = apply_action(code, "fix_logic")

    assert "result = a + b" in updated
    assert "return result + c" in updated
    assert "return b + a" in updated


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


def test_environment_exposes_action_error_in_step_info():
    demo_env = CodeFixEnv()
    demo_env.reset("easy")

    _obs, reward, _done, info = demo_env.step("unknown_action")

    assert info["action_error"]
    assert reward <= -0.1

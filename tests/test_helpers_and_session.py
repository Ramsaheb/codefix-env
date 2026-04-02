import logging
from datetime import datetime as real_datetime, timedelta, timezone

import pytest

from env.actions import parse_action
from env.environment import CodeFixEnv
from env.logic import apply_action
from env.reward import compute_reward
from env import session_manager
from settings import load_settings
from utils.diff_utils import diff_summary, is_improved
from utils.logger import LOGGER_NAME, configure_logging


def test_parse_action_validation_paths():
    action, payload = parse_action("NoOp")
    assert action == "noop"
    assert payload == {}

    with pytest.raises(ValueError, match="replace_line format"):
        parse_action("replace_line:3")

    with pytest.raises(ValueError, match="must be >= 1"):
        parse_action("replace_line:0:return 1")

    with pytest.raises(ValueError, match="old_text must be non-empty"):
        parse_action("replace_text::x")

    with pytest.raises(ValueError, match="Unsupported action"):
        parse_action("do_magic")


def test_apply_action_fixes_and_out_of_range_operations():
    code = "if a > b\n    print(a-b\n"

    fixed_syntax = apply_action(code, "fix_syntax")
    assert "if a > b:" in fixed_syntax
    assert "print(a-b)" in fixed_syntax

    fixed_logic = apply_action("def add(a,b):\n    return b-a", "fix_logic")
    assert "return" in fixed_logic
    assert "-" not in fixed_logic
    assert "+" in fixed_logic

    original = "line1\nline2\n"
    assert apply_action(original, "replace_line:10:new") == original
    assert apply_action(original, "delete_line:10") == original

    appended = apply_action("line1", "append_line:line2")
    assert appended == "line1\nline2\n"


def test_compute_reward_negative_delta_with_grade_error():
    reward = compute_reward(
        previous_score=0.8,
        current_score=0.5,
        changed_lines=3,
        action_error="",
        grade_error="failed testcase",
    )

    assert reward == -0.17


def test_environment_requires_reset_before_step_and_observation():
    env = CodeFixEnv()

    with pytest.raises(RuntimeError, match="Call /reset before /step"):
        env.step("noop")

    with pytest.raises(RuntimeError, match="not initialized"):
        env._get_obs()


def test_session_manager_prunes_oldest_and_updates_last_access(monkeypatch):
    class FakeDateTime:
        current = real_datetime(2026, 1, 1, tzinfo=timezone.utc)

        @classmethod
        def now(cls, _tz=None):
            return cls.current

    monkeypatch.setattr(session_manager, "datetime", FakeDateTime)

    manager = session_manager.SessionManager(max_sessions=2, session_ttl_seconds=30)

    t0 = FakeDateTime.current
    FakeDateTime.current = t0
    manager.reset("easy", session_id="s1")

    FakeDateTime.current = t0 + timedelta(seconds=1)
    manager.reset("easy", session_id="s2")

    FakeDateTime.current = t0 + timedelta(seconds=2)
    manager.reset("easy", session_id="s3")

    assert set(manager._sessions.keys()) == {"s2", "s3"}

    FakeDateTime.current = t0 + timedelta(seconds=3)
    manager.step("s2", "noop")
    assert manager._sessions["s2"].last_accessed == FakeDateTime.current


def test_session_manager_cleans_stale_sessions(monkeypatch):
    class FakeDateTime:
        current = real_datetime(2026, 1, 1, tzinfo=timezone.utc)

        @classmethod
        def now(cls, _tz=None):
            return cls.current

    monkeypatch.setattr(session_manager, "datetime", FakeDateTime)

    manager = session_manager.SessionManager(max_sessions=5, session_ttl_seconds=5)
    sid, _ = manager.reset("easy", session_id="stale-sid")

    FakeDateTime.current = FakeDateTime.current + timedelta(seconds=10)
    stats = manager.stats()

    assert stats["active_sessions"] == 0
    assert not manager.delete(sid)

    with pytest.raises(session_manager.SessionNotFoundError):
        manager.step(sid, "noop")


def test_settings_diff_and_logger_utilities(monkeypatch):
    monkeypatch.setenv("APP_NAME", "CodeFixEnv-Test")
    monkeypatch.setenv("APP_VERSION", "2.0.0")
    monkeypatch.setenv("LOG_LEVEL", "debug")
    monkeypatch.setenv("DEFAULT_TASK", "   ")
    monkeypatch.setenv("MAX_SESSIONS", "not-an-int")
    monkeypatch.setenv("SESSION_TTL_SECONDS", "5")

    settings = load_settings()
    assert settings.app_name == "CodeFixEnv-Test"
    assert settings.app_version == "2.0.0"
    assert settings.log_level == "DEBUG"
    assert settings.default_task == "easy"
    assert settings.max_sessions == 1000
    assert settings.session_ttl_seconds == 60

    assert not is_improved("x = 1", "x = 1")
    assert is_improved("x = 1", "x = 2")

    unchanged = diff_summary("x = 1\n", "x = 1\n")
    changed = diff_summary("x = 1\n", "x = 2\n")
    assert unchanged == {"changed_lines": 0, "preview": ""}
    assert changed["changed_lines"] >= 2
    assert "--- before.py" in changed["preview"]

    logger = logging.getLogger(LOGGER_NAME)
    for handler in list(logger.handlers):
        logger.removeHandler(handler)

    configure_logging("INFO")
    configure_logging("DEBUG")

    assert len(logger.handlers) == 1
    assert logger.level == logging.DEBUG

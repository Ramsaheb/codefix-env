import pytest

from graders import grader
from utils import code_executor


def test_compile_code_rejects_oversized_source():
    oversized = "x" * (code_executor.MAX_SOURCE_CHARS + 1)

    ok, error = code_executor.compile_code(oversized)

    assert not ok
    assert "max length" in error


def test_execute_code_returns_runtime_error_payload():
    ok, namespace, error = code_executor.execute_code("raise ValueError('boom')")

    assert not ok
    assert namespace == {}
    assert "ValueError" in error


def test_execute_code_enforces_line_execution_limit():
    ok, namespace, error = code_executor.execute_code(
        "while True:\n    pass",
        max_executed_lines=20,
    )

    assert not ok
    assert namespace == {}
    assert "Execution limit exceeded" in error


def test_invoke_callable_enforces_line_execution_limit():
    def spin():
        while True:
            pass

    with pytest.raises(code_executor.ExecutionLimitExceeded):
        code_executor.invoke_callable(spin, max_executed_lines=20)


def test_grade_code_handles_syntax_error_and_runtime_error():
    syntax_score, syntax_error = grader.grade_code("easy", 'print("oops')
    runtime_score, runtime_error = grader.grade_code("easy", "raise RuntimeError('x')")

    assert syntax_score == 0.0
    assert "SyntaxError" in syntax_error
    assert runtime_score == 0.3
    assert "RuntimeError" in runtime_error


def test_grade_code_returns_full_score_when_no_testcases(monkeypatch):
    monkeypatch.setattr(grader, "get_testcases", lambda _task: [])
    monkeypatch.setitem(grader.TEST_CASES, "custom", [])

    score, error = grader.grade_code("custom", "x = 1")

    assert score == 1.0
    assert error == ""


def test_grade_code_rejects_unknown_task_name():
    score, error = grader.grade_code("not-a-real-task", "print('ok')")

    assert score == 0.0
    assert "Unknown task" in error


def test_run_testcase_reports_missing_function():
    ok, reason = grader._run_testcase(
        {"kind": "call", "function": "add", "args": [1, 2], "expected": 3},
        {},
        "",
    )

    assert not ok
    assert "not found" in reason


def test_run_testcase_call_and_call_approx_branches():
    namespace = {
        "add": lambda a, b: a + b,
        "ratio": lambda a, b: a / b,
    }

    call_ok, _ = grader._run_testcase(
        {"kind": "call", "function": "add", "args": [2, 3], "expected": 5},
        namespace,
        "",
    )
    approx_ok, _ = grader._run_testcase(
        {
            "kind": "call_approx",
            "function": "ratio",
            "args": [1, 3],
            "expected": 0.333,
            "tolerance": 0.01,
        },
        namespace,
        "",
    )
    approx_fail, reason = grader._run_testcase(
        {
            "kind": "call_approx",
            "function": "ratio",
            "args": [1, 3],
            "expected": 0.9,
            "tolerance": 0.01,
        },
        namespace,
        "",
    )

    assert call_ok
    assert approx_ok
    assert not approx_fail
    assert "approximately" in reason


def test_run_testcase_handles_execution_limit_and_unknown_kind(monkeypatch):
    monkeypatch.setattr(
        grader,
        "invoke_callable",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            grader.ExecutionLimitExceeded("line budget exceeded")
        ),
    )

    limit_ok, limit_reason = grader._run_testcase(
        {"kind": "call", "function": "add", "args": [1, 2], "expected": 3},
        {"add": lambda a, b: a + b},
        "",
    )

    unknown_ok, unknown_reason = grader._run_testcase(
        {"kind": "mystery"},
        {},
        "",
    )

    assert not limit_ok
    assert "exceeded execution limit" in limit_reason.lower()
    assert not unknown_ok
    assert "Unknown testcase kind" in unknown_reason


def test_run_testcase_reports_callable_exception(monkeypatch):
    monkeypatch.setattr(
        grader,
        "invoke_callable",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("bad call")),
    )

    ok, reason = grader._run_testcase(
        {"kind": "call", "function": "add", "args": [1, 2], "expected": 3},
        {"add": lambda a, b: a + b},
        "",
    )

    assert not ok
    assert "raised ValueError" in reason


def test_detect_hardcoded_solution_non_trigger_paths():
    short_cases = [{"kind": "call", "function": "add", "args": [1, 2], "expected": 3}]
    mixed_cases = [
        {"kind": "call", "function": "add", "args": [], "expected": 0},
        {"kind": "call", "function": "add", "args": [3, 4], "expected": 7},
    ]

    assert grader._detect_hardcoded_solution("def add(a,b):\n    return a+b", short_cases) == ""
    assert grader._detect_hardcoded_solution("def add(a,b):\n    return a+b", mixed_cases) == ""

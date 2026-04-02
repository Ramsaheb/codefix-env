import logging

import pytest

from env.state import CodeState
from tasks import task_loader
from utils import code_executor
from utils.logger import LOGGER_NAME, configure_logging


def test_task_loader_returns_valid_codestate_for_all_tasks():
    for task_name in task_loader.available_tasks():
        state = task_loader.load_task(task_name)

        assert isinstance(state, CodeState)
        assert state.task_name == task_name
        assert state.code.strip()
        assert state.error.strip()
        assert 1 <= state.max_steps <= 64


def test_task_loader_validates_factory_contract(monkeypatch):
    def bad_factory():
        return CodeState(
            task_name="wrong-name",
            code="print('x')",
            error="err",
            max_steps=4,
        )

    monkeypatch.setitem(task_loader.TASK_FACTORIES, "easy", bad_factory)

    with pytest.raises(ValueError, match="mismatched task_name"):
        task_loader.load_task("easy")


def test_compile_code_rejects_non_string_input():
    ok, error = code_executor.compile_code(123)  # type: ignore[arg-type]

    assert not ok
    assert "string" in error


def test_execute_code_rejects_invalid_execution_budget():
    ok, namespace, error = code_executor.execute_code("x = 1", max_executed_lines=0)

    assert not ok
    assert namespace == {}
    assert "must be >= 1" in error


def test_execute_code_supports_common_safe_builtins():
    ok, namespace, error = code_executor.execute_code(
        "values = list(map(lambda x: x * 2, [1, 2, 3]))\n"
        "result = sorted(values, reverse=True)\n"
        "flag = any(v > 5 for v in result)\n"
    )

    assert ok
    assert error == ""
    assert namespace["values"] == [2, 4, 6]
    assert namespace["result"] == [6, 4, 2]
    assert namespace["flag"] is True


def test_configure_logging_falls_back_on_invalid_level():
    logger = logging.getLogger(LOGGER_NAME)
    for handler in list(logger.handlers):
        logger.removeHandler(handler)

    configure_logging("invalid-level")

    assert logger.level == logging.INFO
    assert len(logger.handlers) == 1

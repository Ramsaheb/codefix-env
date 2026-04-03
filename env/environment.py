"""
CodeFixEnvironment – OpenEnv-compliant Environment subclass.

Extends ``Environment[CodeFixAction, CodeFixObservation, CodeFixState]``
so that ``create_app`` / ``create_fastapi_app`` can register the standard
``/reset``, ``/step``, ``/state``, ``/health``, and WebSocket ``/ws``
endpoints automatically.
"""

from __future__ import annotations

import uuid
from typing import Any, Optional

from openenv.core.env_server.interfaces import Environment

from env.logic import apply_action
from env.reward import build_reward
from graders.grader import grade_code
from models import CodeFixAction, CodeFixObservation, CodeFixState
from tasks.task_loader import load_task
from utils.diff_utils import diff_summary
from utils.logger import log


class CodeFixEnvironment(Environment[CodeFixAction, CodeFixObservation, CodeFixState]):
    """
    RL environment for iterative code-debugging tasks.

    An agent receives buggy Python code and must choose actions
    (fix_syntax, fix_logic, replace_line, etc.) to make the code pass
    a deterministic grader.  Rewards provide partial-progress signal
    so that agents can learn incrementally.
    """

    SUPPORTS_CONCURRENT_SESSIONS: bool = True

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._state: Optional[CodeFixState] = None

    # ------------------------------------------------------------------
    # OpenEnv interface
    # ------------------------------------------------------------------

    def reset(
        self,
        seed: Optional[int] = None,
        episode_id: Optional[str] = None,
        **kwargs: Any,
    ) -> CodeFixObservation:
        task_name: str = kwargs.get("task", "easy")
        task_data = load_task(task_name)

        initial_score, grade_error = grade_code(task_data.task_name, task_data.code)

        self._state = CodeFixState(
            episode_id=episode_id or str(uuid.uuid4()),
            step_count=0,
            task_name=task_data.task_name,
            code=task_data.code,
            error=grade_error,
            max_steps=task_data.max_steps,
            target_hint=task_data.target_hint,
            last_score=initial_score,
            history=[],
        )

        log(f"reset task={task_name} episode={self._state.episode_id}")

        return CodeFixObservation(
            task=self._state.task_name,
            code=self._state.code,
            error=self._state.error,
            step_count=0,
            history=[],
            score=initial_score,
            done=False,
            reward=0.0,
        )

    def step(
        self,
        action: CodeFixAction,
        timeout_s: Optional[float] = None,
        **kwargs: Any,
    ) -> CodeFixObservation:
        if self._state is None:
            self.reset(task="easy")

        raw_action = action.action
        old_code = self._state.code
        action_error = ""

        try:
            new_code = apply_action(old_code, raw_action)
        except ValueError as exc:
            new_code = old_code
            action_error = str(exc)

        change = diff_summary(old_code, new_code)
        new_score, grade_error = grade_code(self._state.task_name, new_code)
        reward_details = build_reward(
            previous_score=self._state.last_score,
            current_score=new_score,
            changed_lines=int(change["changed_lines"]),
            action_error=action_error,
            grade_error=grade_error,
        )
        reward = reward_details.value

        self._state.code = new_code
        self._state.step_count += 1
        self._state.history.append(raw_action)
        self._state.last_score = new_score
        self._state.error = action_error or grade_error

        done = new_score >= 1.0 or self._state.step_count >= self._state.max_steps

        log(
            f"step task={self._state.task_name} "
            f"step={self._state.step_count} score={new_score} reward={reward}"
        )

        return CodeFixObservation(
            task=self._state.task_name,
            code=self._state.code,
            error=self._state.error,
            step_count=self._state.step_count,
            history=list(self._state.history),
            score=new_score,
            done=done,
            reward=reward,
            metadata={
                "changed_lines": change["changed_lines"],
                "action_error": action_error,
                "grade_error": grade_error,
                "reward": reward_details.model_dump(),
            },
        )

    @property
    def state(self) -> CodeFixState:
        if self._state is None:
            self.reset(task="easy")
        assert self._state is not None
        return self._state
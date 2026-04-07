from typing import Optional, Tuple

from env.logic import apply_action
from env.reward import compute_reward
from env.state import CodeState, PUBLIC_SCORE_EPSILON
from graders.grader import grade_code
from tasks.task_loader import load_task
from utils.diff_utils import diff_summary
from utils.logger import log


class CodeFixEnv:
    def __init__(self):
        self.state: Optional[CodeState] = None

    def reset(self, task: str = "easy") -> dict:
        self.state = load_task(task)
        initial_score, grade_error = grade_code(self.state.task_name, self.state.code)

        self.state.last_score = initial_score
        if grade_error:
            self.state.error = grade_error

        return self._get_obs()

    def step(self, action: str) -> Tuple[dict, float, bool, dict]:
        if self.state is None:
            raise RuntimeError("Call /reset before /step.")

        old_code = self.state.code
        action_error = ""

        try:
            new_code = apply_action(old_code, action)
        except ValueError as exc:
            new_code = old_code
            action_error = str(exc)

        change = diff_summary(old_code, new_code)
        new_score, grade_error = grade_code(self.state.task_name, new_code)
        reward = compute_reward(
            previous_score=self.state.last_score,
            current_score=new_score,
            changed_lines=int(change["changed_lines"]),
            action_error=action_error,
            grade_error=grade_error,
        )
        reward = max(0.0, min(reward, 1.0))

        self.state.code = new_code
        self.state.step_count += 1
        self.state.history.append(action)
        self.state.last_score = new_score
        self.state.error = action_error or grade_error

        done = new_score >= (1.0 - PUBLIC_SCORE_EPSILON) or self.state.step_count >= self.state.max_steps

        log(
            f"task={self.state.task_name} step={self.state.step_count} "
            f"score={new_score} reward={reward}"
        )

        info = {
            "score": new_score,
            "changed_lines": change["changed_lines"],
            "action_error": action_error,
            "grade_error": grade_error,
        }

        return self._get_obs(), reward, done, info

    def _get_obs(self) -> dict:
        if self.state is None:
            raise RuntimeError("Environment is not initialized. Call reset first.")

        return self.state.to_observation()
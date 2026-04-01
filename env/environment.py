from env.state import CodeState
from env.logic import apply_action
from env.reward import compute_reward
from tasks.task_loader import load_task

class CodeFixEnv:

    def reset(self, task="easy"):
        self.state = load_task(task)
        return self._get_obs()

    def step(self, action):
        old_code = self.state.code

        new_code = apply_action(old_code, action)

        reward = compute_reward(old_code, new_code)

        self.state.code = new_code
        self.state.step_count += 1
        self.state.history.append(action)

        done = reward >= 1.0 or self.state.step_count >= 5

        return self._get_obs(), reward, done, {}

    def _get_obs(self):
        return {
            "code": self.state.code,
            "step_count": self.state.step_count,
            "history": self.state.history
        }
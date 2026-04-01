from fastapi import FastAPI
from env.environment import CodeFixEnv
from models.request_models import StepRequest

app = FastAPI()
env = CodeFixEnv()

@app.post("/reset")
def reset():
    state = env.reset("easy")
    return {"state": state}

@app.post("/step")
def step(req: StepRequest):
    obs, reward, done, _ = env.step(req.action)
    return {
        "state": obs,
        "reward": reward,
        "done": done
    }
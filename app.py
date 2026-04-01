from typing import Optional

from fastapi import Body, FastAPI, HTTPException

from env.environment import CodeFixEnv
from models.request_models import ResetRequest, StepRequest
from models.response_models import ResetResponse, StepResponse
from utils.logger import log

app = FastAPI(title="CodeFixEnv Demo")
runtime_env = CodeFixEnv()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/reset", response_model=ResetResponse)
def reset(req: Optional[ResetRequest] = Body(default=None)):
    task_name = req.task if req else "easy"

    try:
        state = runtime_env.reset(task_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    log(f"Episode reset with task '{task_name}'")
    return {"state": state}


@app.post("/step", response_model=StepResponse)
def step(req: StepRequest):
    try:
        obs, reward, done, info = runtime_env.step(req.action)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "state": obs,
        "reward": reward,
        "done": done,
        "score": info.get("score", 0.0),
    }
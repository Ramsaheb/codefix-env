from typing import Optional

from fastapi import Body, FastAPI, HTTPException, Response, status

from env.session_manager import SessionManager, SessionNotFoundError
from models.request_models import ResetRequest, StepRequest
from models.response_models import ResetResponse, StepResponse
from settings import load_settings
from tasks.task_loader import available_tasks
from utils.logger import configure_logging, log

settings = load_settings()
configure_logging(settings.log_level)

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Deployment-ready RL environment for iterative code debugging tasks.",
)
session_manager = SessionManager(
    max_sessions=settings.max_sessions,
    session_ttl_seconds=settings.session_ttl_seconds,
)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
    }


@app.get("/ready")
def ready():
    return {
        "status": "ready",
        "default_task": settings.default_task,
        "tasks": available_tasks(),
        **session_manager.stats(),
    }


@app.post("/reset", response_model=ResetResponse)
def reset(req: Optional[ResetRequest] = Body(default=None)):
    payload = req or ResetRequest(task=settings.default_task)
    task_name = payload.task
    requested_session_id = payload.session_id or ""

    try:
        session_id, state = session_manager.reset(task=task_name, session_id=requested_session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    log(f"Episode reset session={session_id} task={task_name}")
    return {"session_id": session_id, "state": state}


@app.post("/step", response_model=StepResponse)
def step(req: StepRequest):
    try:
        obs, reward, done, info = session_manager.step(req.session_id, req.action)
    except SessionNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=(
                "Session not found. Call /reset first, or pass an existing session_id in /reset "
                "to resume an episode."
            ),
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "session_id": req.session_id,
        "state": obs,
        "reward": reward,
        "done": done,
        "score": info.get("score", 0.0),
    }


@app.delete("/session/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(session_id: str):
    removed = session_manager.delete(session_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Session not found.")

    return Response(status_code=status.HTTP_204_NO_CONTENT)
from typing import Optional

from fastapi import Body, FastAPI, HTTPException, Request, Response, status
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import os

from env.session_manager import SessionManager, SessionNotFoundError
from env.state import to_public_score
from models.request_models import ResetRequest, StepRequest
from models.response_models import MetadataResponse, Observation, ResetResponse, SchemaResponse, StateResponse, StepResponse
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


@app.exception_handler(Exception)
def handle_unexpected_exception(request: Request, exc: Exception):
    log(f"Unhandled server error on {request.url.path}: {exc.__class__.__name__}: {exc}")
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
    }


static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/", response_class=FileResponse)
def root():
    return FileResponse(os.path.join(static_dir, "index.html"))


@app.get("/ready")
def ready():
    return {
        "status": "ready",
        "default_task": settings.default_task,
        "tasks": available_tasks(),
        **session_manager.stats(),
    }


@app.get("/schema", response_model=SchemaResponse)
def schema():
    # /step accepts a string action, while observation/state expose the same state structure.
    return {
        "action": {
            "title": "CodeFixAction",
            "type": "object",
            "additionalProperties": False,
            "required": ["action"],
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Action or code-edit command to apply to current state",
                    "minLength": 1,
                    "maxLength": 50000,
                }
            },
        },
        "observation": Observation.model_json_schema(),
        "state": Observation.model_json_schema(),
    }


@app.get("/metadata", response_model=MetadataResponse)
def metadata():
    return {
        "name": settings.app_name,
        "description": "Code debugging RL environment",
        "version": settings.app_version,
        "author": "CodeFixEnv Team",
        "documentation_url": "/docs",
        "readme_content": None,
        "tasks": available_tasks(),
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
        "score": to_public_score(obs.get("score", 0.001)),
    }


@app.get("/state/{session_id}", response_model=StateResponse)
def state(session_id: str):
    try:
        obs = session_manager.state(session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=(
                "Session not found. Call /reset first, or pass an existing session_id in /reset "
                "to resume an episode."
            ),
        ) from exc

    return {"session_id": session_id, "state": obs}


@app.delete("/session/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(session_id: str):
    removed = session_manager.delete(session_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Session not found.")

    return Response(status_code=status.HTTP_204_NO_CONTENT)
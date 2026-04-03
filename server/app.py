"""
FastAPI application for the CodeFix Environment.

This module creates an HTTP server that exposes the CodeFixEnvironment
over HTTP and WebSocket endpoints, compatible with EnvClient.

Usage:
    # Development (with auto-reload):
    uvicorn server.app:app --reload --host 0.0.0.0 --port 7860

    # Production:
    uvicorn server.app:app --host 0.0.0.0 --port 7860

    # Or run directly:
    python -m server.app
"""

import sys
import os

# Ensure project root is on sys.path so that sibling packages
# (env, graders, tasks, utils, models) are importable when running
# as 'python -m server.app' or via the [project.scripts] entry point.
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from openenv.core.env_server import create_app

from env.environment import CodeFixEnvironment
from models import CodeFixAction, CodeFixObservation

# Create the app with OpenEnv-managed endpoints.
# Pass the class (factory) so each WS/HTTP session gets its own instance.
app = create_app(
    CodeFixEnvironment,
    CodeFixAction,
    CodeFixObservation,
    env_name="codefix_env",
    max_concurrent_envs=50,
)


def main():
    """Entry point for direct execution via `python -m server.app` or [project.scripts]."""
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)


if __name__ == "__main__":
    main()

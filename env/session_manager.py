from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Dict, Tuple
from uuid import uuid4

from env.environment import CodeFixEnv


@dataclass
class SessionEntry:
    env: CodeFixEnv
    last_accessed: datetime


class SessionNotFoundError(KeyError):
    pass


class SessionManager:
    def __init__(self, max_sessions: int, session_ttl_seconds: int):
        self._max_sessions = max_sessions
        self._session_ttl = timedelta(seconds=session_ttl_seconds)
        self._sessions: Dict[str, SessionEntry] = {}
        self._lock = Lock()

    def reset(self, task: str, session_id: str = "") -> Tuple[str, dict]:
        with self._lock:
            self._cleanup_stale_locked()

            sid = session_id.strip() or str(uuid4())
            existing = self._sessions.get(sid)
            env = existing.env if existing else CodeFixEnv()

            state = env.reset(task)
            self._sessions[sid] = SessionEntry(env=env, last_accessed=datetime.now(timezone.utc))
            self._prune_to_capacity_locked()

        return sid, state

    def step(self, session_id: str, action: str):
        with self._lock:
            self._cleanup_stale_locked()
            entry = self._sessions.get(session_id)
            if entry is None:
                raise SessionNotFoundError(session_id)

            result = entry.env.step(action)
            entry.last_accessed = datetime.now(timezone.utc)
            return result

    def state(self, session_id: str) -> dict:
        with self._lock:
            self._cleanup_stale_locked()
            entry = self._sessions.get(session_id)
            if entry is None:
                raise SessionNotFoundError(session_id)

            entry.last_accessed = datetime.now(timezone.utc)
            return entry.env._get_obs()

    def delete(self, session_id: str) -> bool:
        with self._lock:
            return self._sessions.pop(session_id, None) is not None

    def stats(self) -> dict:
        with self._lock:
            self._cleanup_stale_locked()
            return {
                "active_sessions": len(self._sessions),
                "max_sessions": self._max_sessions,
                "session_ttl_seconds": int(self._session_ttl.total_seconds()),
            }

    def _cleanup_stale_locked(self) -> None:
        cutoff = datetime.now(timezone.utc) - self._session_ttl
        stale_keys = [
            sid for sid, entry in self._sessions.items() if entry.last_accessed < cutoff
        ]
        for sid in stale_keys:
            del self._sessions[sid]

    def _prune_to_capacity_locked(self) -> None:
        if len(self._sessions) <= self._max_sessions:
            return

        ordered = sorted(self._sessions.items(), key=lambda item: item[1].last_accessed)
        to_remove = len(self._sessions) - self._max_sessions
        for sid, _ in ordered[:to_remove]:
            del self._sessions[sid]
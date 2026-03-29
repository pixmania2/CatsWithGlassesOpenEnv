"""
session.py — In-Memory Session Management for the PTPA OpenEnv Environment

Manages episode lifecycle: IDLE -> ACTIVE -> GRADING -> DONE
Single-worker safe (in-memory dict), keyed by episode_id.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from models import (
    EpisodeStatus,
    GraderResult,
    PTPAAction,
    PTPAObservation,
    PTPAState,
    TaskID,
)


# ---------------------------------------------------------------------------
# Valid state transitions
# ---------------------------------------------------------------------------
_VALID_TRANSITIONS = {
    EpisodeStatus.IDLE:    {EpisodeStatus.ACTIVE},
    EpisodeStatus.ACTIVE:  {EpisodeStatus.GRADING},
    EpisodeStatus.GRADING: {EpisodeStatus.DONE},
    EpisodeStatus.DONE:    set(),                       # terminal
}


# ---------------------------------------------------------------------------
# Session entry — one per episode
# ---------------------------------------------------------------------------
@dataclass
class SessionEntry:
    """Holds all mutable data for a single episode."""

    episode_id: str
    task_id: TaskID
    state: PTPAState
    created_at: float                                   # time.time()

    # Observation / step history (for baseline trace recording)
    step_history: List[Dict[str, Any]] = field(default_factory=list)

    # Task 3 appeal letter (stored when generate_appeal_letter action runs)
    appeal_letter: Optional[str] = None

    # Grader result (populated after POST /grader)
    grader_result: Optional[GraderResult] = None

    # The last submitted decision parameters (for grading)
    submitted_decision: Optional[Dict[str, Any]] = None

    @property
    def status(self) -> EpisodeStatus:
        return self.state.status

    @property
    def is_expired(self) -> bool:
        return (time.time() - self.created_at) > 3600   # 1-hour timeout


# ---------------------------------------------------------------------------
# Session store
# ---------------------------------------------------------------------------
class SessionStore:
    """In-memory session store keyed by ``episode_id``."""

    def __init__(
        self,
        max_sessions: int = 50,
        timeout_seconds: int = 3600,
    ) -> None:
        self._sessions: Dict[str, SessionEntry] = {}
        self._max_sessions = max_sessions
        self._timeout = timeout_seconds

    # -- helpers -------------------------------------------------------------

    def _cleanup_expired(self) -> None:
        now = time.time()
        expired = [
            eid
            for eid, entry in self._sessions.items()
            if (now - entry.created_at) > self._timeout
        ]
        for eid in expired:
            del self._sessions[eid]

    @staticmethod
    def generate_episode_id() -> str:
        return uuid.uuid4().hex[:12]

    # -- CRUD ----------------------------------------------------------------

    def create(self, task_id: TaskID, state: PTPAState) -> SessionEntry:
        """Create a new session entry. Returns the SessionEntry."""
        self._cleanup_expired()

        if len(self._sessions) >= self._max_sessions:
            oldest_eid = min(
                self._sessions, key=lambda k: self._sessions[k].created_at
            )
            del self._sessions[oldest_eid]

        entry = SessionEntry(
            episode_id=state.episode_id,
            task_id=task_id,
            state=state,
            created_at=time.time(),
        )
        self._sessions[entry.episode_id] = entry
        return entry

    def get(self, episode_id: str) -> SessionEntry:
        """Retrieve a session. Raises ``KeyError`` if not found or expired."""
        self._cleanup_expired()
        if episode_id not in self._sessions:
            raise KeyError(f"Episode not found: {episode_id}")
        return self._sessions[episode_id]

    def exists(self, episode_id: str) -> bool:
        return episode_id in self._sessions

    def update_state(self, episode_id: str, new_state: PTPAState) -> None:
        entry = self.get(episode_id)
        entry.state = new_state

    def set_status(self, episode_id: str, new_status: EpisodeStatus) -> None:
        """Transition episode status with validation."""
        entry = self.get(episode_id)
        current = entry.state.status

        if new_status not in _VALID_TRANSITIONS.get(current, set()):
            raise ValueError(
                f"Invalid status transition: {current.value} -> {new_status.value}"
            )
        entry.state.status = new_status

    def record_step(
        self,
        episode_id: str,
        action: PTPAAction,
        observation: PTPAObservation,
        cumulative_reward: float,
    ) -> None:
        """Append a step to the episode history (for baseline traces)."""
        entry = self.get(episode_id)
        entry.step_history.append(
            {
                "step_number": len(entry.step_history) + 1,
                "action": action.model_dump(),
                "observation": observation.model_dump(),
                "cumulative_reward": cumulative_reward,
            }
        )

    def delete(self, episode_id: str) -> None:
        self._sessions.pop(episode_id, None)

    def list_sessions(self) -> List[Dict[str, Any]]:
        """Return a summary of all active sessions."""
        self._cleanup_expired()
        return [
            {
                "episode_id": e.episode_id,
                "task_id": e.task_id.value,
                "status": e.status.value,
                "step_count": e.state.step_count,
                "created_at": e.state.created_at,
            }
            for e in self._sessions.values()
        ]

    @property
    def count(self) -> int:
        return len(self._sessions)

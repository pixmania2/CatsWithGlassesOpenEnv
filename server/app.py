"""
app.py — FastAPI Application for the PTPA OpenEnv Environment

All endpoints required by the OpenEnv specification:
  POST /reset, POST /step, GET /state, GET /tasks,
  POST /grader, POST /baseline, GET /health, GET /validate, GET /info
"""

from __future__ import annotations

import logging
import os
import random
import traceback
from typing import Any, Dict

import yaml
from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from models import (
    BaselineResponse,
    EpisodeStatus,
    GraderRequest,
    GraderResult,
    PTPAState,
    ResetRequest,
    ResetResponse,
    StepRequest,
    StepResponse,
    TaskID,
    TaskListResponse,
)
from tasks import get_all_tasks, get_task
from server.session import SessionStore
from environment.engine import PTPAEngine

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
ENV_NAME = "healthcare_prior_auth"
ENV_VERSION = "1.2.0"

LOG_LEVEL = os.getenv("PTPA_LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger("ptpa")

# ---------------------------------------------------------------------------
# App + middleware
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Patient Triage & Prior Authorization (PTPA) OpenEnv",
    version=ENV_VERSION,
    description="A healthcare RL environment for prior authorization workflows.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Global singletons
# ---------------------------------------------------------------------------
session_store = SessionStore(
    max_sessions=int(os.getenv("PTPA_MAX_SESSIONS", "50")),
    timeout_seconds=3600,
)
engine = PTPAEngine()

# ---------------------------------------------------------------------------
# Static files + UI
# ---------------------------------------------------------------------------
_STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")


@app.get("/", include_in_schema=False)
async def ui_root():
    """Serve the interactive UI."""
    return FileResponse(os.path.join(_STATIC_DIR, "index.html"))


app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")


# ===================================================================
# POST /reset
# ===================================================================
@app.post("/reset", response_model=ResetResponse)
async def reset_endpoint(req: ResetRequest = Body(default=None)):
    """Initialize a new episode for the given task."""
    if req is None:
        req = ResetRequest()

    # Default to a random task if none provided
    task_id = req.task_id
    if task_id is None:
        task_id = random.choice(list(TaskID))

    try:
        get_task(task_id)  # validate task exists
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Unknown task_id: {task_id}")

    episode_id = SessionStore.generate_episode_id()

    seed = req.seed
    if seed is None:
        seed = random.randint(0, 99999)

    seed_override = os.getenv("PTPA_SEED_OVERRIDE")
    if seed_override is not None:
        seed = int(seed_override)

    try:
        diff_config = req.difficulty_config if req.difficulty_config else None
        obs, state = engine.reset(
            episode_id=episode_id,
            task_id=task_id,
            seed=seed,
            patient_id=req.patient_id,
            difficulty_config=diff_config,
        )
    except Exception as exc:
        logger.error("Reset failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))

    session_store.create(task_id=task_id, state=state)

    return ResetResponse(
        episode_id=episode_id,
        task_id=task_id,
        initial_observation=obs,
        state=state,
    )


# ===================================================================
# POST /step
# ===================================================================
@app.post("/step", response_model=StepResponse)
async def step_endpoint(req: StepRequest):
    """Execute one agent action in the given episode."""
    # 1. Lookup session
    try:
        entry = session_store.get(req.episode_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Episode not found: {req.episode_id}")

    # 2. Validate status
    if entry.status != EpisodeStatus.ACTIVE:
        raise HTTPException(
            status_code=400,
            detail=f"Episode is {entry.status.value}, not ACTIVE. Cannot step.",
        )

    # 3. Validate action belongs to correct task & patient
    action = req.action
    if action.task_id != entry.task_id:
        raise HTTPException(
            status_code=400,
            detail=f"Action task_id '{action.task_id.value}' does not match episode task '{entry.task_id.value}'",
        )
    if action.patient_id != entry.state.patient.patient_id:
        raise HTTPException(
            status_code=400,
            detail=f"Action patient_id '{action.patient_id}' does not match episode patient '{entry.state.patient.patient_id}'",
        )

    # 4. Execute step
    try:
        obs, reward, done, state = engine.step(req.episode_id, action)
    except Exception as exc:
        logger.error("Step failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))

    # 5. Update session
    session_store.update_state(req.episode_id, state)
    session_store.record_step(
        req.episode_id,
        action,
        obs,
        state.progress.total_reward_so_far,
    )

    # 6. Transition to GRADING if done
    if done and entry.status == EpisodeStatus.ACTIVE:
        session_store.set_status(req.episode_id, EpisodeStatus.GRADING)

    return StepResponse(
        episode_id=req.episode_id,
        observation=obs,
        reward=reward,
        done=done,
        state=state,
    )


# ===================================================================
# GET /state
# ===================================================================
@app.get("/state", response_model=PTPAState)
async def state_endpoint(episode_id: str = Query(..., description="Episode ID")):
    """Return the full state for a given episode."""
    try:
        entry = session_store.get(episode_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Episode not found: {episode_id}")
    return entry.state


# ===================================================================
# GET /tasks
# ===================================================================
@app.get("/tasks", response_model=TaskListResponse)
async def tasks_endpoint():
    """Return all available tasks with action schemas and grader specs."""
    return TaskListResponse(
        tasks=get_all_tasks(),
        environment=ENV_NAME,
        version=ENV_VERSION,
    )


# ===================================================================
# POST /grader
# ===================================================================
@app.post("/grader", response_model=GraderResult)
async def grader_endpoint(req: GraderRequest):
    """Grade a completed episode and return detailed scores."""
    try:
        entry = session_store.get(req.episode_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Episode not found: {req.episode_id}")

    if entry.status not in (EpisodeStatus.ACTIVE, EpisodeStatus.GRADING):
        raise HTTPException(
            status_code=400,
            detail=f"Episode is {entry.status.value}. Grading requires ACTIVE or GRADING status.",
        )

    # Transition to GRADING if still ACTIVE
    if entry.status == EpisodeStatus.ACTIVE:
        session_store.set_status(req.episode_id, EpisodeStatus.GRADING)

    try:
        result = engine.grade(req.episode_id)
    except Exception as exc:
        logger.error("Grading failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))

    # Transition to DONE
    session_store.set_status(req.episode_id, EpisodeStatus.DONE)

    entry.grader_result = result
    return result


# ===================================================================
# POST /baseline
# ===================================================================
@app.post("/baseline", response_model=BaselineResponse)
async def baseline_endpoint():
    """
    Run the baseline gpt-5.4-mini agent against all 3 tasks.

    This endpoint orchestrates the full baseline loop internally:
    reset -> step loop -> grade for each task.
    """
    from baseline.baseline import run_baseline_internal

    try:
        response = await run_baseline_internal(engine, session_store)
    except Exception as exc:
        logger.error("Baseline failed: %s\n%s", exc, traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Baseline failed: {exc}")

    return response


# ===================================================================
# GET /health
# ===================================================================
@app.get("/health")
async def health_endpoint():
    """Liveness check."""
    return {
        "status": "healthy",
        "environment": ENV_NAME,
        "version": ENV_VERSION,
        "active_sessions": session_store.count,
    }


# ===================================================================
# GET /validate
# ===================================================================
@app.get("/validate")
async def validate_endpoint():
    """Validate environment integrity."""
    checks: Dict[str, Any] = {}

    # Check tasks
    try:
        tasks = get_all_tasks()
        checks["tasks_loaded"] = {"status": "pass", "count": len(tasks)}
    except Exception as e:
        checks["tasks_loaded"] = {"status": "fail", "error": str(e)}

    # Check patient data (via engine)
    from environment.engine import _PATIENTS, _POLICIES
    checks["patient_fixtures"] = {
        "status": "pass" if len(_PATIENTS) >= 15 else "fail",
        "count": len(_PATIENTS),
        "expected": ">=15",
    }
    checks["policy_database"] = {
        "status": "pass" if len(_POLICIES) >= 3 else "fail",
        "insurers": list(_POLICIES.keys()),
    }

    # Check openenv.yaml
    try:
        yaml_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "openenv.yaml")
        with open(yaml_path) as f:
            manifest = yaml.safe_load(f)
        checks["openenv_yaml"] = {"status": "pass", "name": manifest.get("name")}
    except Exception as e:
        checks["openenv_yaml"] = {"status": "fail", "error": str(e)}

    # Check endpoints
    required_endpoints = ["/reset", "/step", "/state", "/tasks", "/grader", "/baseline", "/health"]
    routes = [getattr(r, "path", None) for r in app.routes]
    missing = [ep for ep in required_endpoints if ep not in routes]
    checks["endpoints"] = {
        "status": "pass" if not missing else "fail",
        "missing": missing,
    }

    all_pass = all(
        v.get("status") == "pass" for v in checks.values() if isinstance(v, dict)
    )
    return {"valid": all_pass, "checks": checks}


# ===================================================================
# GET /info
# ===================================================================
@app.get("/info")
async def info_endpoint():
    """Return environment metadata."""
    try:
        yaml_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "openenv.yaml")
        with open(yaml_path) as f:
            manifest = yaml.safe_load(f)
    except Exception:
        manifest = {}

    return {
        "name": manifest.get("name", "healthcare_prior_auth"),
        "version": manifest.get("version", "1.2.0"),
        "display_name": manifest.get("display_name", "Patient Triage & Prior Authorization (PTPA)"),
        "description": manifest.get("description", ""),
        "tasks": [
            {"id": t.task_id.value, "name": t.name, "difficulty": t.difficulty.value}
            for t in get_all_tasks()
        ],
        "endpoints": manifest.get("endpoints", {}),
        "spec": manifest.get("spec", {}),
    }


# ===================================================================
# GET /replay
# ===================================================================
@app.get("/replay")
async def replay_endpoint(episode_id: str = Query(..., description="Episode ID")):
    """Return the full step-by-step trace for a completed episode."""
    try:
        entry = session_store.get(episode_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Episode not found: {episode_id}")

    return {
        "episode_id": entry.episode_id,
        "task_id": entry.task_id.value,
        "status": entry.status.value,
        "step_count": entry.state.step_count,
        "total_reward": entry.state.progress.total_reward_so_far,
        "observation_history": [h.model_dump() for h in entry.state.observation_history],
        "step_history": entry.step_history,
        "grader_result": entry.grader_result.model_dump() if entry.grader_result else None,
        "difficulty_config": entry.state.difficulty_config.model_dump(),
    }


# ===================================================================
# GET /metadata  (OpenEnv spec requirement)
# ===================================================================
@app.get("/metadata")
async def metadata_endpoint():
    """Return environment name and description (OpenEnv spec)."""
    try:
        yaml_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "openenv.yaml")
        with open(yaml_path) as f:
            manifest = yaml.safe_load(f)
    except Exception:
        manifest = {}

    return {
        "name": manifest.get("name", "healthcare_prior_auth"),
        "description": manifest.get("description", ""),
        "version": manifest.get("version", ENV_VERSION),
        "display_name": manifest.get("display_name", "Patient Triage & Prior Authorization"),
        "author": manifest.get("author", "PTPA Team"),
    }


# ===================================================================
# GET /schema  (OpenEnv spec requirement)
# ===================================================================
@app.get("/schema")
async def schema_endpoint():
    """Return JSON schemas for action, observation, and state (OpenEnv spec)."""
    from models import PTPAAction, PTPAObservation, PTPAState

    return {
        "action": PTPAAction.model_json_schema(),
        "observation": PTPAObservation.model_json_schema(),
        "state": PTPAState.model_json_schema(),
    }


# ===================================================================
# POST /mcp  (OpenEnv spec — MCP JSON-RPC stub)
# ===================================================================
@app.post("/mcp")
async def mcp_endpoint():
    """MCP JSON-RPC endpoint stub (OpenEnv spec)."""
    return {
        "jsonrpc": "2.0",
        "result": {
            "name": "healthcare_prior_auth",
            "version": ENV_VERSION,
            "capabilities": {
                "tools": True,
                "resources": False,
                "prompts": False,
            },
        },
        "id": 1,
    }


# ===================================================================
# WebSocket — imported from websocket module
# ===================================================================
from server.websocket import websocket_endpoint  # noqa: E402

app.add_api_websocket_route("/ws", websocket_endpoint)


# ===================================================================
# Entry point for `openenv serve` and `project.scripts`
# ===================================================================
def main():
    """Start the PTPA OpenEnv server."""
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()

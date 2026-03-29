"""
websocket.py — WebSocket Handler for the PTPA OpenEnv Environment

Supports real-time multi-turn interaction via /ws.
Protocol:
  Client sends JSON: {"type": "reset"|"step", "data": {...}}
  Server responds with JSON: corresponding response or error.
"""

from __future__ import annotations

import json
import logging

from fastapi import WebSocket, WebSocketDisconnect

from models import (
    EpisodeStatus,
    PTPAAction,
    ResetRequest,
    StepRequest,
    TaskID,
)

logger = logging.getLogger("ptpa.ws")


async def websocket_endpoint(websocket: WebSocket):
    """
    Single-episode WebSocket session.

    Message format (client -> server):
      {"type": "reset", "data": {"task_id": "task1_verification", "seed": 42}}
      {"type": "step",  "data": {"episode_id": "abc123", "action": {...}}}

    Response format (server -> client):
      {"type": "reset_response"|"step_response"|"grader_response"|"error", "data": {...}}
    """
    await websocket.accept()

    # Import here to avoid circular import at module level
    from server.app import engine, session_store
    from server.session import SessionStore

    current_episode_id: str | None = None

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "data": {"error": "Invalid JSON"}})
                continue

            msg_type = msg.get("type", "")
            data = msg.get("data", {})

            # ---- RESET ----
            if msg_type == "reset":
                try:
                    task_id = TaskID(data.get("task_id", ""))
                except ValueError:
                    await websocket.send_json({"type": "error", "data": {"error": f"Invalid task_id: {data.get('task_id')}"}})
                    continue

                episode_id = SessionStore.generate_episode_id()
                seed = data.get("seed")
                patient_id = data.get("patient_id")

                import random
                if seed is None:
                    seed = random.randint(0, 99999)

                obs, state = engine.reset(
                    episode_id=episode_id,
                    task_id=task_id,
                    seed=seed,
                    patient_id=patient_id,
                )
                session_store.create(task_id=task_id, state=state)
                current_episode_id = episode_id

                await websocket.send_json({
                    "type": "reset_response",
                    "data": {
                        "episode_id": episode_id,
                        "task_id": task_id.value,
                        "initial_observation": obs.model_dump(),
                        "state": state.model_dump(),
                    },
                })

            # ---- STEP ----
            elif msg_type == "step":
                episode_id = data.get("episode_id", current_episode_id)
                if not episode_id:
                    await websocket.send_json({"type": "error", "data": {"error": "No episode_id. Call reset first."}})
                    continue

                try:
                    entry = session_store.get(episode_id)
                except KeyError:
                    await websocket.send_json({"type": "error", "data": {"error": f"Episode not found: {episode_id}"}})
                    continue

                if entry.status != EpisodeStatus.ACTIVE:
                    await websocket.send_json({"type": "error", "data": {"error": f"Episode is {entry.status.value}, not ACTIVE."}})
                    continue

                try:
                    action_data = data.get("action", {})
                    action = PTPAAction(**action_data)
                except Exception as e:
                    await websocket.send_json({"type": "error", "data": {"error": f"Invalid action: {e}"}})
                    continue

                obs, reward, done, state = engine.step(episode_id, action)
                session_store.update_state(episode_id, state)
                session_store.record_step(episode_id, action, obs, state.progress.total_reward_so_far)

                if done and entry.status == EpisodeStatus.ACTIVE:
                    try:
                        session_store.set_status(episode_id, EpisodeStatus.GRADING)
                    except ValueError:
                        pass

                await websocket.send_json({
                    "type": "step_response",
                    "data": {
                        "episode_id": episode_id,
                        "observation": obs.model_dump(),
                        "reward": reward,
                        "done": done,
                        "state": state.model_dump(),
                    },
                })

                # Auto-send grader result if done
                if done:
                    try:
                        grader_result = engine.grade(episode_id)
                        try:
                            session_store.set_status(episode_id, EpisodeStatus.DONE)
                        except ValueError:
                            pass
                        await websocket.send_json({
                            "type": "grader_response",
                            "data": grader_result.model_dump(),
                        })
                    except Exception as e:
                        logger.error("Auto-grade failed: %s", e)

            # ---- UNKNOWN ----
            else:
                await websocket.send_json({
                    "type": "error",
                    "data": {"error": f"Unknown message type: {msg_type}. Use 'reset' or 'step'."},
                })

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected (episode: %s)", current_episode_id)
    except Exception as e:
        logger.error("WebSocket error: %s", e)
        try:
            await websocket.send_json({"type": "error", "data": {"error": str(e)}})
        except Exception:
            pass

"""
websocket.py — WebSocket Handler for the PTPA OpenEnv Environment

Compatible with both:
  1. OpenEnv SDK GenericEnvClient (sends action dict directly as step data)
  2. Custom clients (sends {"episode_id": ..., "action": {...}})

Protocol (OpenEnv SDK):
  Client -> {"type": "reset", "data": {"task_id": "..."}}
  Server -> {"type": "reset_response", "data": {"observation": {...}, "reward": null, "done": false}}
  Client -> {"type": "step", "data": {"action_type": "...", ...}}
  Server -> {"type": "step_response", "data": {"observation": {...}, "reward": 0.1, "done": false}}
  Client -> {"type": "state"}
  Server -> {"type": "state_response", "data": {...state...}}
"""

from __future__ import annotations

import json
import logging
import random

from fastapi import WebSocket, WebSocketDisconnect

from models import (
    EpisodeStatus,
    PTPAAction,
    TaskID,
)

logger = logging.getLogger("ptpa.ws")


async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    from server.app import engine, session_store
    from server.session import SessionStore

    current_episode_id: str | None = None
    current_patient_id: str | None = None
    current_task_id: TaskID | None = None

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
                task_id_str = data.get("task_id", "")
                if not task_id_str:
                    # Default to random task
                    task_id = random.choice(list(TaskID))
                else:
                    try:
                        task_id = TaskID(task_id_str)
                    except ValueError:
                        await websocket.send_json({"type": "error", "data": {"error": f"Invalid task_id: {task_id_str}"}})
                        continue

                episode_id = SessionStore.generate_episode_id()
                seed = data.get("seed")
                patient_id = data.get("patient_id")

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
                current_patient_id = state.patient.patient_id
                current_task_id = task_id

                # OpenEnv SDK expects: observation, reward, done at top level
                await websocket.send_json({
                    "type": "reset_response",
                    "data": {
                        "observation": obs.model_dump(),
                        "reward": None,
                        "done": False,
                        "episode_id": episode_id,
                        "task_id": task_id.value,
                        "state": state.model_dump(),
                    },
                })

            # ---- STEP ----
            elif msg_type == "step":
                if not current_episode_id:
                    await websocket.send_json({"type": "error", "data": {"error": "No active episode. Call reset first."}})
                    continue

                episode_id = current_episode_id

                try:
                    entry = session_store.get(episode_id)
                except KeyError:
                    await websocket.send_json({"type": "error", "data": {"error": f"Episode not found: {episode_id}"}})
                    continue

                if entry.status != EpisodeStatus.ACTIVE:
                    await websocket.send_json({"type": "error", "data": {"error": f"Episode is {entry.status.value}, not ACTIVE."}})
                    continue

                # Handle both formats:
                # SDK: data = {"action_type": "...", "patient_id": "...", ...}
                # Custom: data = {"episode_id": "...", "action": {"action_type": "...", ...}}
                if "action" in data and isinstance(data["action"], dict):
                    action_data = data["action"]
                elif "action_type" in data:
                    action_data = data
                else:
                    await websocket.send_json({"type": "error", "data": {"error": "Step data must contain 'action_type' or 'action' field."}})
                    continue

                # Fill in defaults from session context
                action_data.setdefault("patient_id", current_patient_id or entry.state.patient.patient_id)
                action_data.setdefault("task_id", (current_task_id or entry.task_id).value)
                action_data.setdefault("parameters", {})

                try:
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

                # OpenEnv SDK expects: observation, reward, done at top level
                await websocket.send_json({
                    "type": "step_response",
                    "data": {
                        "observation": obs.model_dump(),
                        "reward": reward,
                        "done": done,
                        "episode_id": episode_id,
                        "state": state.model_dump(),
                    },
                })

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

            # ---- STATE ----
            elif msg_type == "state":
                if not current_episode_id:
                    await websocket.send_json({"type": "error", "data": {"error": "No active episode."}})
                    continue
                try:
                    entry = session_store.get(current_episode_id)
                    await websocket.send_json({
                        "type": "state_response",
                        "data": entry.state.model_dump(),
                    })
                except KeyError:
                    await websocket.send_json({"type": "error", "data": {"error": "Episode not found."}})

            # ---- UNKNOWN ----
            else:
                await websocket.send_json({
                    "type": "error",
                    "data": {"error": f"Unknown message type: {msg_type}. Use 'reset', 'step', or 'state'."},
                })

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected (episode: %s)", current_episode_id)
    except Exception as e:
        logger.error("WebSocket error: %s", e)
        try:
            await websocket.send_json({"type": "error", "data": {"error": str(e)}})
        except Exception:
            pass

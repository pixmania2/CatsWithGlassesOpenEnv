"""
Inference Script — PTPA OpenEnv (Healthcare Prior Authorization)
================================================================
MANDATORY ENV VARS:
    API_BASE_URL   The API endpoint for the LLM (default: https://router.huggingface.co/v1)
    MODEL_NAME     The model identifier (default: Qwen/Qwen2.5-72B-Instruct)
    HF_TOKEN       Your Hugging Face / API key
    LOCAL_IMAGE_NAME  Docker image name when using from_docker_image()

STDOUT FORMAT:
    [START] task=<task> env=<benchmark> model=<model>
    [STEP]  step=<n> action=<action> reward=<0.00> done=<true|false> error=<null|msg>
    [END]   success=<true|false> steps=<n> score=<0.000> rewards=<r1,r2,...>
"""

import asyncio
import json
import os
import re
import textwrap
from typing import Any, Dict, List, Optional

from openai import OpenAI
from openenv import GenericEnvClient, GenericAction

# ---------------------------------------------------------------------------
# Configuration from environment variables
# ---------------------------------------------------------------------------
IMAGE_NAME = os.getenv("LOCAL_IMAGE_NAME", "ptpa-env")
API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY") or os.getenv("OPENAI_API_KEY")
API_BASE_URL = os.getenv("API_BASE_URL") or "https://router.huggingface.co/v1"
MODEL_NAME = os.getenv("MODEL_NAME") or "Qwen/Qwen2.5-72B-Instruct"

BENCHMARK = "healthcare_prior_auth"
TEMPERATURE = 0.3
MAX_COMPLETION_TOKENS = 800

# Task definitions: task_id -> (max_steps, strategy description)
TASKS = {
    "task1_verification": {
        "max_steps": 10,
        "strategy": (
            "1) check_eligibility with member_id and insurer from the patient record. "
            "2) check_cpt_coverage with cpt_code, icd10_code, insurer. "
            "3) submit_decision with approve/deny and rationale citing policy section."
        ),
    },
    "task2_mri_necessity": {
        "max_steps": 20,
        "strategy": (
            "1) extract_pt_sessions to get PT records. "
            "2) check_red_flags for clinical urgency. "
            "3) query_policy_database insurer=X section=prior_auth_criteria. "
            "4) submit_decision citing specific PT weeks vs required threshold."
        ),
    },
    "task3_cgm_appeal": {
        "max_steps": 25,
        "strategy": (
            "1) extract_lab_values for HbA1c, fasting_glucose, glucose_reading. "
            "2) check_step_therapy for CGM with insurer. "
            "3) query_policy_database insurer=X section=exception_criteria. "
            "4) generate_appeal_letter with evidence and exception clause. "
            "5) submit_decision with 'appeal' citing exact values and thresholds."
        ),
    },
    "task4_peer_review": {
        "max_steps": 30,
        "strategy": (
            "1) review_denial_letter to understand the denial reason. "
            "2) gather_counter_evidence from relevant PRS sections. "
            "3) check_red_flags if denial mentions no clinical urgency. "
            "4) submit_rebuttal with rebuttal_points, recommended_action=overturn/uphold, rationale."
        ),
    },
}


# ---------------------------------------------------------------------------
# Logging helpers (strict format)
# ---------------------------------------------------------------------------
def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    done_val = str(done).lower()
    print(
        f"[STEP] step={step} action={action} reward={reward:.2f} done={done_val} error={error_val}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={rewards_str}",
        flush=True,
    )


# ---------------------------------------------------------------------------
# System prompt for the LLM agent
# ---------------------------------------------------------------------------
SYSTEM_PROMPT_TEMPLATE = textwrap.dedent("""
You are a healthcare prior authorization agent interacting with the PTPA environment.
You must gather evidence and submit a decision.

TASK: {task_id}
STRATEGY: {strategy}

PATIENT INFO (from last observation):
{patient_info}

RULES:
- Output EXACTLY ONE JSON object per turn. No markdown, no explanation.
- Format: {{"action_type": "...", "patient_id": "{patient_id}", "task_id": "{task_id}", "parameters": {{...}}}}
- For submit_decision: decision must be "approve", "deny", or "appeal". rationale must be >=20 chars.
- For submit_rebuttal (task4): include rebuttal_points (list of strings), recommended_action ("overturn"/"uphold"), rationale.
- You have {max_steps} steps. Submit by step {deadline}.
""").strip()


# ---------------------------------------------------------------------------
# JSON parser (handles multi-object LLM responses)
# ---------------------------------------------------------------------------
def parse_action_json(text: str) -> Dict[str, Any]:
    """Extract the first valid JSON object from LLM output."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Brace-counting: find first balanced {...}
    depth = 0
    start = None
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start is not None:
                try:
                    return json.loads(text[start : i + 1])
                except json.JSONDecodeError:
                    start = None

    raise ValueError(f"No valid JSON in: {text[:200]}")


# ---------------------------------------------------------------------------
# LLM call
# ---------------------------------------------------------------------------
def get_llm_action(
    client: OpenAI,
    task_id: str,
    patient_id: str,
    strategy: str,
    patient_info: str,
    observation: str,
    step_num: int,
    max_steps: int,
    history: List[str],
) -> Dict[str, Any]:
    deadline = max(1, max_steps - 2)
    system = SYSTEM_PROMPT_TEMPLATE.format(
        task_id=task_id,
        strategy=strategy,
        patient_info=patient_info,
        patient_id=patient_id,
        max_steps=max_steps,
        deadline=deadline,
    )

    remaining = max_steps - step_num
    urgency = ""
    if remaining <= 2:
        urgency = " URGENT: Submit your decision/rebuttal NOW!"
    elif remaining <= 4:
        urgency = f" WARNING: Only {remaining} steps left."

    history_block = "\n".join(history[-4:]) if history else "None"
    user = f"Step {step_num}/{max_steps}.{urgency}\n\nLAST RESULT:\n{observation}\n\nHISTORY:\n{history_block}\n\nRespond with ONE JSON action."

    try:
        resp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=TEMPERATURE,
            max_completion_tokens=MAX_COMPLETION_TOKENS,
        )
        content = (resp.choices[0].message.content or "").strip()
        return parse_action_json(content)
    except Exception as exc:
        print(f"[DEBUG] LLM error: {exc}", flush=True)
        # Fallback: submit decision to end episode
        return {
            "action_type": "submit_decision",
            "patient_id": patient_id,
            "task_id": task_id,
            "parameters": {
                "decision": "deny",
                "rationale": f"Fallback due to LLM error: {exc}",
            },
        }


# ---------------------------------------------------------------------------
# Run one task
# ---------------------------------------------------------------------------
async def run_task(env: GenericEnvClient, client: OpenAI, task_id: str) -> float:
    task_config = TASKS[task_id]
    max_steps = task_config["max_steps"]
    strategy = task_config["strategy"]

    log_start(task=task_id, env=BENCHMARK, model=MODEL_NAME)

    rewards: List[float] = []
    steps_taken = 0
    score = 0.0
    success = False

    try:
        result = await env.reset(task_id=task_id)
        obs_data = result.observation if hasattr(result, "observation") else result
        obs_text = str(obs_data) if not isinstance(obs_data, str) else obs_data

        # Extract patient_id from state
        state = await env.state()
        state_dict = dict(state) if hasattr(state, "items") else {}
        patient = state_dict.get("patient", {})
        patient_id = patient.get("patient_id", "unknown")
        patient_info = (
            f"ID: {patient_id} | Member: {patient.get('member_id','')} | "
            f"Insurer: {patient.get('insurer','')} | Plan: {patient.get('plan_id','')} | "
            f"ICD-10: {patient.get('primary_icd10','')} | CPT: {patient.get('requested_cpt','')}"
        )

        history: List[str] = []

        for step in range(1, max_steps + 1):
            action_dict = get_llm_action(
                client, task_id, patient_id, strategy,
                patient_info, obs_text, step, max_steps, history,
            )
            action_dict.setdefault("patient_id", patient_id)
            action_dict.setdefault("task_id", task_id)
            action_dict.setdefault("parameters", {})

            action_str = action_dict.get("action_type", "unknown")

            action = GenericAction(**action_dict)
            result = await env.step(action)

            # Parse result
            reward = getattr(result, "reward", 0.0) or 0.0
            done = getattr(result, "done", False) or False
            obs_data = getattr(result, "observation", "")
            error_msg = getattr(obs_data, "error", None) if hasattr(obs_data, "error") else None
            obs_text = str(obs_data)

            rewards.append(reward)
            steps_taken = step

            log_step(step=step, action=action_str, reward=reward, done=done, error=error_msg)
            history.append(f"Step {step}: {action_str} -> reward={reward:.2f}")

            if done:
                break

        # Score = grader final_score (call grader via state or separate endpoint)
        try:
            final_state = await env.state()
            state_dict = dict(final_state) if hasattr(final_state, "items") else {}
            # Use total reward as score proxy, normalized to [0,1]
            total_reward = sum(rewards)
            max_possible = max_steps * 0.4  # max reward per step
            score = min(max(total_reward / max_possible, 0.0), 1.0) if max_possible > 0 else 0.0
        except Exception:
            score = min(max(sum(rewards) / (max_steps * 0.4), 0.0), 1.0) if max_steps > 0 else 0.0

        success = score > 0.1

    except Exception as exc:
        print(f"[DEBUG] Task {task_id} error: {exc}", flush=True)
    finally:
        try:
            await env.close()
        except Exception as e:
            print(f"[DEBUG] env.close() error: {e}", flush=True)

        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)

    return score


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
async def main() -> None:
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

    scores = []
    for task_id in TASKS:
        env = await GenericEnvClient.from_docker_image(IMAGE_NAME)
        task_score = await run_task(env, client, task_id)
        scores.append(task_score)

    if scores:
        overall = sum(scores) / len(scores)
        print(f"\n[SUMMARY] overall_score={overall:.3f} tasks={len(scores)}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())

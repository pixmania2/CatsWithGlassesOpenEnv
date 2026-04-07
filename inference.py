"""
Inference Script — PTPA OpenEnv (Healthcare Prior Authorization)
================================================================
MANDATORY ENV VARS:
    API_BASE_URL   The API endpoint for the LLM
    MODEL_NAME     The model identifier to use for inference
    HF_TOKEN       Your Hugging Face / API key
    IMAGE_NAME     The Docker image name (when using from_docker_image())

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
IMAGE_NAME = os.getenv("IMAGE_NAME")
API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY") or os.getenv("OPENAI_API_KEY")

API_BASE_URL = os.getenv("API_BASE_URL") or "https://router.huggingface.co/v1"
MODEL_NAME = os.getenv("MODEL_NAME") or "Qwen/Qwen2.5-72B-Instruct"

BENCHMARK = "healthcare_prior_auth"
TEMPERATURE = 0.3
MAX_COMPLETION_TOKENS = 800

TASKS = {
    "task1_verification": {"max_steps": 10},
    "task2_mri_necessity": {"max_steps": 20},
    "task3_cgm_appeal": {"max_steps": 25},
    "task4_peer_review": {"max_steps": 30},
}

STRATEGIES = {
    "task1_verification": (
        "1) check_eligibility with member_id and insurer. "
        "2) check_cpt_coverage with cpt_code, icd10_code, insurer. "
        "3) submit_decision with approve/deny and rationale."
    ),
    "task2_mri_necessity": (
        "1) extract_pt_sessions. 2) check_red_flags. "
        "3) query_policy_database insurer=X section=prior_auth_criteria. "
        "4) submit_decision citing PT weeks vs required threshold."
    ),
    "task3_cgm_appeal": (
        "1) extract_lab_values for HbA1c, fasting_glucose, glucose_reading. "
        "2) check_step_therapy for CGM. "
        "3) query_policy_database section=exception_criteria. "
        "4) generate_appeal_letter. "
        "5) submit_decision with 'appeal' citing values and thresholds."
    ),
    "task4_peer_review": (
        "1) review_denial_letter. "
        "2) gather_counter_evidence from relevant sections. "
        "3) submit_rebuttal with rebuttal_points and recommended_action."
    ),
}


# ---------------------------------------------------------------------------
# Logging (strict stdout format)
# ---------------------------------------------------------------------------
def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    print(
        f"[STEP] step={step} action={action} reward={reward:.2f} "
        f"done={str(done).lower()} error={error if error else 'null'}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={rewards_str}",
        flush=True,
    )


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = textwrap.dedent("""
You are a healthcare prior authorization agent.

TASK: {task_id}
STRATEGY: {strategy}
PATIENT: {patient_info}

RULES:
- Output EXACTLY ONE JSON object. No markdown, no extra text.
- Format: {{"action_type": "...", "patient_id": "{patient_id}", "task_id": "{task_id}", "parameters": {{...}}}}
- submit_decision: decision="approve"/"deny"/"appeal", rationale >=20 chars citing evidence.
- submit_rebuttal (task4): rebuttal_points (list), recommended_action="overturn"/"uphold", rationale.
- You have {max_steps} steps. Submit by step {deadline}.
""").strip()


# ---------------------------------------------------------------------------
# JSON parser (handles multi-object LLM responses)
# ---------------------------------------------------------------------------
def parse_action_json(text: str) -> Dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
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
    raise ValueError(f"No valid JSON: {text[:200]}")


# ---------------------------------------------------------------------------
# LLM call
# ---------------------------------------------------------------------------
def get_llm_action(
    client: OpenAI, task_id: str, patient_id: str, patient_info: str,
    observation: str, step_num: int, max_steps: int, history: List[str],
) -> Dict[str, Any]:
    strategy = STRATEGIES.get(task_id, "Gather evidence, then submit decision.")
    deadline = max(1, max_steps - 2)

    system = SYSTEM_PROMPT.format(
        task_id=task_id, strategy=strategy, patient_info=patient_info,
        patient_id=patient_id, max_steps=max_steps, deadline=deadline,
    )

    remaining = max_steps - step_num
    urgency = " URGENT: Submit NOW!" if remaining <= 2 else (f" Only {remaining} steps left." if remaining <= 4 else "")

    history_block = "\n".join(history[-4:]) if history else "None"
    user = f"Step {step_num}/{max_steps}.{urgency}\n\nRESULT:\n{observation}\n\nHISTORY:\n{history_block}\n\nJSON action:"

    try:
        resp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=TEMPERATURE,
            max_completion_tokens=MAX_COMPLETION_TOKENS,
        )
        return parse_action_json((resp.choices[0].message.content or "").strip())
    except Exception as exc:
        print(f"[DEBUG] LLM error: {exc}", flush=True)
        return {
            "action_type": "submit_decision", "patient_id": patient_id,
            "task_id": task_id, "parameters": {"decision": "deny", "rationale": f"Fallback: {exc}"},
        }


# ---------------------------------------------------------------------------
# Run one task
# ---------------------------------------------------------------------------
async def run_task(env: GenericEnvClient, client: OpenAI, task_id: str) -> float:
    max_steps = TASKS[task_id]["max_steps"]

    log_start(task=task_id, env=BENCHMARK, model=MODEL_NAME)

    rewards: List[float] = []
    steps_taken = 0
    score = 0.0
    success = False

    try:
        result = await env.reset(task_id=task_id)
        obs_text = str(getattr(result, "observation", result))

        state = await env.state()
        state_dict = dict(state) if hasattr(state, "items") else {}
        patient = state_dict.get("patient", {})
        patient_id = patient.get("patient_id", "unknown")
        patient_info = (
            f"ID={patient_id} Member={patient.get('member_id','')} "
            f"Insurer={patient.get('insurer','')} Plan={patient.get('plan_id','')} "
            f"ICD10={patient.get('primary_icd10','')} CPT={patient.get('requested_cpt','')}"
        )

        history: List[str] = []

        for step in range(1, max_steps + 1):
            action_dict = get_llm_action(
                client, task_id, patient_id, patient_info,
                obs_text, step, max_steps, history,
            )
            action_dict.setdefault("patient_id", patient_id)
            action_dict.setdefault("task_id", task_id)
            action_dict.setdefault("parameters", {})

            action_str = action_dict.get("action_type", "unknown")
            action = GenericAction(**action_dict)
            result = await env.step(action)

            reward = getattr(result, "reward", 0.0) or 0.0
            done = getattr(result, "done", False) or False
            obs_obj = getattr(result, "observation", "")
            error_msg = getattr(obs_obj, "error", None) if hasattr(obs_obj, "error") else None
            obs_text = str(obs_obj)

            rewards.append(reward)
            steps_taken = step

            log_step(step=step, action=action_str, reward=reward, done=done, error=error_msg)
            history.append(f"Step {step}: {action_str} -> reward={reward:.2f}")

            if done:
                break

        total = sum(rewards)
        max_possible = max_steps * 0.4
        score = min(0.999, max(0.001, total / max_possible)) if max_possible > 0 else 0.001
        success = score > 0.1

    except Exception as exc:
        print(f"[DEBUG] Task {task_id} error: {exc}", flush=True)
    finally:
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
        try:
            task_score = await run_task(env, client, task_id)
        finally:
            try:
                await env.close()
            except Exception as e:
                print(f"[DEBUG] env.close() error: {e}", flush=True)
        scores.append(task_score)

    if scores:
        overall = sum(scores) / len(scores)
        print(f"\n[SUMMARY] overall_score={overall:.3f} tasks={len(scores)}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())

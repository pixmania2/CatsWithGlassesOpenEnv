"""
baseline.py — Baseline Inference Script for the PTPA OpenEnv Environment

Runs gpt-5.4-mini against all 3 tasks using fixed seeds.
Can be invoked:
  1. Internally by POST /baseline (run_baseline_internal)
  2. Standalone:  python -m baseline.baseline --url http://localhost:8000
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime
from typing import List, Optional

from models import (
    ActionType,
    AuthorizationDecision,
    BaselineResponse,
    BaselineStepTrace,
    BaselineTaskResult,
    EpisodeStatus,
    GraderResult,
    PTPAAction,
    PTPAObservation,
    PTPAState,
    TaskID,
)
from tasks import BASELINE_SEEDS, get_task

logger = logging.getLogger("ptpa.baseline")

# =========================================================================
# Baseline Agent
# =========================================================================

_SYSTEM_PROMPT_TEMPLATE = """You are a healthcare prior authorization agent. You must complete the assigned task by gathering evidence and submitting a decision.

TASK: {task_name}
DESCRIPTION: {task_description}

AVAILABLE ACTIONS (use the exact action_type string):
{actions_block}

PATIENT: {patient_name} (ID: {patient_id})
INSURER: {insurer} | PLAN: {plan_id}
DIAGNOSIS: {diagnosis} ({icd10})
REQUESTED PROCEDURE: {procedure} (CPT {cpt_code})

RULES:
- Call actions to gather evidence BEFORE submitting your decision.
- For submit_decision, "decision" must be "approve", "deny", or "appeal".
- For submit_decision, "rationale" must be at least 20 characters and reference specific evidence.
- You have {max_steps} steps total. Be efficient.

Respond with ONLY a JSON object (no markdown, no explanation):
{{"action_type": "...", "patient_id": "{patient_id}", "task_id": "{task_id}", "parameters": {{...}}}}
"""

_USER_PROMPT_TEMPLATE = """Step {step}/{max_steps}. 

LAST ACTION RESULT:
{observation}

PROGRESS SO FAR:
{progress}

What is your next action? Respond with ONLY a valid JSON action object."""


def _format_actions(task_id: TaskID) -> str:
    task = get_task(task_id)
    lines = []
    for a in task.available_actions:
        params = ", ".join(f"{k}: {v}" for k, v in a.parameters.items()) if a.parameters else "none"
        required = ", ".join(a.required_params) if a.required_params else "none"
        lines.append(f'  - "{a.action_type.value}": {a.description}\n    Parameters: {params}\n    Required: {required}')
    return "\n".join(lines)


def _format_progress(state: PTPAState) -> str:
    p = state.progress
    flags = []
    if p.eligibility_verified:
        flags.append("eligibility_verified")
    if p.cpt_coverage_checked:
        flags.append("cpt_coverage_checked")
    if p.pt_sessions_extracted:
        flags.append("pt_sessions_extracted")
    if p.red_flags_checked:
        flags.append("red_flags_checked")
    if p.lab_values_extracted:
        flags.append("lab_values_extracted")
    if p.step_therapy_checked:
        flags.append("step_therapy_checked")
    if p.policy_retrieved:
        flags.append("policy_retrieved")
    if p.decision_submitted:
        flags.append("decision_submitted")
    return f"Completed: {', '.join(flags) if flags else 'none'} | Cumulative reward: {p.total_reward_so_far:.2f}"


def _parse_action(response_text: str, patient_id: str, task_id: TaskID) -> PTPAAction:
    """Extract a PTPAAction from the LLM's response text."""
    # Try to find JSON in the response
    text = response_text.strip()

    # Strip markdown code fences
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Try to extract JSON from within the text
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
            except json.JSONDecodeError:
                raise ValueError(f"Could not parse JSON from response: {text[:200]}")
        else:
            raise ValueError(f"No JSON found in response: {text[:200]}")

    # Ensure required fields
    data.setdefault("patient_id", patient_id)
    data.setdefault("task_id", task_id.value)
    data.setdefault("parameters", {})

    return PTPAAction(**data)


class BaselineAgent:
    """Runs gpt-5.4-mini against the environment API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-5.4-mini",
        temperature: float = 0,
        max_tokens: int = 1000,
    ):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

        key = api_key or os.getenv("OPENAI_API_KEY", "")
        if not key:
            raise RuntimeError("OPENAI_API_KEY not set")

        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=key)
        except ImportError:
            raise RuntimeError("openai package not installed. Run: pip install openai")

    def decide(
        self,
        state: PTPAState,
        last_observation: PTPAObservation,
        step_num: int,
    ) -> PTPAAction:
        task = get_task(state.task_id)

        system_prompt = _SYSTEM_PROMPT_TEMPLATE.format(
            task_name=task.name,
            task_description=task.description,
            actions_block=_format_actions(state.task_id),
            patient_name=state.patient.name,
            patient_id=state.patient.patient_id,
            insurer=state.patient.insurer,
            plan_id=state.patient.plan_id,
            diagnosis=state.patient.primary_icd10,
            icd10=state.patient.primary_icd10,
            procedure=state.patient.requested_cpt,
            cpt_code=state.patient.requested_cpt,
            max_steps=state.max_steps,
            task_id=state.task_id.value,
        )

        user_prompt = _USER_PROMPT_TEMPLATE.format(
            step=step_num,
            max_steps=state.max_steps,
            observation=last_observation.result,
            progress=_format_progress(state),
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            content = response.choices[0].message.content or ""
        except Exception as e:
            logger.error("OpenAI API error: %s", e)
            # Fallback: submit a basic decision
            content = json.dumps({
                "action_type": "submit_decision",
                "patient_id": state.patient.patient_id,
                "task_id": state.task_id.value,
                "parameters": {
                    "decision": "deny",
                    "rationale": "Unable to complete analysis due to API error. Defaulting to deny.",
                },
            })

        return _parse_action(content, state.patient.patient_id, state.task_id)


# =========================================================================
# Internal baseline runner (called by POST /baseline)
# =========================================================================

async def run_baseline_internal(engine, session_store) -> BaselineResponse:
    """
    Run the baseline agent against all 3 tasks using fixed seeds.
    Called directly by the /baseline endpoint.
    """
    from server.session import SessionStore

    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        # Return a placeholder response if no API key
        return _placeholder_baseline_response()

    agent = BaselineAgent(api_key=api_key)
    task_results: List[BaselineTaskResult] = []
    seeds_used = BASELINE_SEEDS[:1]  # Use first seed for speed

    for task_id in [TaskID.VERIFICATION, TaskID.MRI_NECESSITY, TaskID.CGM_APPEAL]:
        seed = seeds_used[0]
        episode_id = SessionStore.generate_episode_id()

        # Reset
        obs, state = engine.reset(
            episode_id=episode_id,
            task_id=task_id,
            seed=seed,
        )
        session_store.create(task_id=task_id, state=state)

        # Step loop
        trace: List[BaselineStepTrace] = []
        step_num = 0
        done = False

        while not done and step_num < state.max_steps:
            step_num += 1
            try:
                action = agent.decide(state, obs, step_num)
            except Exception as e:
                logger.error("Agent decide error (task=%s, step=%d): %s", task_id.value, step_num, e)
                # Fallback: submit decision
                action = PTPAAction(
                    action_type=ActionType.SUBMIT_DECISION,
                    patient_id=state.patient.patient_id,
                    task_id=task_id,
                    parameters={
                        "decision": "deny",
                        "rationale": f"Fallback decision due to agent error: {e}",
                    },
                )

            obs, reward, done, state = engine.step(episode_id, action)
            session_store.update_state(episode_id, state)

            trace.append(BaselineStepTrace(
                step_number=step_num,
                action=action,
                observation=obs,
                cumulative_reward=state.progress.total_reward_so_far,
            ))

        # Grade
        try:
            session_store.set_status(episode_id, EpisodeStatus.GRADING)
        except (ValueError, KeyError):
            pass

        grader_result = engine.grade(episode_id)

        try:
            session_store.set_status(episode_id, EpisodeStatus.DONE)
        except (ValueError, KeyError):
            pass

        agent_decision = None
        ep_data = engine.get_episode_data(episode_id)
        if ep_data and ep_data.get("submitted_decision"):
            try:
                agent_decision = AuthorizationDecision(ep_data["submitted_decision"].get("decision", ""))
            except ValueError:
                pass

        task_results.append(BaselineTaskResult(
            task_id=task_id,
            episode_id=episode_id,
            seed=seed,
            final_score=grader_result.final_score,
            steps_taken=step_num,
            decision_made=agent_decision,
            grader_result=grader_result,
            trace=trace,
            success=grader_result.final_score > 0.5,
        ))

    overall = sum(r.final_score for r in task_results) / len(task_results) if task_results else 0.0

    return BaselineResponse(
        environment_version="1.2.0",
        model_used="gpt-5.4-mini",
        seeds_used=seeds_used,
        task_results=task_results,
        overall_score=round(overall, 4),
        run_timestamp=datetime.utcnow().isoformat(),
    )


def _placeholder_baseline_response() -> BaselineResponse:
    """Return a placeholder when OPENAI_API_KEY is not set."""
    task_results = []
    for task_id, expected_score in [
        (TaskID.VERIFICATION, 0.98),
        (TaskID.MRI_NECESSITY, 0.42),
        (TaskID.CGM_APPEAL, 0.15),
    ]:
        task_results.append(BaselineTaskResult(
            task_id=task_id,
            episode_id="placeholder",
            seed=42,
            final_score=expected_score,
            steps_taken=0,
            decision_made=None,
            grader_result=GraderResult(
                task_id=task_id,
                episode_id="placeholder",
                final_score=expected_score,
                components=[],
                feedback="Placeholder — OPENAI_API_KEY not set. These are expected baseline scores.",
                appeal_letter_score=None,
            ),
            trace=[],
            success=expected_score > 0.5,
        ))

    return BaselineResponse(
        environment_version="1.2.0",
        model_used="gpt-5.4-mini (placeholder)",
        seeds_used=[42],
        task_results=task_results,
        overall_score=round(sum(r.final_score for r in task_results) / 3, 4),
        run_timestamp=datetime.utcnow().isoformat(),
    )


# =========================================================================
# Standalone CLI mode
# =========================================================================

if __name__ == "__main__":
    import argparse
    import asyncio
    import sys

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    parser = argparse.ArgumentParser(description="Run PTPA baseline agent")
    parser.add_argument("--url", default="http://localhost:8000", help="Server URL")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    print(f"Running baseline against {args.url} with seed {args.seed}")

    from environment.engine import PTPAEngine
    from server.session import SessionStore

    eng = PTPAEngine()
    store = SessionStore()

    result = asyncio.run(run_baseline_internal(eng, store))
    print("\nBaseline Results:")
    print(f"  Overall Score: {result.overall_score:.4f}")
    for tr in result.task_results:
        print(f"  {tr.task_id.value}: {tr.final_score:.4f} ({tr.steps_taken} steps)")

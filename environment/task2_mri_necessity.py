"""
task2_mri_necessity.py — Task 2 Grader: Medical Necessity Review (MRI)

Grader components (weights):
  - evidence_extraction      (35%) — Did the agent extract PT session data?
  - policy_duration_logic    (30%) — Did the agent apply the correct duration threshold?
  - red_flag_recognition     (20%) — Did the agent check for clinical red flags?
  - final_decision_accuracy  (15%) — Was the final decision correct?
"""

from __future__ import annotations

from models import (
    AuthorizationDecision,
    EpisodeProgress,
    GraderComponentScore,
    GraderResult,
    TaskID,
)
from tasks import TASK2_ANSWER_KEYS


def grade(
    patient_id: str,
    submitted: dict,
    progress: EpisodeProgress,
    episode_id: str,
) -> GraderResult:
    """Score a completed Task 2 episode."""
    key = TASK2_ANSWER_KEYS.get(patient_id, {})
    correct_decision = key.get("decision")
    agent_decision_str = submitted.get("decision", "")

    try:
        agent_decision = AuthorizationDecision(agent_decision_str)
        decision_correct = agent_decision == correct_decision
    except ValueError:
        agent_decision = None
        decision_correct = False

    # Evidence extraction (35%)
    ev_score = 1.0 if progress.pt_sessions_extracted else 0.0

    # Policy duration logic (30%)
    dur_score = 0.0
    if progress.policy_retrieved:
        dur_score = 0.5
    if decision_correct:
        dur_score = 1.0

    # Red flag recognition (20%)
    rf_score = 1.0 if progress.red_flags_checked else 0.0

    # Final decision accuracy (15%)
    dec_score = 1.0 if decision_correct else 0.0

    components = [
        GraderComponentScore(
            component_name="evidence_extraction", weight=0.35,
            score=ev_score, weighted_score=round(0.35 * ev_score, 4),
            passed=ev_score > 0.5,
            feedback=f"PT sessions extracted: {progress.pt_sessions_extracted}",
        ),
        GraderComponentScore(
            component_name="policy_duration_logic", weight=0.30,
            score=dur_score, weighted_score=round(0.30 * dur_score, 4),
            passed=dur_score > 0.5,
            feedback=f"Duration logic score: {dur_score}",
        ),
        GraderComponentScore(
            component_name="red_flag_recognition", weight=0.20,
            score=rf_score, weighted_score=round(0.20 * rf_score, 4),
            passed=rf_score > 0.5,
            feedback=f"Red flags checked: {progress.red_flags_checked}",
        ),
        GraderComponentScore(
            component_name="final_decision_accuracy", weight=0.15,
            score=dec_score, weighted_score=round(0.15 * dec_score, 4),
            passed=decision_correct,
            feedback=f"Decision correct: {decision_correct}",
        ),
    ]
    final = sum(c.weighted_score for c in components)

    return GraderResult(
        task_id=TaskID.MRI_NECESSITY,
        episode_id=episode_id,
        final_score=round(final, 4),
        components=components,
        decision_made=agent_decision,
        decision_correct=decision_correct,
        feedback=(
            f"Decision: {agent_decision_str} | "
            f"Correct: {correct_decision.value if correct_decision else 'N/A'} | "
            f"Score: {final:.2f}"
        ),
    )

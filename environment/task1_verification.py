"""
task1_verification.py — Task 1 Grader: Insurance Verification & Eligibility

Grader components (weights):
  - eligibility_status   (40%) — Did the agent verify active/inactive?
  - procedure_coverage   (40%) — Did the agent check CPT coverage?
  - policy_rationale     (20%) — Did the rationale cite the correct policy section?
"""

from __future__ import annotations

from models import (
    AuthorizationDecision,
    EpisodeProgress,
    GraderComponentScore,
    GraderResult,
    TaskID,
)
from tasks import TASK1_ANSWER_KEYS


def grade(
    patient_id: str,
    submitted: dict,
    progress: EpisodeProgress,
    episode_id: str,
) -> GraderResult:
    """Score a completed Task 1 episode."""
    key = TASK1_ANSWER_KEYS.get(patient_id, {})
    correct_decision = key.get("decision")
    agent_decision_str = submitted.get("decision", "")

    try:
        agent_decision = AuthorizationDecision(agent_decision_str)
        decision_correct = agent_decision == correct_decision
    except ValueError:
        agent_decision = None
        decision_correct = False

    # Eligibility (40%)
    elig_score = 1.0 if progress.eligibility_verified else 0.0
    if not decision_correct:
        elig_score *= 0.5

    # Procedure coverage (40%)
    cov_score = 1.0 if progress.cpt_coverage_checked else 0.0
    if not decision_correct:
        cov_score *= 0.5

    # Policy rationale (20%)
    rationale = submitted.get("rationale", "")
    correct_section = key.get("correct_policy_section", "")
    if correct_section and correct_section.lower() in rationale.lower():
        rat_score = 1.0
    elif key.get("insurer", "") in rationale.lower():
        rat_score = 0.5
    else:
        rat_score = 0.0

    components = [
        GraderComponentScore(
            component_name="eligibility_status", weight=0.40,
            score=elig_score, weighted_score=round(0.40 * elig_score, 4),
            passed=elig_score > 0.5,
            feedback=f"Eligibility verified: {progress.eligibility_verified}",
        ),
        GraderComponentScore(
            component_name="procedure_coverage", weight=0.40,
            score=cov_score, weighted_score=round(0.40 * cov_score, 4),
            passed=cov_score > 0.5,
            feedback=f"CPT coverage checked: {progress.cpt_coverage_checked}",
        ),
        GraderComponentScore(
            component_name="policy_rationale", weight=0.20,
            score=rat_score, weighted_score=round(0.20 * rat_score, 4),
            passed=rat_score > 0.5,
            feedback=f"Rationale quality: {rat_score}",
        ),
    ]
    final = sum(c.weighted_score for c in components)

    return GraderResult(
        task_id=TaskID.VERIFICATION,
        episode_id=episode_id,
        final_score=min(0.999, max(0.001, round(final, 4))),
        components=components,
        decision_made=agent_decision,
        decision_correct=decision_correct,
        feedback=(
            f"Decision: {agent_decision_str} | "
            f"Correct: {correct_decision.value if correct_decision else 'N/A'} | "
            f"Score: {final:.2f}"
        ),
    )

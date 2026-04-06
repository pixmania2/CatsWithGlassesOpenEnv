"""
task2_mri_necessity.py — Task 2 Grader: Medical Necessity Review (MRI)

Grader components (weights):
  - evidence_extraction      (35%) — Did the agent extract PT session data?
  - policy_duration_logic    (30%) — Did the agent compute PT duration and compare to threshold?
  - red_flag_recognition     (20%) — Did the agent check for clinical red flags?
  - final_decision_accuracy  (15%) — Was the final decision correct?
"""

from __future__ import annotations

import re

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
    """Score a completed Task 2 episode with smarter duration verification."""
    key = TASK2_ANSWER_KEYS.get(patient_id, {})
    correct_decision = key.get("decision")
    agent_decision_str = submitted.get("decision", "")

    try:
        agent_decision = AuthorizationDecision(agent_decision_str)
        decision_correct = agent_decision == correct_decision
    except ValueError:
        agent_decision = None
        decision_correct = False

    # ---- Evidence extraction (35%) ----
    ev_score = 0.0
    if progress.pt_sessions_extracted:
        ev_score = 0.7
        # Bonus: did the agent also query imaging or pharmacy history?
        queried = set(progress.queried_sections)
        if queried & {"imaging_history", "physical_exam", "progress_notes"}:
            ev_score = 1.0

    # ---- Policy duration logic (30%) — SMARTER ----
    dur_score = 0.0
    rationale = submitted.get("rationale", "")
    documented_weeks = key.get("documented_pt_weeks", 0)
    required_weeks = key.get("required_pt_weeks", 6)
    has_red_flag = key.get("red_flag_present", False)

    if progress.policy_retrieved:
        dur_score = 0.3  # Retrieved the policy

    # Check if the agent cited the correct number of weeks in rationale
    week_numbers = re.findall(r"(\d+(?:\.\d+)?)\s*weeks?", rationale.lower())
    mentioned_weeks = [float(w) for w in week_numbers]

    if mentioned_weeks:
        dur_score = max(dur_score, 0.5)  # At least mentioned weeks

        # Check if agent cited the correct documented PT duration
        if any(abs(w - documented_weeks) < 0.5 for w in mentioned_weeks):
            dur_score = max(dur_score, 0.7)

        # Check if agent cited the correct required threshold
        if any(abs(w - required_weeks) < 0.5 for w in mentioned_weeks):
            dur_score = max(dur_score, 0.8)

        # Both correct = full score
        has_documented = any(abs(w - documented_weeks) < 0.5 for w in mentioned_weeks)
        has_required = any(abs(w - required_weeks) < 0.5 for w in mentioned_weeks)
        if has_documented and has_required:
            dur_score = 1.0

    # Red flag bypass overrides: if agent correctly identified red flag
    if has_red_flag:
        red_flag_type = key.get("red_flag_type", "").lower()
        if red_flag_type and any(kw in rationale.lower() for kw in red_flag_type.split()):
            dur_score = 1.0  # Correctly identified bypass

    # Correct decision gives at least partial credit
    if decision_correct and dur_score < 0.5:
        dur_score = 0.5

    # ---- Red flag recognition (20%) ----
    rf_score = 0.0
    if progress.red_flags_checked:
        rf_score = 0.7
        # Bonus: did the rationale correctly reference the red flag (or lack thereof)?
        if has_red_flag:
            red_flag_type = key.get("red_flag_type", "").lower()
            if red_flag_type and any(kw in rationale.lower() for kw in red_flag_type.split()):
                rf_score = 1.0
        else:
            # Correctly identified no red flags
            if "no red flag" in rationale.lower() or "no clinical urgency" in rationale.lower():
                rf_score = 1.0
            elif decision_correct:
                rf_score = 0.85  # Got the right answer even without explicit mention

    # ---- Final decision accuracy (15%) ----
    dec_score = 1.0 if decision_correct else 0.0

    components = [
        GraderComponentScore(
            component_name="evidence_extraction", weight=0.35,
            score=ev_score, weighted_score=round(0.35 * ev_score, 4),
            passed=ev_score > 0.5,
            feedback=f"PT sessions extracted: {progress.pt_sessions_extracted}, queried sections: {progress.queried_sections}",
        ),
        GraderComponentScore(
            component_name="policy_duration_logic", weight=0.30,
            score=dur_score, weighted_score=round(0.30 * dur_score, 4),
            passed=dur_score > 0.5,
            feedback=f"Duration logic: documented={documented_weeks}w, required={required_weeks}w, mentioned={mentioned_weeks}, score={dur_score}",
        ),
        GraderComponentScore(
            component_name="red_flag_recognition", weight=0.20,
            score=rf_score, weighted_score=round(0.20 * rf_score, 4),
            passed=rf_score > 0.5,
            feedback=f"Red flags checked: {progress.red_flags_checked}, present: {has_red_flag}",
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

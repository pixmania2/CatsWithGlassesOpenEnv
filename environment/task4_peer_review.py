"""
task4_peer_review.py — Task 4 Grader: Peer-to-Peer Review Denial Rebuttal

Grader components (weights):
  - denial_analysis       (25%) — Did the agent read and identify the denial reason?
  - evidence_gathering    (30%) — Did the agent gather relevant counter-evidence?
  - rebuttal_quality      (25%) — Quality of the structured rebuttal arguments.
  - outcome_accuracy      (20%) — Did the agent correctly determine overturn/uphold?
"""

from __future__ import annotations

from models import (
    AuthorizationDecision,
    EpisodeProgress,
    GraderComponentScore,
    GraderResult,
    TaskID,
)
from tasks import TASK4_ANSWER_KEYS


def grade(
    patient_id: str,
    submitted: dict,
    progress: EpisodeProgress,
    episode_data: dict,
    episode_id: str,
) -> GraderResult:
    """Score a completed Task 4 episode."""
    key = TASK4_ANSWER_KEYS.get(patient_id, {})
    expected_outcome = key.get("expected_outcome", "")
    agent_outcome = submitted.get("recommended_action", submitted.get("decision", ""))

    # Normalize: submit_decision with "appeal" = "overturn", "deny" = "uphold"
    if agent_outcome == "appeal":
        agent_outcome = "overturn"
    elif agent_outcome == "deny":
        agent_outcome = "uphold"

    outcome_correct = agent_outcome == expected_outcome

    # Map to AuthorizationDecision for the result
    try:
        decision_enum = AuthorizationDecision.APPEAL if agent_outcome == "overturn" else AuthorizationDecision.DENY
    except ValueError:
        decision_enum = None

    # --- Denial analysis (25%) ---
    denial_score = 0.0
    if progress.policy_retrieved:
        denial_score = 0.5  # Read the denial letter
        # Check if rationale mentions the denial reason
        rationale = submitted.get("rationale", "")
        denial_reason = key.get("denial_reason", "")
        if denial_reason:
            keywords = denial_reason.replace("_", " ").split()
            matches = sum(1 for kw in keywords if kw.lower() in rationale.lower())
            if matches >= len(keywords) * 0.5:
                denial_score = 1.0
            elif matches > 0:
                denial_score = 0.75

    # --- Evidence gathering (30%) ---
    evidence_score = 0.0
    checks = 0
    total = 4
    if progress.pt_sessions_extracted:
        checks += 1
    if progress.lab_values_extracted:
        checks += 1
    if progress.red_flags_checked:
        checks += 1
    if len(progress.queried_sections) >= 2:
        checks += 1
    evidence_score = checks / total

    # Bonus for finding the key evidence
    key_evidence = key.get("key_evidence", "")
    rationale = submitted.get("rationale", "")
    rebuttal_points = submitted.get("rebuttal_points", [])
    all_text = rationale + " ".join(rebuttal_points if isinstance(rebuttal_points, list) else [])

    if key_evidence:
        # Check if key words from the evidence appear in the rebuttal
        evidence_words = [w for w in key_evidence.split() if len(w) > 3]
        matches = sum(1 for w in evidence_words if w.lower() in all_text.lower())
        if matches >= len(evidence_words) * 0.4:
            evidence_score = min(1.0, evidence_score + 0.3)

    # --- Rebuttal quality (25%) ---
    rebuttal_score = 0.0
    points = submitted.get("rebuttal_points", [])
    if isinstance(points, list) and len(points) > 0:
        # Points exist
        rebuttal_score = 0.3
        # Check quality: each point should be substantive
        substantive = sum(1 for p in points if len(str(p)) > 30)
        if substantive >= 2:
            rebuttal_score = 0.6
        if substantive >= 3:
            rebuttal_score = 0.8
        # Check if points address the denial reason
        if denial_reason and any(
            denial_reason.replace("_", " ").lower() in str(p).lower()
            for p in points
        ):
            rebuttal_score = min(1.0, rebuttal_score + 0.2)

    # --- Outcome accuracy (20%) ---
    outcome_score = 1.0 if outcome_correct else 0.0

    components = [
        GraderComponentScore(
            component_name="denial_analysis", weight=0.25,
            score=denial_score, weighted_score=round(0.25 * denial_score, 4),
            passed=denial_score > 0.5,
            feedback=f"Denial letter analyzed: {progress.policy_retrieved}",
        ),
        GraderComponentScore(
            component_name="evidence_gathering", weight=0.30,
            score=evidence_score, weighted_score=round(0.30 * evidence_score, 4),
            passed=evidence_score > 0.5,
            feedback=f"Evidence gathering score: {evidence_score:.2f}",
        ),
        GraderComponentScore(
            component_name="rebuttal_quality", weight=0.25,
            score=rebuttal_score, weighted_score=round(0.25 * rebuttal_score, 4),
            passed=rebuttal_score > 0.5,
            feedback=f"Rebuttal quality: {rebuttal_score:.2f} ({len(points)} points)",
        ),
        GraderComponentScore(
            component_name="outcome_accuracy", weight=0.20,
            score=outcome_score, weighted_score=round(0.20 * outcome_score, 4),
            passed=outcome_correct,
            feedback=f"Outcome: {agent_outcome} (expected: {expected_outcome})",
        ),
    ]
    final = sum(c.weighted_score for c in components)

    return GraderResult(
        task_id=TaskID.PEER_REVIEW,
        episode_id=episode_id,
        final_score=min(0.999, max(0.001, round(final, 4))),
        components=components,
        decision_made=decision_enum,
        decision_correct=outcome_correct,
        feedback=(
            f"Outcome: {agent_outcome} | "
            f"Expected: {expected_outcome} | "
            f"Score: {final:.2f}"
        ),
    )

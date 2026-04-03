"""
task3_cgm_appeal.py — Task 3 Grader: CGM Exception Appeal

Grader components (weights):
  - metric_identification    (40%) — Did the agent find the qualifying lab value?
  - rationale_mapping        (30%) — Did the rationale cite the correct exception clause?
  - appeal_letter_quality    (30%) — LLM-as-judge score on the appeal letter quality.

The appeal_letter_quality component uses an actual OpenAI gpt-4o-mini call
when OPENAI_API_KEY is available, falling back to keyword heuristics otherwise.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict

from models import (
    AuthorizationDecision,
    EpisodeProgress,
    GraderComponentScore,
    GraderResult,
    TaskID,
)
from tasks import APPEAL_LETTER_JUDGE_RUBRIC, CGM_EXCEPTION_THRESHOLDS, TASK3_ANSWER_KEYS

logger = logging.getLogger("ptpa.grader.task3")


# =========================================================================
# LLM-as-Judge for Appeal Letter
# =========================================================================

def _llm_judge_appeal_letter(letter: str) -> float:
    """
    Call gpt-4o-mini to score the appeal letter using the rubric from tasks.py.
    Returns a float 0.0–1.0. Falls back to keyword heuristics on failure.
    """
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key or not letter:
        return _keyword_judge_appeal_letter(letter, {}, "")

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)

        prompt = APPEAL_LETTER_JUDGE_RUBRIC.replace("{letter_text}", letter)

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
        content = response.choices[0].message.content or ""

        # Strip markdown fences
        content = content.strip()
        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?\s*", "", content)
            content = re.sub(r"\s*```$", "", content)

        result = json.loads(content)
        score = float(result.get("total_score", 0.0))
        feedback = result.get("feedback", "")
        logger.info("LLM judge score: %.2f — %s", score, feedback)
        return max(0.0, min(1.0, score))

    except Exception as e:
        logger.warning("LLM judge failed, falling back to keywords: %s", e)
        return _keyword_judge_appeal_letter(letter, {}, "")


def _keyword_judge_appeal_letter(
    letter: str,
    patient_data: Dict[str, Any],
    correct_clause: str,
) -> float:
    """Keyword-based fallback for appeal letter scoring."""
    if not letter:
        return 0.0

    checks = 0

    # A. ICD codes present
    icd_patterns = [r"E11\.\d+", r"E10\.\d+", r"ICD-10"]
    if any(re.search(p, letter) for p in icd_patterns):
        checks += 1
    elif patient_data:
        for dx in patient_data.get("diagnosis_codes", []):
            if dx.get("code", "") in letter:
                checks += 1
                break

    # B. Lab values cited
    lab_patterns = [r"\d+\.?\d*\s*mg/dL", r"\d+\.?\d*\s*%", r"HbA1c", r"glucose"]
    if sum(1 for p in lab_patterns if re.search(p, letter, re.IGNORECASE)) >= 2:
        checks += 1
    elif patient_data:
        for lab in patient_data.get("lab_results", []):
            if str(lab.get("value", "")) in letter:
                checks += 1
                break

    # C. Exception clause referenced
    if correct_clause and any(
        word.lower() in letter.lower()
        for word in correct_clause.split()[:3]
        if len(word) > 3
    ):
        checks += 1
    elif any(kw in letter.lower() for kw in ["exception", "lcd", "cpb", "coverage exception"]):
        checks += 1

    # D. Professional format
    if ("dear" in letter.lower() or "to:" in letter.lower()) and (
        "respectfully" in letter.lower() or "sincerely" in letter.lower()
    ):
        checks += 1

    # E. Physician attestation
    if "npi" in letter.lower() or ("dr." in letter.lower() and "respectfully" in letter.lower()):
        checks += 1

    return checks / 5.0


# =========================================================================
# Clinical Threshold Helpers
# =========================================================================

def check_dawn_phenomenon(lab_results: list) -> dict:
    """Check if fasting glucose > 200 mg/dL (Dawn Phenomenon exception)."""
    threshold = CGM_EXCEPTION_THRESHOLDS["dawn_phenomenon_fasting_glucose_mg_dl"]
    fasting = [
        lab for lab in lab_results
        if (lab.get("test_name") or lab.get("test", "")) == "fasting_glucose"
    ]
    if not fasting:
        return {"met": False, "max_value": None, "threshold": threshold}

    max_val = max(lab.get("value", 0) for lab in fasting)
    return {"met": max_val > threshold, "max_value": max_val, "threshold": threshold}


def check_hypoglycemic_unawareness(lab_results: list) -> dict:
    """Check if glucose < 54 mg/dL (Hypoglycemic Unawareness exception)."""
    threshold = CGM_EXCEPTION_THRESHOLDS["hypoglycemic_unawareness_threshold_mg_dl"]
    readings = [
        lab for lab in lab_results
        if (lab.get("test_name") or lab.get("test", "")) == "glucose_reading"
    ]
    if not readings:
        return {"met": False, "min_value": None, "threshold": threshold}

    min_val = min(lab.get("value", 999) for lab in readings)
    return {"met": min_val < threshold, "min_value": min_val, "threshold": threshold}


def check_glycemic_variability(lab_results: list) -> dict:
    """Check if HbA1c > 7.0% (Glycemic Variability exception)."""
    threshold = CGM_EXCEPTION_THRESHOLDS["hba1c_target_failure_percent"]
    hba1c = [
        lab for lab in lab_results
        if (lab.get("test_name") or lab.get("test", "")) == "HbA1c"
    ]
    if not hba1c:
        return {"met": False, "value": None, "threshold": threshold}

    latest = max(hba1c, key=lambda x: x.get("date", ""))
    val = latest.get("value", 0)
    return {"met": val > threshold, "value": val, "threshold": threshold}


# =========================================================================
# Task 3 Grader
# =========================================================================

def grade(
    patient_id: str,
    submitted: dict,
    progress: EpisodeProgress,
    episode_data: dict,
    episode_id: str,
) -> GraderResult:
    """Score a completed Task 3 episode. Uses LLM-as-judge for appeal letter."""
    key = TASK3_ANSWER_KEYS.get(patient_id, {})
    correct_decision = key.get("decision")
    agent_decision_str = submitted.get("decision", "")

    try:
        agent_decision = AuthorizationDecision(agent_decision_str)
        decision_correct = agent_decision == correct_decision
    except ValueError:
        agent_decision = None
        decision_correct = False

    # --- Metric identification (40%) ---
    metric_score = 0.0
    if progress.lab_values_extracted:
        metric_score = 0.5
        rationale = submitted.get("rationale", "")
        qv = key.get("qualifying_value")
        if qv is not None and str(int(qv)) in rationale:
            metric_score = 1.0
        elif key.get("exception_type") and key["exception_type"].replace("_", " ") in rationale.lower():
            metric_score = 0.75

    # --- Rationale mapping (30%) ---
    rat_score = 0.0
    correct_clause = key.get("correct_exception_clause", "") or ""
    rationale = submitted.get("rationale", "")
    policy_cited = submitted.get("policy_section_cited", "") or ""
    if correct_clause:
        if correct_clause.lower() in rationale.lower() or correct_clause.lower() in policy_cited.lower():
            rat_score = 1.0
        elif key.get("insurer", "") in rationale.lower() and "exception" in rationale.lower():
            rat_score = 0.5

    # --- Appeal letter quality (30%) — LLM-as-judge ---
    letter = episode_data.get("appeal_letter", "")
    patient_data = episode_data.get("patient_data", {})

    # Try LLM judge first, fall back to keywords
    letter_score = _llm_judge_appeal_letter(letter)
    if letter_score == 0.0 and letter:
        # LLM returned 0 or failed — use keyword fallback with patient context
        letter_score = _keyword_judge_appeal_letter(letter, patient_data, correct_clause)

    components = [
        GraderComponentScore(
            component_name="metric_identification", weight=0.40,
            score=metric_score, weighted_score=round(0.40 * metric_score, 4),
            passed=metric_score > 0.5,
            feedback=f"Metric identification: {metric_score}",
        ),
        GraderComponentScore(
            component_name="rationale_mapping", weight=0.30,
            score=rat_score, weighted_score=round(0.30 * rat_score, 4),
            passed=rat_score > 0.5,
            feedback=f"Rationale mapping: {rat_score}",
        ),
        GraderComponentScore(
            component_name="appeal_letter_quality", weight=0.30,
            score=letter_score, weighted_score=round(0.30 * letter_score, 4),
            passed=letter_score > 0.5,
            feedback=f"Appeal letter score: {letter_score:.2f} ({'LLM judge' if os.getenv('OPENAI_API_KEY') else 'keyword fallback'})",
        ),
    ]
    final = sum(c.weighted_score for c in components)

    return GraderResult(
        task_id=TaskID.CGM_APPEAL,
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
        appeal_letter_score=round(letter_score, 4),
    )

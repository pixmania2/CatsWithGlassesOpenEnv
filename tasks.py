"""
tasks.py — Task Registry for the PTPA OpenEnv Environment

Patient Triage & Prior Authorization (PTPA) Environment
=========================================================
This file is the authoritative source for:
  - All task definitions and metadata (TaskInfo objects for GET /tasks)
  - Grader specifications per task (component weights and scoring logic)
  - Reward signal configuration (partial progress values, penalties)
  - Patient scenario routing per task
  - Ground-truth answer keys for Tasks 1 & 2 (Task 3 uses LLM-as-judge)

Both Person A (task logic / graders) and Person B (server / baseline) import from here.
"""

from __future__ import annotations

from typing import Dict, List
from models import (
    TaskID, TaskInfo, Difficulty, ActionType, ActionSchema,
    GraderComponentSpec, AuthorizationDecision
)


# ===========================================================================
# REWARD SIGNAL CONFIGURATION
# (Single source of truth — imported by rewards.py)
# ===========================================================================

REWARD_SIGNALS: Dict[str, float] = {
    # Positive partial progress signals
    "discovery_reward"  : +0.10,   # Successfully retrieved a relevant policy section
    "evidence_reward"   : +0.20,   # Extracted a lab value or PT note critical to the case
    "logic_reward"      : +0.30,   # Correctly identified a red flag or exception criteria
    "success_reward"    : +0.40,   # Submitted the correct Approve/Deny/Appeal determination

    # Negative signals (penalties)
    "loop_penalty"      : -0.10,   # Same query repeated without new results (loop detection)
    "destructive_penalty": -0.50,  # Accessing unauthorized records OR submitting false info

    # Neutral
    "no_reward"         : 0.00,
}

# Max steps before forced episode termination
MAX_STEPS: Dict[TaskID, int] = {
    TaskID.VERIFICATION  : 10,
    TaskID.MRI_NECESSITY : 20,
    TaskID.CGM_APPEAL    : 25,
}

# Seeds used by the baseline inference script (fixed for reproducibility)
BASELINE_SEEDS: List[int] = [42, 137, 999]


# ===========================================================================
# TASK 1: INSURANCE VERIFICATION & ELIGIBILITY (Easy)
# ===========================================================================

TASK1_GRADER_COMPONENTS: List[GraderComponentSpec] = [
    GraderComponentSpec(
        component_name="eligibility_status",
        weight=0.40,
        description=(
            "Agent correctly identifies whether the member's insurance policy is active. "
            "Full score (1.0) if correct, zero otherwise. "
            "Checks: member_id exists, plan active_status == True, no termination date in past."
        ),
    ),
    GraderComponentSpec(
        component_name="procedure_coverage",
        weight=0.40,
        description=(
            "Agent correctly identifies whether the requested CPT code is in the plan's "
            "Covered Services list for the given ICD-10 diagnosis. "
            "Full score (1.0) if correct. Zero if wrong. "
            "Partial (0.5) if agent identifies coverage but cites wrong plan tier."
        ),
    ),
    GraderComponentSpec(
        component_name="policy_rationale",
        weight=0.20,
        description=(
            "Agent cites the correct policy section ID in its rationale. "
            "1.0 = exact section cited (e.g. 'Section 4.2 Covered Services'). "
            "0.5 = general reference to correct insurer policy but no section ID. "
            "0.0 = no citation or wrong insurer."
        ),
    ),
]

TASK1_AVAILABLE_ACTIONS: List[ActionSchema] = [
    ActionSchema(
        action_type=ActionType.CHECK_ELIGIBILITY,
        description="Verify the patient's member ID and check if the insurance plan is currently active.",
        parameters={
            "member_id": "str — Insurance member ID from the patient record",
            "insurer"  : "str — Insurer name: 'aetna', 'cigna', 'cms', 'united'",
        },
        required_params=["member_id", "insurer"],
    ),
    ActionSchema(
        action_type=ActionType.CHECK_CPT_COVERAGE,
        description="Look up whether a CPT procedure code is covered under the patient's plan for a given diagnosis.",
        parameters={
            "cpt_code"  : "str — Procedure code e.g. '73721' (knee MRI), '99213' (office visit)",
            "icd10_code": "str — Diagnosis code e.g. 'M17.11' (primary osteoarthritis, right knee)",
            "insurer"   : "str — Insurer name",
            "plan_id"   : "str (optional) — Specific plan ID if known",
        },
        required_params=["cpt_code", "icd10_code", "insurer"],
    ),
    ActionSchema(
        action_type=ActionType.QUERY_POLICY_DATABASE,
        description="Retrieve a section of the insurance policy database for a specific insurer.",
        parameters={
            "insurer"   : "str — Insurer name",
            "section"   : "str — PolicySection enum value",
            "cpt_code"  : "str (optional) — Filter by CPT code",
            "icd10_code": "str (optional) — Filter by ICD-10 code",
        },
        required_params=["insurer", "section"],
    ),
    ActionSchema(
        action_type=ActionType.QUERY_PATIENT_RECORD,
        description="Retrieve a section of the patient's electronic health record.",
        parameters={
            "section": "str — PRSSection enum value: 'vitals', 'diagnosis_codes', 'pharmacy_history', etc.",
        },
        required_params=["section"],
    ),
    ActionSchema(
        action_type=ActionType.SUBMIT_DECISION,
        description="Submit final authorization decision. Ends the episode.",
        parameters={
            "decision"            : "str — AuthorizationDecision: 'approve', 'deny', 'appeal'",
            "rationale"           : "str — Clinical rationale (min 20 chars)",
            "policy_section_cited": "str (optional) — Policy section ID",
            "icd10_codes"         : "list[str] (optional) — Relevant ICD-10 codes",
            "cpt_codes"           : "list[str] (optional) — Relevant CPT codes",
        },
        required_params=["decision", "rationale"],
    ),
]

TASK1_INFO = TaskInfo(
    task_id=TaskID.VERIFICATION,
    name="Insurance Verification & Eligibility Check",
    description=(
        "Determine whether a patient's insurance policy is active and whether the requested "
        "procedure (identified by CPT code) is covered under their plan for the given diagnosis "
        "(ICD-10 code). This is the foundational administrative step of any prior authorization. "
        "The agent must query the Insurance Policy Database (IPD) to verify member eligibility "
        "and procedure coverage, then submit a correct Approve or Deny decision with the relevant "
        "policy section cited."
    ),
    difficulty=Difficulty.EASY,
    max_steps=MAX_STEPS[TaskID.VERIFICATION],
    available_actions=TASK1_AVAILABLE_ACTIONS,
    grader_components=TASK1_GRADER_COMPONENTS,
    reward_signals=REWARD_SIGNALS,
    example_patient_context=(
        "Patient PAT-001 (Member ID: MBR-881234, Insurer: Aetna Gold PPO) is requesting a "
        "knee MRI (CPT 73721) for osteoarthritis (ICD-10 M17.11). The agent must confirm "
        "the policy is active and that 73721 is listed in covered services."
    ),
    baseline_expected_score=0.98,
)


# ===========================================================================
# TASK 2: MEDICAL NECESSITY FOR ADVANCED IMAGING (Medium)
# ===========================================================================

TASK2_GRADER_COMPONENTS: List[GraderComponentSpec] = [
    GraderComponentSpec(
        component_name="evidence_extraction",
        weight=0.35,
        description=(
            "Agent correctly extracts physical therapy session records from the PRS. "
            "Score = (relevant PT sessions found) / (total relevant PT sessions). "
            "Relevant = sessions within the policy's look-back window. "
            "Must capture: session_date, session_number, and functional_outcome."
        ),
    ),
    GraderComponentSpec(
        component_name="policy_duration_logic",
        weight=0.30,
        description=(
            "Agent correctly applies the insurer's PT duration requirement. "
            "1.0 = agent correctly calculates weeks between first and last session "
            "AND compares against the correct policy threshold (3 or 6 weeks). "
            "0.5 = correct duration calculation but wrong threshold cited. "
            "0.0 = incorrect calculation or threshold."
        ),
    ),
    GraderComponentSpec(
        component_name="red_flag_recognition",
        weight=0.20,
        description=(
            "Agent correctly identifies or rules out clinical red flags. "
            "Red flags include: True Locking (torn meniscus), suspected tumor/infection, "
            "progressive neurological deficit, fracture on X-ray. "
            "1.0 = correctly identifies red flag AND invokes bypass. "
            "1.0 = correctly confirms NO red flags present when none exist. "
            "0.0 = misses a present red flag OR falsely claims one."
        ),
    ),
    GraderComponentSpec(
        component_name="final_decision_accuracy",
        weight=0.15,
        description=(
            "Agent's Approve/Deny/Appeal decision is correct given the evidence. "
            "Full score only if the decision is logically consistent with the "
            "duration analysis AND red flag status."
        ),
    ),
]

TASK2_AVAILABLE_ACTIONS: List[ActionSchema] = [
    ActionSchema(
        action_type=ActionType.EXTRACT_PT_SESSIONS,
        description=(
            "Extract all documented physical therapy session records from the patient's "
            "progress notes and rehab records."
        ),
        parameters={
            "start_date": "str (optional) — ISO date filter e.g. '2024-01-01'",
            "end_date"  : "str (optional) — ISO date filter e.g. '2024-06-01'",
        },
        required_params=[],
    ),
    ActionSchema(
        action_type=ActionType.CHECK_RED_FLAGS,
        description=(
            "Scan all physical exam notes and progress notes for clinical red flags that "
            "may bypass the standard conservative therapy requirement for imaging."
        ),
        parameters={},
        required_params=[],
    ),
    ActionSchema(
        action_type=ActionType.COMPARE_POLICY_DURATION,
        description=(
            "Compare the weeks of PT documented in the PRS against the insurer's required "
            "minimum duration. Returns whether the requirement is met."
        ),
        parameters={
            "weeks_of_pt_found": "float — Duration in weeks calculated from PT session dates",
            "insurer"          : "str — Insurer name",
            "cpt_code"         : "str — CPT code for the imaging procedure",
        },
        required_params=["weeks_of_pt_found", "insurer", "cpt_code"],
    ),
    ActionSchema(
        action_type=ActionType.QUERY_POLICY_DATABASE,
        description="Retrieve the specific prior auth criteria for the requested imaging procedure.",
        parameters={
            "insurer"   : "str — Insurer name",
            "section"   : "str — Use 'prior_auth_criteria' to get PT duration requirements",
            "cpt_code"  : "str (optional)",
            "icd10_code": "str (optional)",
        },
        required_params=["insurer", "section"],
    ),
    ActionSchema(
        action_type=ActionType.QUERY_PATIENT_RECORD,
        description="Retrieve a section of the patient's EHR.",
        parameters={
            "section": "str — PRSSection: 'progress_notes', 'physical_exam', 'imaging_history'",
        },
        required_params=["section"],
    ),
    ActionSchema(
        action_type=ActionType.SUBMIT_DECISION,
        description="Submit final authorization decision. Ends the episode.",
        parameters={
            "decision"            : "str — 'approve', 'deny', or 'appeal'",
            "rationale"           : "str — Must reference PT session dates and duration",
            "policy_section_cited": "str (optional)",
            "icd10_codes"         : "list[str] (optional)",
            "cpt_codes"           : "list[str] (optional)",
        },
        required_params=["decision", "rationale"],
    ),
]

TASK2_INFO = TaskInfo(
    task_id=TaskID.MRI_NECESSITY,
    name="Medical Necessity Review: Advanced Imaging (MRI)",
    description=(
        "Determine whether a patient meets the medical necessity criteria for an MRI. "
        "Insurance policies require documented evidence that 'conservative therapy' — such as "
        "physical therapy (PT), NSAIDs, and activity modification — has failed for a specific "
        "duration (typically 3 to 6 weeks) before an MRI will be authorized. "
        "The agent must: (1) retrieve the insurer-specific policy for the requested imaging, "
        "(2) extract PT session records from the EHR and calculate total duration, "
        "(3) check for clinical red flags that bypass the PT requirement, and "
        "(4) submit a correct Approve/Deny decision with precise temporal evidence cited. "
        "Note: Aetna guidelines for knee MRIs require 3 weeks of conservative therapy; "
        "Cigna and most CMS plans require 6 weeks. Policy varies by insurer."
    ),
    difficulty=Difficulty.MEDIUM,
    max_steps=MAX_STEPS[TaskID.MRI_NECESSITY],
    available_actions=TASK2_AVAILABLE_ACTIONS,
    grader_components=TASK2_GRADER_COMPONENTS,
    reward_signals=REWARD_SIGNALS,
    example_patient_context=(
        "Patient PAT-007 (Insurer: Cigna) is requesting an MRI of the right knee (CPT 73721) "
        "for a torn meniscus (ICD-10 M23.211). The policy requires 6 weeks of PT. "
        "The PRS shows only 3 PT sessions over 2 weeks, but the physical exam notes "
        "document 'True Locking' — a red flag that bypasses the PT requirement entirely. "
        "Correct decision: APPROVE (red flag bypass)."
    ),
    baseline_expected_score=0.42,
)


# ===========================================================================
# TASK 3: MEDICAL EXCEPTION APPEAL — CGM (Hard)
# ===========================================================================

# CGM exception thresholds (encoded here as ground-truth for the grader)
CGM_EXCEPTION_THRESHOLDS = {
    "dawn_phenomenon_fasting_glucose_mg_dl" : 200,   # Fasting BG > 200 mg/dL
    "hypoglycemic_unawareness_threshold_mg_dl": 54,  # Glucose < 54 mg/dL (Level 2 hypo)
    "hba1c_target_failure_percent"           : 7.0,  # HbA1c above 7.0 despite 3mo adherence
    "min_months_current_therapy_adherence"   : 3,    # Must show 3+ months of adherence
    "min_daily_insulin_injections_for_cgm"   : 2,    # Step therapy: ≥2 daily injections required
}

TASK3_GRADER_COMPONENTS: List[GraderComponentSpec] = [
    GraderComponentSpec(
        component_name="metric_identification",
        weight=0.40,
        description=(
            "Agent correctly identifies the clinical metric that qualifies the patient for a "
            "CGM exception. "
            "1.0 = agent finds the specific threshold value (fasting glucose > 200 mg/dL "
            "for Dawn Phenomenon, OR documented glucose < 54 mg/dL for hypoglycemic "
            "unawareness) in the patient's lab records. "
            "0.5 = agent identifies the condition (e.g. 'Dawn Phenomenon') but does not "
            "extract the specific mg/dL value. "
            "0.0 = misidentifies or misses the qualifying metric."
        ),
    ),
    GraderComponentSpec(
        component_name="rationale_mapping",
        weight=0.30,
        description=(
            "Agent correctly links the identified clinical metric to the specific exception "
            "clause in the insurance policy. "
            "1.0 = agent cites the correct exception clause AND maps the patient's data "
            "(date, value, unit) to that clause. "
            "0.5 = agent invokes an exception clause but maps the wrong metric to it. "
            "0.0 = no mapping or wrong clause."
        ),
    ),
    GraderComponentSpec(
        component_name="appeal_letter_quality",
        weight=0.30,
        description=(
            "Quality of the generated Letter of Medical Necessity, scored by an LLM-as-judge "
            "(gpt-4o-mini with a structured rubric). "
            "Rubric dimensions: "
            "(A) ICD-10 codes present and correct; "
            "(B) Specific lab values cited with dates; "
            "(C) Policy exception clause explicitly referenced; "
            "(D) Professional tone and template compliance; "
            "(E) Physician attestation present (even if placeholder). "
            "Each dimension is 0.0 or 1.0; final score = sum / 5."
        ),
    ),
]

# LLM-as-Judge rubric for Task 3 appeal letter (used in grader)
APPEAL_LETTER_JUDGE_RUBRIC = """
You are a senior medical reviewer evaluating a Letter of Medical Necessity (LMN) generated 
by an AI agent. Score the letter on the following 5 dimensions. Each dimension scores 0 or 1.

Dimensions:
A. ICD_CODES_PRESENT: Does the letter include at least one correct ICD-10 code relevant to the patient's condition?
B. LAB_VALUES_CITED: Does the letter cite specific lab values (e.g., glucose mg/dL or HbA1c %) with dates?
C. EXCEPTION_CLAUSE_REFERENCED: Does the letter explicitly name or quote a specific insurance policy exception clause?
D. PROFESSIONAL_FORMAT: Is the letter professionally formatted with a greeting, body paragraphs, and closing?
E. PHYSICIAN_ATTESTATION: Does the letter include a physician signature block (can be placeholder)?

Respond ONLY in JSON format like this:
{
  "A_ICD_CODES_PRESENT": 0 or 1,
  "B_LAB_VALUES_CITED": 0 or 1,
  "C_EXCEPTION_CLAUSE_REFERENCED": 0 or 1,
  "D_PROFESSIONAL_FORMAT": 0 or 1,
  "E_PHYSICIAN_ATTESTATION": 0 or 1,
  "total_score": float (sum of above / 5),
  "feedback": "one sentence explanation"
}

Letter to evaluate:
{letter_text}
"""

TASK3_AVAILABLE_ACTIONS: List[ActionSchema] = [
    ActionSchema(
        action_type=ActionType.EXTRACT_LAB_VALUES,
        description=(
            "Extract laboratory test results from the patient's record. "
            "Key labs for CGM: HbA1c, fasting_glucose, glucose_readings (daily log), eGFR."
        ),
        parameters={
            "lab_tests"          : "list[str] — e.g. ['HbA1c', 'fasting_glucose', 'glucose_readings']",
            "date_range_months"  : "int (optional) — How many months back (default 3)",
        },
        required_params=["lab_tests"],
    ),
    ActionSchema(
        action_type=ActionType.CHECK_STEP_THERAPY,
        description=(
            "Verify whether the patient has met the insurer's step therapy requirements "
            "before a CGM can be approved (e.g., documented use of ≥2 daily insulin injections)."
        ),
        parameters={
            "device_requested": "str — 'CGM' or 'insulin_pump'",
            "insurer"         : "str — Insurer name",
        },
        required_params=["device_requested", "insurer"],
    ),
    ActionSchema(
        action_type=ActionType.QUERY_POLICY_DATABASE,
        description="Retrieve CGM coverage criteria or exception clauses from the policy database.",
        parameters={
            "insurer"   : "str — Insurer name",
            "section"   : "str — Use 'exception_criteria' for CGM exception conditions",
            "cpt_code"  : "str (optional) — CGM CPT: 'E2101', 'K0553'",
            "icd10_code": "str (optional) — Diabetes ICD-10: 'E11.649', 'E10.641'",
        },
        required_params=["insurer", "section"],
    ),
    ActionSchema(
        action_type=ActionType.QUERY_PATIENT_RECORD,
        description="Retrieve a section of the patient's EHR.",
        parameters={
            "section": "str — PRSSection: 'lab_results', 'pharmacy_history', 'progress_notes'",
        },
        required_params=["section"],
    ),
    ActionSchema(
        action_type=ActionType.GENERATE_APPEAL_LETTER,
        description=(
            "Generate a Letter of Medical Necessity (LMN) to appeal the CGM denial. "
            "Must include the clinical evidence found and the specific exception clause invoked. "
            "This action does NOT end the episode — the agent must still call SUBMIT_DECISION."
        ),
        parameters={
            "evidence_found"  : "list[str] — Evidence strings the agent identified",
            "exception_clause": "str — The specific exception clause being invoked",
            "physician_name"  : "str (optional)",
            "physician_npi"   : "str (optional)",
        },
        required_params=["evidence_found", "exception_clause"],
    ),
    ActionSchema(
        action_type=ActionType.SUBMIT_DECISION,
        description="Submit final authorization decision. Should be 'appeal' for Task 3.",
        parameters={
            "decision"            : "str — Expected: 'appeal'",
            "rationale"           : "str — Must reference specific exception criteria and lab values",
            "policy_section_cited": "str (optional)",
            "icd10_codes"         : "list[str] (optional)",
            "cpt_codes"           : "list[str] (optional)",
        },
        required_params=["decision", "rationale"],
    ),
]

TASK3_INFO = TaskInfo(
    task_id=TaskID.CGM_APPEAL,
    name="Medical Exception Appeal: Continuous Glucose Monitor (CGM)",
    description=(
        "Handle an appeal after an initial CGM device denial. Many health plans deny CGMs "
        "unless the patient meets specific 'Step Therapy' requirements (e.g., documented use "
        "of ≥2 daily insulin injections). However, medical exceptions exist for patients with "
        "Problematic Hypoglycemia (documented glucose < 54 mg/dL) or the Dawn Phenomenon "
        "(fasting glucose frequently exceeding 200 mg/dL). "
        "The agent must: "
        "(1) check step therapy compliance in the pharmacy history, "
        "(2) extract glucose and HbA1c lab values to identify qualifying exception criteria, "
        "(3) retrieve the specific exception clause from the insurance policy, "
        "(4) generate a Letter of Medical Necessity (LMN) that cites the clinical evidence, and "
        "(5) submit an Appeal decision with the evidence-backed rationale. "
        "This task requires synthesizing longitudinal lab data and mapping it to precise "
        "policy thresholds — the most cognitively demanding task in the environment."
    ),
    difficulty=Difficulty.HARD,
    max_steps=MAX_STEPS[TaskID.CGM_APPEAL],
    available_actions=TASK3_AVAILABLE_ACTIONS,
    grader_components=TASK3_GRADER_COMPONENTS,
    reward_signals=REWARD_SIGNALS,
    example_patient_context=(
        "Patient PAT-015 (Type 1 Diabetic, Insurer: CMS/Medicare) was denied a CGM "
        "(CPT K0553). Pharmacy history shows 4 daily insulin injections (step therapy met). "
        "Lab records contain fasting glucose readings of 215 mg/dL, 228 mg/dL, and 210 mg/dL "
        "across 3 consecutive mornings — meeting the Dawn Phenomenon threshold (> 200 mg/dL). "
        "HbA1c is 8.4% despite 3 months of adherence. "
        "The agent must find the 200 mg/dL threshold, cite the CMS exception clause, "
        "generate an LMN, and submit an Appeal."
    ),
    baseline_expected_score=0.15,
)


# ===========================================================================
# TASK REGISTRY (imported by server and baseline)
# ===========================================================================

ALL_TASKS: Dict[TaskID, TaskInfo] = {
    TaskID.VERIFICATION  : TASK1_INFO,
    TaskID.MRI_NECESSITY : TASK2_INFO,
    TaskID.CGM_APPEAL    : TASK3_INFO,
}

TASK_DIFFICULTY_ORDER: List[TaskID] = [
    TaskID.VERIFICATION,
    TaskID.MRI_NECESSITY,
    TaskID.CGM_APPEAL,
]


def get_task(task_id: TaskID) -> TaskInfo:
    """Retrieve a TaskInfo by ID. Raises KeyError if not found."""
    if task_id not in ALL_TASKS:
        raise KeyError(f"Unknown task_id: {task_id!r}. Valid: {list(ALL_TASKS.keys())}")
    return ALL_TASKS[task_id]


def get_all_tasks() -> List[TaskInfo]:
    """Return all tasks in difficulty order (easy → medium → hard)."""
    return [ALL_TASKS[tid] for tid in TASK_DIFFICULTY_ORDER]


def get_grader_components(task_id: TaskID) -> List[GraderComponentSpec]:
    """Return the grader component specs for a given task."""
    return get_task(task_id).grader_components


def get_reward_value(signal_name: str) -> float:
    """Look up a reward signal value by name. Returns 0.0 if not found."""
    return REWARD_SIGNALS.get(signal_name, 0.0)


def get_max_steps(task_id: TaskID) -> int:
    """Return the max steps allowed for a given task."""
    return MAX_STEPS.get(task_id, 25)


# ===========================================================================
# GROUND TRUTH ANSWER KEYS
# (Used by programmatic graders for Tasks 1 & 2)
# Maps patient_id → correct answer for each task
# ===========================================================================

# Format: { patient_id: { "decision": AuthorizationDecision, "key_facts": [...] } }
TASK1_ANSWER_KEYS: Dict[str, Dict] = {
    "PAT-001": {
        "decision"            : AuthorizationDecision.APPROVE,
        "member_active"       : True,
        "cpt_covered"         : True,
        "correct_policy_section": "Section 4.2 Covered Services",
        "insurer"             : "aetna",
    },
    "PAT-002": {
        "decision"            : AuthorizationDecision.DENY,
        "member_active"       : False,
        "cpt_covered"         : True,   # Would be covered, but plan is inactive
        "correct_policy_section": "Section 2.1 Eligibility Requirements",
        "insurer"             : "cigna",
    },
    "PAT-003": {
        "decision"            : AuthorizationDecision.DENY,
        "member_active"       : True,
        "cpt_covered"         : False,  # CPT not in covered services for this plan
        "correct_policy_section": "Section 4.2 Covered Services",
        "insurer"             : "united",
    },
    "PAT-004": {
        "decision"            : AuthorizationDecision.APPROVE,
        "member_active"       : True,
        "cpt_covered"         : True,
        "correct_policy_section": "Section 4.2 Covered Services",
        "insurer"             : "cms",
    },
    "PAT-005": {
        "decision"            : AuthorizationDecision.DENY,
        "member_active"       : True,
        "cpt_covered"         : False,
        "correct_policy_section": "Section 5.1 Prior Authorization Required",
        "insurer"             : "aetna",
    },
}

TASK2_ANSWER_KEYS: Dict[str, Dict] = {
    "PAT-006": {
        "decision"            : AuthorizationDecision.APPROVE,
        "insurer"             : "aetna",
        "required_pt_weeks"   : 3,
        "documented_pt_weeks" : 4.0,
        "pt_sessions_count"   : 8,
        "red_flag_present"    : False,
        "correct_policy_section": "Aetna CPB 0171 — MRI Extremities Criteria",
    },
    "PAT-007": {
        "decision"            : AuthorizationDecision.APPROVE,  # Red flag bypass
        "insurer"             : "cigna",
        "required_pt_weeks"   : 6,
        "documented_pt_weeks" : 2.0,
        "pt_sessions_count"   : 4,
        "red_flag_present"    : True,
        "red_flag_type"       : "True Locking (suspected torn meniscus)",
        "bypass_clause"       : "Urgency Bypass — Mechanical Joint Locking",
        "correct_policy_section": "Cigna Clinical Policy Bulletin MRI Extremities",
    },
    "PAT-008": {
        "decision"            : AuthorizationDecision.DENY,
        "insurer"             : "cigna",
        "required_pt_weeks"   : 6,
        "documented_pt_weeks" : 2.0,
        "pt_sessions_count"   : 3,
        "red_flag_present"    : False,
        "correct_policy_section": "Cigna Clinical Policy Bulletin MRI Extremities",
    },
    "PAT-009": {
        "decision"            : AuthorizationDecision.APPROVE,
        "insurer"             : "cms",
        "required_pt_weeks"   : 6,
        "documented_pt_weeks" : 7.5,
        "pt_sessions_count"   : 15,
        "red_flag_present"    : False,
        "correct_policy_section": "CMS LCD L33642 — Lumbar MRI Criteria",
    },
    "PAT-010": {
        "decision"            : AuthorizationDecision.DENY,
        "insurer"             : "aetna",
        "required_pt_weeks"   : 3,
        "documented_pt_weeks" : 1.5,
        "pt_sessions_count"   : 2,
        "red_flag_present"    : False,
        "correct_policy_section": "Aetna CPB 0171 — MRI Extremities Criteria",
    },
}

# Task 3 uses LLM-as-judge; keys define the qualifying exception for each patient
TASK3_ANSWER_KEYS: Dict[str, Dict] = {
    "PAT-011": {
        "decision"             : AuthorizationDecision.APPEAL,
        "insurer"              : "cms",
        "exception_type"       : "dawn_phenomenon",
        "qualifying_metric"    : "fasting_glucose",
        "qualifying_value"     : 215.0,
        "qualifying_unit"      : "mg/dL",
        "qualifying_threshold" : "> 200 mg/dL",
        "correct_exception_clause": "CMS LCD L33822 — CGM Exception: Problematic Hypoglycemia / Dawn Phenomenon",
        "step_therapy_met"     : True,
    },
    "PAT-012": {
        "decision"             : AuthorizationDecision.APPEAL,
        "insurer"              : "aetna",
        "exception_type"       : "hypoglycemic_unawareness",
        "qualifying_metric"    : "glucose_reading",
        "qualifying_value"     : 48.0,
        "qualifying_unit"      : "mg/dL",
        "qualifying_threshold" : "< 54 mg/dL",
        "correct_exception_clause": "Aetna CPB 0515 — CGM Exception: Level 2 Hypoglycemic Events",
        "step_therapy_met"     : True,
    },
    "PAT-013": {
        "decision"             : AuthorizationDecision.APPEAL,
        "insurer"              : "cigna",
        "exception_type"       : "glycemic_variability",
        "qualifying_metric"    : "HbA1c",
        "qualifying_value"     : 8.9,
        "qualifying_unit"      : "%",
        "qualifying_threshold" : "> 7.0% despite 3 months adherence",
        "correct_exception_clause": "Cigna CPG CGM Coverage Exception — Inadequate Glycemic Control",
        "step_therapy_met"     : True,
    },
    "PAT-014": {
        "decision"             : AuthorizationDecision.DENY,  # Step therapy NOT met
        "insurer"              : "cms",
        "exception_type"       : None,
        "step_therapy_met"     : False,
        "denial_reason"        : "Patient on oral medication only; < 2 daily insulin injections",
        "correct_exception_clause": None,
    },
    "PAT-015": {
        "decision"             : AuthorizationDecision.APPEAL,
        "insurer"              : "cms",
        "exception_type"       : "dawn_phenomenon",
        "qualifying_metric"    : "fasting_glucose",
        "qualifying_value"     : 215.0,
        "qualifying_unit"      : "mg/dL",
        "qualifying_threshold" : "> 200 mg/dL",
        "correct_exception_clause": "CMS LCD L33822 — CGM Exception: Problematic Hypoglycemia / Dawn Phenomenon",
        "step_therapy_met"     : True,
    },
}

"""
models.py — Shared Contract: All Pydantic Models for the PTPA OpenEnv Environment

Patient Triage & Prior Authorization (PTPA) Environment
=========================================================
This file defines ALL typed Pydantic models for Actions, Observations, State,
and supporting structures. Both Person A (environment engine) and Person B
(FastAPI server + baseline) build against this contract.

DO NOT modify without team agreement — this is the interface boundary.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


# ===========================================================================
# ENUMS
# ===========================================================================

class TaskID(str, Enum):
    """The three tasks in the PTPA environment, ordered by difficulty."""
    VERIFICATION    = "task1_verification"
    MRI_NECESSITY   = "task2_mri_necessity"
    CGM_APPEAL      = "task3_cgm_appeal"


class Difficulty(str, Enum):
    EASY   = "easy"
    MEDIUM = "medium"
    HARD   = "hard"


class EpisodeStatus(str, Enum):
    """Lifecycle states of an episode."""
    IDLE    = "idle"
    ACTIVE  = "active"
    GRADING = "grading"
    DONE    = "done"


class AuthorizationDecision(str, Enum):
    """The three possible final determinations an agent can submit."""
    APPROVE = "approve"
    DENY    = "deny"
    APPEAL  = "appeal"


class ActionType(str, Enum):
    """
    All legal action types an agent can take across all tasks.
    Some actions are only valid in certain tasks (documented below).
    """
    # --- Universal actions (all tasks) ---
    QUERY_PATIENT_RECORD    = "query_patient_record"    # Retrieve a section of the PRS
    QUERY_POLICY_DATABASE   = "query_policy_database"   # Retrieve an insurance policy rule
    SUBMIT_DECISION         = "submit_decision"         # Final approve/deny/appeal + rationale

    # --- Task 1: Verification ---
    CHECK_ELIGIBILITY       = "check_eligibility"       # Verify member ID + plan active status
    CHECK_CPT_COVERAGE      = "check_cpt_coverage"      # Look up CPT code in covered services

    # --- Task 2: MRI Necessity ---
    EXTRACT_PT_SESSIONS     = "extract_pt_sessions"     # Pull physical therapy session records
    CHECK_RED_FLAGS         = "check_red_flags"         # Scan for clinical urgency indicators
    COMPARE_POLICY_DURATION = "compare_policy_duration" # Compare PT weeks vs policy requirement

    # --- Task 3: CGM Appeal ---
    EXTRACT_LAB_VALUES      = "extract_lab_values"      # Retrieve HbA1c, glucose readings
    CHECK_STEP_THERAPY      = "check_step_therapy"      # Verify prior therapy requirements met
    GENERATE_APPEAL_LETTER  = "generate_appeal_letter"  # Draft Letter of Medical Necessity


class PRSSection(str, Enum):
    """Queryable sections of the Patient Record System."""
    VITALS           = "vitals"
    PROGRESS_NOTES   = "progress_notes"
    LAB_RESULTS      = "lab_results"
    PHYSICAL_EXAM    = "physical_exam"
    PHARMACY_HISTORY = "pharmacy_history"
    IMAGING_HISTORY  = "imaging_history"
    DIAGNOSIS_CODES  = "diagnosis_codes"


class PolicySection(str, Enum):
    """Queryable sections of the Insurance Policy Database."""
    ELIGIBILITY          = "eligibility"
    COVERED_SERVICES     = "covered_services"
    PRIOR_AUTH_CRITERIA  = "prior_auth_criteria"
    STEP_THERAPY_RULES   = "step_therapy_rules"
    EXCEPTION_CRITERIA   = "exception_criteria"
    APPEAL_PROCESS       = "appeal_process"


# ===========================================================================
# ACTION MODELS
# ===========================================================================

class PTPAAction(BaseModel):
    """
    The universal action model. Every agent step sends exactly one of these.

    Fields
    ------
    action_type : ActionType
        Which action to perform. See ActionType enum for all valid values.
    patient_id : str
        The patient whose records to query (e.g. "PAT-001").
    task_id : TaskID
        Which task this action belongs to.
    parameters : dict
        Action-specific parameters. Key schemas documented in Params* models below.

    Example
    -------
    {
        "action_type": "check_eligibility",
        "patient_id": "PAT-001",
        "task_id": "task1_verification",
        "parameters": {
            "member_id": "MBR-881234",
            "insurer": "aetna"
        }
    }
    """
    action_type : ActionType
    patient_id  : str             = Field(..., description="Patient identifier, e.g. 'PAT-001'")
    task_id     : TaskID
    parameters  : Dict[str, Any]  = Field(
        default_factory=dict,
        description="Action-specific parameters. See ActionParameters sub-models."
    )


# ---- Per-action parameter schemas (for documentation + server-side validation) ----

class ParamsQueryPatientRecord(BaseModel):
    section: PRSSection = Field(..., description="Which PRS section to retrieve")


class ParamsQueryPolicyDatabase(BaseModel):
    insurer    : str           = Field(..., description="Insurer name: 'aetna', 'cigna', 'cms'")
    section    : PolicySection
    cpt_code   : Optional[str] = Field(None, description="CPT code to look up, e.g. '73721'")
    icd10_code : Optional[str] = Field(None, description="ICD-10 code, e.g. 'M17.11'")


class ParamsCheckEligibility(BaseModel):
    member_id : str = Field(..., description="Insurance member ID from patient record")
    insurer   : str = Field(..., description="Insurer name")


class ParamsCheckCPTCoverage(BaseModel):
    cpt_code   : str           = Field(..., description="Procedure code, e.g. '73721' for knee MRI")
    icd10_code : str
    insurer    : str
    plan_id    : Optional[str] = None


class ParamsExtractPTSessions(BaseModel):
    start_date : Optional[str] = Field(None, description="ISO date filter, e.g. '2024-01-01'")
    end_date   : Optional[str] = Field(None, description="ISO date filter, e.g. '2024-06-01'")


class ParamsCheckRedFlags(BaseModel):
    """No additional params — scans all physical exam + progress notes automatically."""
    pass


class ParamsComparePolicyDuration(BaseModel):
    weeks_of_pt_found : float = Field(..., description="Duration in weeks extracted from PRS")
    insurer           : str
    cpt_code          : str


class ParamsExtractLabValues(BaseModel):
    lab_tests          : List[str]     = Field(
        ...,
        description="Lab test names to extract. Valid: 'HbA1c', 'fasting_glucose', 'eGFR', "
                    "'glucose_readings', 'insulin_dose'"
    )
    date_range_months  : Optional[int] = Field(
        3, description="How many months back to look (default 3)"
    )


class ParamsCheckStepTherapy(BaseModel):
    device_requested : str = Field(..., description="Device: 'CGM' or 'insulin_pump'")
    insurer          : str


class ParamsGenerateAppealLetter(BaseModel):
    evidence_found    : List[str] = Field(
        ...,
        description="Evidence strings the agent identified, e.g. "
                    "['Dawn Phenomenon: fasting glucose 215 mg/dL on 2024-03-01']"
    )
    exception_clause  : str       = Field(
        ...,
        description="The specific policy exception clause being invoked"
    )
    physician_name : Optional[str] = None
    physician_npi  : Optional[str] = None


class ParamsSubmitDecision(BaseModel):
    decision             : AuthorizationDecision
    rationale            : str            = Field(
        ..., min_length=20,
        description="Clinical rationale referencing specific evidence."
    )
    policy_section_cited : Optional[str]  = Field(
        None, description="Specific policy section that supports the decision"
    )
    icd10_codes          : Optional[List[str]] = None
    cpt_codes            : Optional[List[str]] = None


# ===========================================================================
# OBSERVATION MODELS
# ===========================================================================

class EvidenceItem(BaseModel):
    """A single piece of extracted clinical evidence."""
    evidence_type         : str   = Field(..., description="'lab_result', 'pt_session', 'red_flag', 'policy_rule'")
    label                 : str   = Field(..., description="Human-readable label, e.g. 'HbA1c'")
    value                 : Any   = Field(..., description="Extracted value, e.g. 8.2 or '6 sessions'")
    unit                  : Optional[str] = Field(default=None, description="Unit: '%', 'mg/dL', 'weeks'")
    date                  : Optional[str] = Field(default=None, description="ISO date when recorded")
    source_section        : Optional[str] = Field(default=None, description="Which PRS section this came from")
    clinically_significant: bool  = Field(
        False,
        description="True if this evidence directly affects the grader score"
    )


class RedFlagItem(BaseModel):
    """A clinical red flag that may bypass standard policy requirements."""
    flag_name            : str = Field(..., description="e.g. 'True Locking', 'Suspected Infection'")
    description          : str
    bypasses_requirement : str = Field(
        ..., description="Which policy requirement this red flag bypasses"
    )
    severity             : Literal["low", "medium", "high", "critical"] = "high"


class PTSession(BaseModel):
    """A single physical therapy session record."""
    session_date     : str             = Field(..., description="ISO date, e.g. '2024-01-15'")
    session_number   : int
    therapist_notes  : str
    functional_outcome: Optional[str] = None
    pain_score       : Optional[float] = Field(None, ge=0, le=10)
    improved         : bool = False


class PolicyRule(BaseModel):
    """A retrieved insurance policy rule."""
    insurer            : str
    section            : str
    rule_id            : str
    description        : str
    requirement        : Optional[str]       = None
    exception_criteria : Optional[List[str]] = None
    effective_date     : Optional[str]       = None


class PTPAObservation(BaseModel):
    """
    Returned after every agent action via step().

    Fields
    ------
    result : str
        Human-readable summary of what was found or done.
    success : bool
        Whether the action completed without error.
    found_evidence : list[EvidenceItem]
        Structured evidence extracted by this action (may be empty).
    red_flags : list[RedFlagItem]
        Clinical red flags detected (Task 2 primarily).
    pt_sessions : list[PTSession]
        Physical therapy records (Task 2 only).
    policy_rule : PolicyRule | None
        The insurance policy rule retrieved (Tasks 1 & 2).
    reward : float
        Partial progress reward for this step (range: -0.5 to +0.4).
    reward_reason : str
        Explanation of why this reward was given.
    step_count : int
        How many steps have been taken in this episode so far.
    done : bool
        True if the episode has ended (decision submitted or max steps reached).
    error : str | None
        Error message if action was invalid or malformed.
    info : dict
        Extra metadata (task-specific debug info, loop detection flags, etc.).
    """
    result         : str
    success        : bool
    found_evidence : List[EvidenceItem]  = Field(default_factory=list)
    red_flags      : List[RedFlagItem]   = Field(default_factory=list)
    pt_sessions    : List[PTSession]     = Field(default_factory=list)
    policy_rule    : Optional[PolicyRule] = None
    reward         : float = Field(default=0.0, ge=-1.0, le=1.0)
    reward_reason  : str   = ""
    step_count     : int   = 0
    done           : bool  = False
    error          : Optional[str]       = None
    info           : Dict[str, Any]      = Field(default_factory=dict)


# ===========================================================================
# STATE MODELS
# ===========================================================================

class PatientRecord(BaseModel):
    """
    Minimal patient record header (full record lives in PRS fixtures).
    Returned as part of state() so the agent always knows who it's working on.
    """
    patient_id          : str = Field(..., description="e.g. 'PAT-001'")
    name                : str
    dob                 : str = Field(..., description="ISO date, e.g. '1965-04-12'")
    member_id           : str = Field(..., description="Insurance member ID")
    insurer             : str
    plan_id             : str
    primary_icd10       : str = Field(..., description="Primary diagnosis code e.g. 'M17.11'")
    requested_cpt       : str = Field(..., description="Procedure being requested e.g. '73721'")
    attending_physician : str


class EpisodeProgress(BaseModel):
    """Tracks what the agent has discovered so far in the current episode."""
    # Completion flags
    eligibility_verified   : bool = False
    cpt_coverage_checked   : bool = False
    pt_sessions_extracted  : bool = False
    red_flags_checked      : bool = False
    lab_values_extracted   : bool = False
    step_therapy_checked   : bool = False
    policy_retrieved       : bool = False
    decision_submitted     : bool = False

    # Accumulated findings
    discovered_evidence    : List[EvidenceItem] = Field(default_factory=list)
    discovered_red_flags   : List[RedFlagItem]  = Field(default_factory=list)
    queried_sections       : List[str]           = Field(default_factory=list)

    # Loop detection
    repeated_queries       : int   = Field(default=0, description="Count of duplicate queries")
    total_reward_so_far    : float = 0.0


class PTPAState(BaseModel):
    """
    Full environment state returned by GET /state.
    This is the agent's complete world view.
    """
    episode_id : str
    task_id    : TaskID
    difficulty : Difficulty
    status     : EpisodeStatus
    step_count : int
    max_steps  : int         = Field(25, description="Episode terminates at this step count")
    patient    : PatientRecord
    progress   : EpisodeProgress
    seed       : int         = Field(..., description="Random seed for reproducibility")
    created_at : str         = Field(..., description="ISO datetime of episode start")


# ===========================================================================
# GRADER MODELS
# ===========================================================================

class GraderComponentScore(BaseModel):
    """Score for one sub-component of the grader."""
    component_name : str
    weight         : float = Field(..., ge=0.0, le=1.0, description="Weight of this component (sums to 1.0)")
    score          : float = Field(..., ge=0.0, le=1.0, description="Raw score for this component")
    weighted_score : float = Field(..., ge=0.0, le=1.0)
    passed         : bool
    feedback       : str   = ""


class GraderResult(BaseModel):
    """
    Full grader output returned by POST /grader.
    final_score is the weighted sum of all component scores (0.0–1.0).
    """
    task_id             : TaskID
    episode_id          : str
    final_score         : float = Field(..., ge=0.0, le=1.0)
    components          : List[GraderComponentScore]
    decision_made       : Optional[AuthorizationDecision] = None
    decision_correct    : Optional[bool] = None
    feedback            : str   = Field("", description="Human-readable overall feedback")
    grader_version      : str   = "1.0.0"

    # Task 3 only: LLM-as-judge sub-score for the appeal letter
    appeal_letter_score : Optional[float] = Field(
        default=None, ge=0.0, le=1.0,
        description="LLM-as-judge score for appeal letter quality (Task 3 only)"
    )


# ===========================================================================
# TASK INFO MODELS  (for GET /tasks)
# ===========================================================================

class ActionSchema(BaseModel):
    """Describes what parameters an action type accepts."""
    action_type    : ActionType
    description    : str
    parameters     : Dict[str, str] = Field(
        default_factory=dict,
        description="Parameter name → type/description mapping"
    )
    required_params: List[str]       = Field(default_factory=list)


class GraderComponentSpec(BaseModel):
    """Describes how a task is graded (self-documenting for the agent)."""
    component_name : str
    weight         : float
    description    : str


class TaskInfo(BaseModel):
    """
    Full task descriptor returned by GET /tasks.
    Agents use this to understand the task, available actions, and grading criteria.
    """
    task_id                 : TaskID
    name                    : str
    description             : str
    difficulty              : Difficulty
    max_steps               : int
    available_actions       : List[ActionSchema]
    grader_components       : List[GraderComponentSpec]
    reward_signals          : Dict[str, float] = Field(
        default_factory=dict,
        description="Signal name → reward value mapping"
    )
    example_patient_context : str   = Field(
        "", description="Brief example of a patient scenario for this task"
    )
    baseline_expected_score : float = Field(
        ..., description="Expected score for gpt-5.4-mini baseline agent"
    )


class TaskListResponse(BaseModel):
    """Response schema for GET /tasks."""
    tasks       : List[TaskInfo]
    environment : str = "healthcare_prior_auth"
    version     : str = "1.2.0"


# ===========================================================================
# BASELINE / INFERENCE MODELS  (for POST /baseline)
# ===========================================================================

class BaselineStepTrace(BaseModel):
    """One recorded step from the baseline inference run."""
    step_number       : int
    action            : PTPAAction
    observation       : PTPAObservation
    cumulative_reward : float


class BaselineTaskResult(BaseModel):
    """Baseline result for a single task."""
    task_id       : TaskID
    episode_id    : str
    seed          : int
    final_score   : float
    steps_taken   : int
    decision_made : Optional[AuthorizationDecision]
    grader_result : GraderResult
    trace         : List[BaselineStepTrace] = Field(default_factory=list)
    success       : bool


class BaselineResponse(BaseModel):
    """
    Full response from POST /baseline.
    Runs gpt-5.4-mini agent against all 3 tasks with fixed seeds.
    """
    environment_version : str  = "1.2.0"
    model_used          : str  = "gpt-5.4-mini"
    seeds_used          : List[int] = Field(default_factory=list)
    task_results        : List[BaselineTaskResult]
    overall_score       : float = Field(..., description="Mean score across all 3 tasks")
    run_timestamp       : str


# ===========================================================================
# API REQUEST / RESPONSE WRAPPERS
# ===========================================================================

class ResetRequest(BaseModel):
    """Request body for POST /reset."""
    task_id    : TaskID
    seed       : Optional[int] = Field(
        None, description="Fix seed for reproducible episodes. None = random."
    )
    patient_id : Optional[str] = Field(
        None, description="Request a specific patient fixture. None = sampled by seed."
    )


class ResetResponse(BaseModel):
    """Response from POST /reset — returns initial observation and full state."""
    episode_id          : str
    task_id             : TaskID
    initial_observation : PTPAObservation
    state               : PTPAState


class StepRequest(BaseModel):
    """Request body for POST /step."""
    episode_id : str
    action     : PTPAAction


class StepResponse(BaseModel):
    """Response from POST /step."""
    episode_id  : str
    observation : PTPAObservation
    reward      : float
    done        : bool
    state       : PTPAState


class GraderRequest(BaseModel):
    """Request body for POST /grader."""
    episode_id : str


class ErrorResponse(BaseModel):
    """Standard error response shape."""
    error      : str
    detail     : Optional[str] = None
    episode_id : Optional[str] = None

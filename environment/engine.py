"""
engine.py — Core Environment Engine for the PTPA OpenEnv Environment

Loads patient data from data/prs/*.json and insurance policies from
data/ipd/*.json. Implements reset(), step(), get_state(), and grade().
"""

from __future__ import annotations

import copy
import json
import os
import random
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from models import (
    ActionType,
    DifficultyConfig,
    EpisodeProgress,
    EpisodeStatus,
    EvidenceItem,
    GraderResult,
    ObservationHistoryEntry,
    PatientRecord,
    PolicyRule,
    PTSession,
    PTPAAction,
    PTPAObservation,
    PTPAState,
    RedFlagItem,
    TaskID,
)
from tasks import (
    get_max_steps,
    get_task,
)
from environment.rewards import compute_step_reward, no_reward
from environment.task1_verification import grade as grade_task1
from environment.task2_mri_necessity import grade as grade_task2
from environment.task3_cgm_appeal import grade as grade_task3
from environment.task4_peer_review import grade as grade_task4


# =========================================================================
# DATA LOADING
# =========================================================================

_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
_PRS_DIR = os.path.join(_DATA_DIR, "prs")
_IPD_DIR = os.path.join(_DATA_DIR, "ipd")


def _load_patients() -> Dict[str, Dict[str, Any]]:
    """Load all patient JSON files from data/prs/."""
    patients: Dict[str, Dict[str, Any]] = {}
    if not os.path.isdir(_PRS_DIR):
        return patients
    for fname in os.listdir(_PRS_DIR):
        if fname.endswith(".json"):
            fpath = os.path.join(_PRS_DIR, fname)
            with open(fpath, "r") as f:
                data = json.load(f)
            pid = data.get("patient_id", fname.replace(".json", ""))
            patients[pid] = data
    return patients


def _load_policies() -> Dict[str, Dict[str, Any]]:
    """Load all insurer policy JSON files from data/ipd/."""
    policies: Dict[str, Dict[str, Any]] = {}
    if not os.path.isdir(_IPD_DIR):
        return policies
    for fname in os.listdir(_IPD_DIR):
        if fname.endswith(".json"):
            fpath = os.path.join(_IPD_DIR, fname)
            with open(fpath, "r") as f:
                data = json.load(f)
            insurer = data.get("insurer", fname.replace("_policies.json", ""))
            policies[insurer] = data
    return policies


# Load on module import
_PATIENTS: Dict[str, Dict[str, Any]] = _load_patients()
_POLICIES: Dict[str, Dict[str, Any]] = _load_policies()

# Patient pool derived from answer keys in tasks.py
_TASK_PATIENTS = {
    TaskID.VERIFICATION:  ["PAT-001", "PAT-002", "PAT-003", "PAT-004", "PAT-005", "PAT-021", "PAT-022", "PAT-023", "PAT-024", "PAT-025"],
    TaskID.MRI_NECESSITY: ["PAT-006", "PAT-007", "PAT-008", "PAT-009", "PAT-010", "PAT-026", "PAT-027", "PAT-028", "PAT-029", "PAT-030"],
    TaskID.CGM_APPEAL:    ["PAT-011", "PAT-012", "PAT-013", "PAT-014", "PAT-015", "PAT-031", "PAT-032", "PAT-033", "PAT-034", "PAT-035"],
    TaskID.PEER_REVIEW:   ["PAT-036", "PAT-037", "PAT-038", "PAT-039", "PAT-040", "PAT-041", "PAT-042", "PAT-043", "PAT-044", "PAT-045", "PAT-046", "PAT-047", "PAT-048", "PAT-049", "PAT-050"],
}


# =========================================================================
# HELPERS — adapt to actual data schemas
# =========================================================================

def _get_insurance_active(patient: dict) -> bool:
    ins = patient.get("insurance", {})
    # data uses "active" (bool)
    return ins.get("active", ins.get("active_status", False))


def _get_insurer(patient: dict) -> str:
    return patient.get("insurance", {}).get("insurer", "")


def _get_member_id(patient: dict) -> str:
    return patient.get("insurance", {}).get("member_id", "")


def _get_plan_id(patient: dict) -> str:
    return patient.get("insurance", {}).get("plan_id", "")


def _get_cpt(patient: dict) -> str:
    return patient.get("requested_procedure", {}).get("cpt_code", "")


def _get_primary_icd10(patient: dict) -> str:
    dx = patient.get("diagnosis_codes", [])
    if dx:
        return dx[0].get("code", "")
    return ""


def _get_patient_name(patient: dict) -> str:
    return patient.get("demographics", {}).get("name", "Unknown")


def _get_dob(patient: dict) -> str:
    return patient.get("demographics", {}).get("dob", "")


def _get_lab_test_name(lab: dict) -> str:
    """data uses 'test_name'; fallback to 'test'."""
    return lab.get("test_name", lab.get("test", ""))


def _get_policy_section(service_entry: dict) -> str:
    """data uses 'policy_section'; fallback to 'section'."""
    return service_entry.get("policy_section", service_entry.get("section", ""))


def _get_pt_required_weeks(criteria: dict) -> int:
    """data uses 'pt_required_weeks'; fallback to 'conservative_therapy_weeks'."""
    return criteria.get("pt_required_weeks", criteria.get("conservative_therapy_weeks", 6))


def _get_step_therapy_rules(policy: dict, device: str = "CGM") -> dict:
    return policy.get("step_therapy_rules", {}).get(device, {})


def _count_insulin_injections(pharmacy: list) -> int:
    """Parse 'X times daily' from pharmacy_history."""
    total = 0
    for med in pharmacy:
        name = (med.get("medication", "") or "").lower()
        if "insulin" not in name:
            continue
        freq = (med.get("frequency", "") or "").lower()
        m = re.search(r"(\d+)\s*times?\s*daily", freq)
        if m:
            total += int(m.group(1))
        else:
            # fallback: check route-based format from richer data
            route = (med.get("route", "") or "").lower()
            if "subcutaneous" in route or "inject" in route:
                if "once" in freq:
                    total += 1
                elif "3x" in freq or "three" in freq:
                    total += 3
                elif "twice" in freq or "2x" in freq:
                    total += 2
                else:
                    total += 1
    return total


def _extract_red_flags_from_patient(patient: dict) -> List[RedFlagItem]:
    """Extract red flags from physical_exam and progress_notes."""
    flags: List[RedFlagItem] = []
    seen = set()

    # Physical exam red_flags field (actual data schema)
    for exam in patient.get("physical_exam", []):
        for rf_name in exam.get("red_flags", []):
            if rf_name not in seen:
                seen.add(rf_name)
                flags.append(RedFlagItem(
                    flag_name=rf_name,
                    description=f"Red flag identified in physical exam: {rf_name}",
                    bypasses_requirement="Conservative therapy duration requirement",
                    severity="critical",
                ))

    # Also scan text of findings and progress notes (for richer data formats)
    all_text = ""
    for exam in patient.get("physical_exam", []):
        findings = exam.get("findings", "")
        if isinstance(findings, list):
            all_text += " ".join(findings) + " "
        elif isinstance(findings, str):
            all_text += findings + " "
    for note in patient.get("progress_notes", []):
        all_text += (note.get("note", "") or "") + " "

    all_upper = all_text.upper()
    text_flags = {
        "True Locking": ["TRUE LOCKING", "LOCKED"],
        "Suspected Tumor": ["TUMOR", "MASS"],
        "Suspected Infection": ["INFECTION"],
        "Progressive Neurological Deficit": ["PROGRESSIVE NEUROLOGICAL", "NEUROLOGICAL DEFICIT"],
        "Fracture": ["FRACTURE"],
    }
    for flag_name, keywords in text_flags.items():
        if flag_name not in seen and any(kw in all_upper for kw in keywords):
            seen.add(flag_name)
            flags.append(RedFlagItem(
                flag_name=flag_name,
                description=f"Red flag detected in clinical notes: {flag_name}",
                bypasses_requirement="Conservative therapy duration requirement",
                severity="critical",
            ))

    return flags


# =========================================================================
# ENGINE
# =========================================================================

class PTPAEngine:
    """
    Core environment engine. Manages episode state internally
    and processes actions against data loaded from data/ files.
    """

    def __init__(self) -> None:
        self._episodes: Dict[str, Dict[str, Any]] = {}

    # -----------------------------------------------------------------
    # reset
    # -----------------------------------------------------------------
    def reset(
        self,
        episode_id: str,
        task_id: TaskID,
        seed: Optional[int] = None,
        patient_id: Optional[str] = None,
        difficulty_config: Optional[DifficultyConfig] = None,
    ) -> Tuple[PTPAObservation, PTPAState]:
        rng = random.Random(seed)

        pool = _TASK_PATIENTS[task_id]
        if patient_id and patient_id in pool:
            pid = patient_id
        elif patient_id and patient_id in _PATIENTS:
            pid = patient_id
        else:
            pid = rng.choice(pool)

        if pid not in _PATIENTS:
            raise ValueError(f"Patient {pid} not found in data/prs/")

        patient_data = copy.deepcopy(_PATIENTS[pid])
        insurer = _get_insurer(patient_data)
        cpt = _get_cpt(patient_data)
        icd10 = _get_primary_icd10(patient_data)
        name = _get_patient_name(patient_data)

        patient_record = PatientRecord(
            patient_id=pid,
            name=name,
            dob=_get_dob(patient_data),
            member_id=_get_member_id(patient_data),
            insurer=insurer,
            plan_id=_get_plan_id(patient_data),
            primary_icd10=icd10,
            requested_cpt=cpt,
            attending_physician=patient_data.get("attending_physician", "Attending Physician"),
        )

        task_info = get_task(task_id)
        state = PTPAState(
            episode_id=episode_id,
            task_id=task_id,
            difficulty=task_info.difficulty,
            status=EpisodeStatus.ACTIVE,
            step_count=0,
            max_steps=get_max_steps(task_id),
            patient=patient_record,
            progress=EpisodeProgress(),
            seed=seed if seed is not None else rng.randint(0, 99999),
            created_at=datetime.utcnow().isoformat(),
            difficulty_config=difficulty_config or DifficultyConfig(),
        )

        self._episodes[episode_id] = {
            "patient_data": patient_data,
            "state": state,
            "queried_sections": set(),
            "appeal_letter": None,
            "submitted_decision": None,
            "difficulty_config": difficulty_config or DifficultyConfig(),
        }

        obs = PTPAObservation(
            result=(
                f"Episode initialized for task '{task_info.name}'.\n"
                f"Patient: {name} (ID: {pid})\n"
                f"Insurer: {insurer.upper()} | Plan: {_get_plan_id(patient_data)}\n"
                f"Diagnosis: {icd10}\n"
                f"Requested: CPT {cpt}\n"
                f"You have {state.max_steps} steps. Use the available actions to gather evidence and submit your decision."
            ),
            success=True,
            step_count=0,
            done=False,
        )
        return obs, state

    # -----------------------------------------------------------------
    # step
    # -----------------------------------------------------------------
    def step(
        self,
        episode_id: str,
        action: PTPAAction,
    ) -> Tuple[PTPAObservation, float, bool, PTPAState]:
        ep = self._episodes.get(episode_id)
        if ep is None:
            raise KeyError(f"Episode not found: {episode_id}")

        state: PTPAState = ep["state"]
        patient_data = ep["patient_data"]
        queried: set = ep["queried_sections"]
        progress: EpisodeProgress = state.progress

        state.step_count += 1

        # Validate action type is allowed for this task
        task_info = get_task(state.task_id)
        valid_actions = {a.action_type for a in task_info.available_actions}
        if action.action_type not in valid_actions:
            obs = PTPAObservation(
                result=f"Action '{action.action_type.value}' is not available for task '{state.task_id.value}'.",
                success=False,
                error=f"Invalid action for task: {action.action_type.value}",
                step_count=state.step_count,
            )
            reward, reason = no_reward("Action not available for this task")
            done = state.step_count >= state.max_steps
            obs.done = done
            obs.reward = reward
            obs.reward_reason = reason
            return obs, reward, done, state

        handler = _ACTION_HANDLERS.get(action.action_type)
        if handler is None:
            obs = PTPAObservation(
                result=f"Unknown action type: {action.action_type.value}",
                success=False,
                error=f"Invalid action type: {action.action_type.value}",
                step_count=state.step_count,
            )
            reward, reason = no_reward("Invalid action")
        else:
            obs, new_info = handler(action, patient_data, ep, progress)
            obs.step_count = state.step_count

            section_key = f"{action.action_type.value}:{action.parameters.get('section', '')}"
            reward, reason = compute_step_reward(
                action_type=action.action_type.value,
                action_succeeded=obs.success,
                new_info_found=new_info,
                queried_sections=queried,
                current_section=section_key,
            )
            if new_info:
                queried.add(section_key)

            # Apply noise if configured
            config = ep.get("difficulty_config", DifficultyConfig())
            if isinstance(config, dict):
                config = DifficultyConfig(**config)
            rng = random.Random(state.seed + state.step_count)
            obs.result = _apply_noise(obs.result, config, rng)

        at = action.action_type
        state.observation_history.append(ObservationHistoryEntry(
            step_number=state.step_count,
            action_type=at,
            observation=obs.result[:500],  # truncate to prevent state bloat
            reward=reward,
        ))

        done = progress.decision_submitted or state.step_count >= state.max_steps

        obs.done = done
        obs.reward = reward
        obs.reward_reason = reason
        progress.total_reward_so_far += reward

        # NOTE: status transition (ACTIVE -> GRADING) is handled by session
        # store in app.py — engine does NOT mutate status to avoid dual
        # ownership of the state machine.

        return obs, reward, done, state

    # -----------------------------------------------------------------
    # get_state
    # -----------------------------------------------------------------
    def get_state(self, episode_id: str) -> PTPAState:
        ep = self._episodes.get(episode_id)
        if ep is None:
            raise KeyError(f"Episode not found: {episode_id}")
        return ep["state"]

    # -----------------------------------------------------------------
    # grade
    # -----------------------------------------------------------------
    def grade(self, episode_id: str) -> GraderResult:
        ep = self._episodes.get(episode_id)
        if ep is None:
            raise KeyError(f"Episode not found: {episode_id}")

        state: PTPAState = ep["state"]
        task_id = state.task_id
        pid = state.patient.patient_id
        progress = state.progress
        submitted = ep.get("submitted_decision") or {}

        if task_id == TaskID.VERIFICATION:
            return grade_task1(pid, submitted, progress, episode_id)
        elif task_id == TaskID.MRI_NECESSITY:
            return grade_task2(pid, submitted, progress, episode_id)
        elif task_id == TaskID.CGM_APPEAL:
            return grade_task3(pid, submitted, progress, ep, episode_id)
        elif task_id == TaskID.PEER_REVIEW:
            return grade_task4(pid, submitted, progress, ep, episode_id)
        else:
            raise ValueError(f"Unknown task: {task_id}")

    def get_episode_data(self, episode_id: str) -> Optional[Dict]:
        return self._episodes.get(episode_id)

    def cleanup_episode(self, episode_id: str) -> None:
        """Remove episode data to free memory after grading is complete."""
        self._episodes.pop(episode_id, None)


# =========================================================================
# ACTION HANDLERS
# =========================================================================

def _handle_query_patient_record(
    action: PTPAAction, patient: dict, ep: dict, progress: EpisodeProgress
) -> Tuple[PTPAObservation, bool]:
    section = action.parameters.get("section", "")
    data = patient.get(section)
    if data is None:
        return PTPAObservation(result=f"Unknown PRS section: {section}", success=False, error=f"Invalid section: {section}"), False

    progress.queried_sections.append(section)
    new_info = True

    if isinstance(data, list) and len(data) == 0:
        result = f"Section '{section}' is empty for this patient."
        new_info = False
    elif isinstance(data, list):
        lines = [f"  - {item}" for item in data]
        result = f"Patient record section '{section}' ({len(data)} entries):\n" + "\n".join(lines)
    elif isinstance(data, dict):
        lines = [f"  {k}: {v}" for k, v in data.items()]
        result = f"Patient record section '{section}':\n" + "\n".join(lines)
    else:
        result = f"Section '{section}': {data}"

    evidence = []
    if section == "lab_results" and isinstance(data, list):
        for lab in data:
            evidence.append(EvidenceItem(
                evidence_type="lab_result",
                label=_get_lab_test_name(lab),
                value=lab.get("value"),
                unit=lab.get("unit"),
                date=lab.get("date"),
                source_section="lab_results",
                clinically_significant=True,
            ))

    return PTPAObservation(result=result, success=True, found_evidence=evidence), new_info


def _handle_query_policy_database(
    action: PTPAAction, patient: dict, ep: dict, progress: EpisodeProgress
) -> Tuple[PTPAObservation, bool]:
    insurer = action.parameters.get("insurer", "").lower()
    section = action.parameters.get("section", "")
    policy = _POLICIES.get(insurer)
    if policy is None:
        return PTPAObservation(result=f"Unknown insurer: {insurer}", success=False, error=f"Insurer not found: {insurer}"), False

    section_data = policy.get(section)
    if section_data is None:
        return PTPAObservation(result=f"Policy section '{section}' not found for {insurer}", success=False), False

    progress.policy_retrieved = True
    cpt = action.parameters.get("cpt_code")

    if isinstance(section_data, dict) and cpt and cpt in section_data:
        detail = section_data[cpt]
        result = f"Policy [{insurer.upper()}] section '{section}' for CPT {cpt}:\n  {json.dumps(detail, indent=2)}"
        rule = PolicyRule(insurer=insurer, section=section, rule_id=f"{insurer}-{section}-{cpt}", description=json.dumps(detail))
    elif isinstance(section_data, list):
        result = f"Policy [{insurer.upper()}] section '{section}':\n"
        for item in section_data:
            result += f"  - {json.dumps(item)}\n"
        rule = PolicyRule(insurer=insurer, section=section, rule_id=f"{insurer}-{section}", description=json.dumps(section_data))
    else:
        result = f"Policy [{insurer.upper()}] section '{section}':\n  {json.dumps(section_data, indent=2)}"
        rule = PolicyRule(insurer=insurer, section=section, rule_id=f"{insurer}-{section}", description=json.dumps(section_data))

    return PTPAObservation(result=result, success=True, policy_rule=rule), True


def _handle_check_eligibility(
    action: PTPAAction, patient: dict, ep: dict, progress: EpisodeProgress
) -> Tuple[PTPAObservation, bool]:
    member_id = action.parameters.get("member_id", "")
    insurer = action.parameters.get("insurer", "").lower()

    actual_member = _get_member_id(patient)
    actual_insurer = _get_insurer(patient)
    active = _get_insurance_active(patient)

    if member_id and member_id != actual_member:
        return PTPAObservation(result=f"Member ID {member_id} not found for insurer {insurer}.", success=True), True

    progress.eligibility_verified = True
    plan_id = _get_plan_id(patient)
    status_str = "ACTIVE" if active else "INACTIVE"
    result = (
        f"Eligibility check for {actual_member} ({actual_insurer.upper()}):\n"
        f"  Status: {status_str}\n"
        f"  Plan: {plan_id}"
    )
    return PTPAObservation(result=result, success=True), True


def _handle_check_cpt_coverage(
    action: PTPAAction, patient: dict, ep: dict, progress: EpisodeProgress
) -> Tuple[PTPAObservation, bool]:
    cpt = action.parameters.get("cpt_code", "")
    icd10 = action.parameters.get("icd10_code", "")
    insurer = action.parameters.get("insurer", "").lower()

    policy = _POLICIES.get(insurer, {})
    services = policy.get("covered_services", {})
    entry = services.get(cpt)

    progress.cpt_coverage_checked = True

    if entry is None:
        result = f"CPT {cpt} not found in {insurer.upper()} covered services database."
        evidence = [EvidenceItem(
            evidence_type="policy_rule", label=f"CPT {cpt} coverage",
            value="not found", clinically_significant=True,
        )]
        return PTPAObservation(result=result, success=True, found_evidence=evidence), True

    covered = entry.get("covered", False)
    section_ref = _get_policy_section(entry)

    result = (
        f"CPT Coverage Check [{insurer.upper()}]:\n"
        f"  CPT: {cpt} | ICD-10: {icd10}\n"
        f"  Covered: {'YES' if covered else 'NO'}\n"
        f"  Policy Section: {section_ref}\n"
    )
    if entry.get("note"):
        result += f"  Note: {entry['note']}\n"
    if entry.get("requires_prior_auth"):
        result += "  Requires Prior Auth: YES\n"

    evidence = [EvidenceItem(
        evidence_type="policy_rule", label=f"CPT {cpt} coverage",
        value="covered" if covered else "not covered",
        source_section=section_ref, clinically_significant=True,
    )]
    return PTPAObservation(result=result, success=True, found_evidence=evidence), True


def _handle_extract_pt_sessions(
    action: PTPAAction, patient: dict, ep: dict, progress: EpisodeProgress
) -> Tuple[PTPAObservation, bool]:
    sessions_raw = patient.get("pt_sessions", [])
    progress.pt_sessions_extracted = True

    if not sessions_raw:
        return PTPAObservation(result="No physical therapy sessions found in patient record.", success=True), False

    pt_sessions = []
    lines = []
    for s in sessions_raw:
        pt = PTSession(
            session_date=s.get("session_date", ""),
            session_number=s.get("session_number", 0),
            therapist_notes=s.get("therapist_notes", ""),
            functional_outcome=s.get("functional_outcome"),
            pain_score=s.get("pain_score"),
            improved=s.get("improved", False),
        )
        pt_sessions.append(pt)
        lines.append(f"  Session {pt.session_number} ({pt.session_date}): {pt.therapist_notes} [pain: {pt.pain_score}]")

    first = sessions_raw[0].get("session_date", "?")
    last = sessions_raw[-1].get("session_date", "?")
    result = (
        f"Physical Therapy Sessions ({len(sessions_raw)} total):\n"
        f"  Date range: {first} to {last}\n"
        + "\n".join(lines)
    )

    evidence = [EvidenceItem(
        evidence_type="pt_session", label="PT session history",
        value=f"{len(sessions_raw)} sessions from {first} to {last}",
        source_section="pt_sessions", clinically_significant=True,
    )]

    return PTPAObservation(result=result, success=True, pt_sessions=pt_sessions, found_evidence=evidence), True


def _handle_check_red_flags(
    action: PTPAAction, patient: dict, ep: dict, progress: EpisodeProgress
) -> Tuple[PTPAObservation, bool]:
    progress.red_flags_checked = True
    red_flags = _extract_red_flags_from_patient(patient)

    if red_flags:
        lines = [f"  - {rf.flag_name}: {rf.description} (BYPASSES: {rf.bypasses_requirement})" for rf in red_flags]
        result = f"RED FLAGS DETECTED ({len(red_flags)}):\n" + "\n".join(lines)
    else:
        result = "No clinical red flags detected. Standard policy requirements apply."

    return PTPAObservation(result=result, success=True, red_flags=red_flags), True


def _handle_compare_policy_duration(
    action: PTPAAction, patient: dict, ep: dict, progress: EpisodeProgress
) -> Tuple[PTPAObservation, bool]:
    weeks = action.parameters.get("weeks_of_pt_found", 0)
    insurer = action.parameters.get("insurer", "").lower()
    cpt = action.parameters.get("cpt_code", "")

    policy = _POLICIES.get(insurer, {})
    criteria = policy.get("prior_auth_criteria", {}).get(cpt, {})
    required_weeks = _get_pt_required_weeks(criteria)

    met = weeks >= required_weeks
    result = (
        f"Policy Duration Comparison [{insurer.upper()}] CPT {cpt}:\n"
        f"  Required: {required_weeks} weeks of conservative therapy\n"
        f"  Documented: {weeks} weeks\n"
        f"  Requirement Met: {'YES' if met else 'NO'}"
    )

    evidence = [EvidenceItem(
        evidence_type="policy_rule", label="PT duration comparison",
        value=f"{weeks} vs {required_weeks} weeks", clinically_significant=True,
    )]
    return PTPAObservation(result=result, success=True, found_evidence=evidence), True


def _handle_extract_lab_values(
    action: PTPAAction, patient: dict, ep: dict, progress: EpisodeProgress
) -> Tuple[PTPAObservation, bool]:
    requested_tests = action.parameters.get("lab_tests", [])
    progress.lab_values_extracted = True

    labs = patient.get("lab_results", [])
    if not labs:
        return PTPAObservation(result="No lab results found in patient record.", success=True), False

    found = []
    evidence = []
    for lab in labs:
        test_name = _get_lab_test_name(lab)
        if test_name in requested_tests or not requested_tests:
            found.append(lab)
            evidence.append(EvidenceItem(
                evidence_type="lab_result",
                label=test_name,
                value=lab.get("value"),
                unit=lab.get("unit"),
                date=lab.get("date"),
                source_section="lab_results",
                clinically_significant=True,
            ))

    if not found:
        return PTPAObservation(result=f"No matching lab results for: {requested_tests}", success=True), False

    lines = []
    for lab in found:
        tn = _get_lab_test_name(lab)
        val = lab.get("value", "")
        unit = lab.get("unit", "")
        date = lab.get("date", "")
        ref = lab.get("reference_range", "")
        line = f"  {tn}: {val} {unit}"
        if date:
            line += f" ({date})"
        if ref:
            line += f" [ref: {ref}]"
        lines.append(line)

    result = f"Lab Values ({len(found)} results):\n" + "\n".join(lines)
    return PTPAObservation(result=result, success=True, found_evidence=evidence), True


def _handle_check_step_therapy(
    action: PTPAAction, patient: dict, ep: dict, progress: EpisodeProgress
) -> Tuple[PTPAObservation, bool]:
    device = action.parameters.get("device_requested", "CGM")
    insurer = action.parameters.get("insurer", "").lower()
    progress.step_therapy_checked = True

    pharmacy = patient.get("pharmacy_history", [])
    insulin_injections = _count_insulin_injections(pharmacy)

    policy = _POLICIES.get(insurer, {})
    step_rules = _get_step_therapy_rules(policy, device)
    required = step_rules.get("min_insulin_injections_per_day",
                              step_rules.get("min_daily_insulin_injections", 2))
    met = insulin_injections >= required

    result = (
        f"Step Therapy Check [{insurer.upper()}] for {device}:\n"
        f"  Required: >= {required} daily insulin injections\n"
        f"  Found: {insulin_injections} daily insulin administrations\n"
        f"  Step Therapy Met: {'YES' if met else 'NO'}"
    )
    if not met:
        result += "\n  Note: Patient does not meet insulin injection requirement for CGM coverage."

    evidence = [EvidenceItem(
        evidence_type="policy_rule", label="Step therapy compliance",
        value="met" if met else "not met", clinically_significant=True,
    )]
    return PTPAObservation(result=result, success=True, found_evidence=evidence), True


def _handle_generate_appeal_letter(
    action: PTPAAction, patient: dict, ep: dict, progress: EpisodeProgress
) -> Tuple[PTPAObservation, bool]:
    evidence_found = action.parameters.get("evidence_found", [])
    exception_clause = action.parameters.get("exception_clause", "")
    physician_name = action.parameters.get("physician_name", patient.get("attending_physician", "Attending Physician"))
    physician_npi = action.parameters.get("physician_npi", "1234567890")

    demo = patient.get("demographics", {})
    ins = patient.get("insurance", {})
    proc = patient.get("requested_procedure", {})
    dx = patient.get("diagnosis_codes", [{}])[0]

    letter = (
        f"LETTER OF MEDICAL NECESSITY\n"
        f"{'='*50}\n"
        f"Date: {datetime.utcnow().strftime('%Y-%m-%d')}\n"
        f"To: {ins.get('insurer', '').upper()} Medical Review Department\n"
        f"Re: Appeal for CPT {proc.get('cpt_code', '')}\n"
        f"Patient: {demo.get('name', '')} | Member ID: {ins.get('member_id', '')}\n"
        f"Diagnosis: ICD-10: {dx.get('code', '')}\n\n"
        f"Dear Medical Review Team,\n\n"
        f"I am writing to appeal the denial of the requested procedure for my patient "
        f"{demo.get('name', '')}. Based on the following clinical evidence, this patient meets "
        f"the criteria for a medical exception under {exception_clause}.\n\n"
        f"Clinical Evidence:\n"
    )
    for e in evidence_found:
        letter += f"  - {e}\n"

    letter += (
        f"\nThis evidence demonstrates that the patient meets the specific exception criteria "
        f"outlined in {exception_clause}. The requested device is medically necessary for "
        f"safe and effective management of the patient's condition.\n\n"
        f"Respectfully,\n"
        f"{physician_name}\n"
        f"NPI: {physician_npi}\n"
    )

    ep["appeal_letter"] = letter
    result = f"Appeal letter generated ({len(letter)} characters).\n\nLetter preview:\n{letter[:500]}..."

    return PTPAObservation(result=result, success=True), True


def _handle_submit_decision(
    action: PTPAAction, patient: dict, ep: dict, progress: EpisodeProgress
) -> Tuple[PTPAObservation, bool]:
    decision = action.parameters.get("decision", "")
    rationale = action.parameters.get("rationale", "")

    if len(rationale) < 20:
        return PTPAObservation(
            result="Rationale must be at least 20 characters.",
            success=False,
            error="Rationale too short (min 20 chars)",
        ), False

    progress.decision_submitted = True
    ep["submitted_decision"] = action.parameters

    result = (
        f"Decision submitted: {decision.upper()}\n"
        f"Rationale: {rationale}\n"
        f"Episode complete. Call POST /grader to receive your score."
    )
    return PTPAObservation(result=result, success=True), True


def _apply_noise(obs_text: str, config: DifficultyConfig, rng: random.Random) -> str:
    """Apply noise/ambiguity to observation text based on difficulty config."""
    if config.noise_level == "none" and not config.missing_data and not config.conflicting_notes:
        return obs_text

    result = obs_text

    if config.missing_data and rng.random() < 0.3:
        lines = result.split("\n")
        if len(lines) > 2:
            idx = rng.randint(1, len(lines) - 1)
            lines[idx] = "  [DATA UNAVAILABLE — record not found in system]"
            result = "\n".join(lines)

    if config.conflicting_notes and rng.random() < 0.25:
        result += "\n  NOTE: A separate progress note from a different provider contains a contradictory assessment."

    if config.noise_level == "low" and rng.random() < 0.2:
        result += "\n  [System note: Some fields may have been updated since last retrieval]"
    elif config.noise_level == "medium" and rng.random() < 0.35:
        result += "\n  WARNING: Record last synced 48 hours ago. Some values may be outdated."
    elif config.noise_level == "high" and rng.random() < 0.5:
        result += "\n  CAUTION: Multiple data sources detected. Values may differ between EMR systems."
        if rng.random() < 0.3:
            lines = result.split("\n")
            if len(lines) > 3:
                idx = rng.randint(1, len(lines) - 1)
                lines[idx] = lines[idx] + " [UNVERIFIED]"
                result = "\n".join(lines)

    if config.ambiguous_labs and rng.random() < 0.3:
        result += "\n  Note: Some lab values are near clinical decision thresholds. Consider repeat testing."

    return result


def _handle_review_denial_letter(action, patient, ep, progress):
    denial = patient.get("denial_letter")
    if not denial:
        return PTPAObservation(result="No denial letter found for this patient.", success=False), False

    result = (
        f"DENIAL LETTER\n"
        f"{'='*50}\n"
        f"Date: {denial.get('date', 'N/A')}\n"
        f"Insurer: {denial.get('insurer', 'N/A').upper()}\n"
        f"Denial Code: {denial.get('denial_code', 'N/A')}\n"
        f"Reviewing Physician: {denial.get('reviewer', 'N/A')}\n"
        f"\nReason for Denial:\n  {denial.get('reason', 'No reason provided')}\n"
    )
    progress.policy_retrieved = True
    return PTPAObservation(result=result, success=True), True


def _handle_gather_counter_evidence(action, patient, ep, progress):
    sections = action.parameters.get("sections", [])
    focus = action.parameters.get("focus_area", "")

    evidence_parts = []
    for section in sections:
        data = patient.get(section)
        if data is None:
            evidence_parts.append(f"Section '{section}': not found")
            continue
        if isinstance(data, list) and len(data) == 0:
            evidence_parts.append(f"Section '{section}': empty")
            continue
        if isinstance(data, list):
            for item in data[:5]:  # limit to 5 entries
                evidence_parts.append(f"  [{section}] {item}")
        elif isinstance(data, dict):
            for k, v in data.items():
                evidence_parts.append(f"  [{section}] {k}: {v}")

    if not evidence_parts:
        return PTPAObservation(result="No evidence found in the requested sections.", success=True), False

    result = f"Counter-evidence gathered (focus: {focus}):\n" + "\n".join(evidence_parts)

    # Update progress flags based on what was gathered
    for s in sections:
        if s == "pt_sessions":
            progress.pt_sessions_extracted = True
        elif s == "lab_results":
            progress.lab_values_extracted = True
        elif s == "physical_exam":
            progress.red_flags_checked = True

    return PTPAObservation(result=result, success=True), True


def _handle_submit_rebuttal(action, patient, ep, progress):
    points = action.parameters.get("rebuttal_points", [])
    recommended = action.parameters.get("recommended_action", "")
    rationale = action.parameters.get("rationale", "")

    if not points or len(points) == 0:
        return PTPAObservation(result="Rebuttal must include at least one point.", success=False, error="Empty rebuttal"), False

    if recommended not in ("overturn", "uphold"):
        return PTPAObservation(result=f"recommended_action must be 'overturn' or 'uphold', got '{recommended}'", success=False), False

    if len(rationale) < 20:
        return PTPAObservation(result="Rationale must be at least 20 characters.", success=False), False

    progress.decision_submitted = True
    ep["submitted_decision"] = {
        "rebuttal_points": points,
        "recommended_action": recommended,
        "rationale": rationale,
        "decision": "appeal" if recommended == "overturn" else "deny",
    }

    result = (
        f"Rebuttal submitted: {recommended.upper()}\n"
        f"Points: {len(points)}\n"
        f"Rationale: {rationale}\n"
        f"Episode complete. Call POST /grader to receive your score."
    )
    return PTPAObservation(result=result, success=True), True


_ACTION_HANDLERS = {
    ActionType.QUERY_PATIENT_RECORD:    _handle_query_patient_record,
    ActionType.QUERY_POLICY_DATABASE:   _handle_query_policy_database,
    ActionType.CHECK_ELIGIBILITY:       _handle_check_eligibility,
    ActionType.CHECK_CPT_COVERAGE:      _handle_check_cpt_coverage,
    ActionType.EXTRACT_PT_SESSIONS:     _handle_extract_pt_sessions,
    ActionType.CHECK_RED_FLAGS:         _handle_check_red_flags,
    ActionType.COMPARE_POLICY_DURATION: _handle_compare_policy_duration,
    ActionType.EXTRACT_LAB_VALUES:      _handle_extract_lab_values,
    ActionType.CHECK_STEP_THERAPY:      _handle_check_step_therapy,
    ActionType.GENERATE_APPEAL_LETTER:  _handle_generate_appeal_letter,
    ActionType.SUBMIT_DECISION:         _handle_submit_decision,
    ActionType.REVIEW_DENIAL_LETTER:    _handle_review_denial_letter,
    ActionType.GATHER_COUNTER_EVIDENCE: _handle_gather_counter_evidence,
    ActionType.SUBMIT_REBUTTAL:         _handle_submit_rebuttal,
}




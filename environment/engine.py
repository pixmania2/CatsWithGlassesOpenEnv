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
    AuthorizationDecision,
    EpisodeProgress,
    EpisodeStatus,
    EvidenceItem,
    GraderComponentScore,
    GraderResult,
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
    ALL_TASKS,
    TASK1_ANSWER_KEYS,
    TASK2_ANSWER_KEYS,
    TASK3_ANSWER_KEYS,
    get_max_steps,
    get_task,
)
from environment.rewards import compute_step_reward, no_reward


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
    TaskID.VERIFICATION:  list(TASK1_ANSWER_KEYS.keys()),
    TaskID.MRI_NECESSITY: list(TASK2_ANSWER_KEYS.keys()),
    TaskID.CGM_APPEAL:    list(TASK3_ANSWER_KEYS.keys()),
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
        )

        self._episodes[episode_id] = {
            "patient_data": patient_data,
            "state": state,
            "queried_sections": set(),
            "appeal_letter": None,
            "submitted_decision": None,
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
            return _grade_task1(pid, submitted, progress, episode_id)
        elif task_id == TaskID.MRI_NECESSITY:
            return _grade_task2(pid, submitted, progress, episode_id)
        elif task_id == TaskID.CGM_APPEAL:
            return _grade_task3(pid, submitted, progress, ep, episode_id)
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
        result += f"  Requires Prior Auth: YES\n"

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
}


# =========================================================================
# GRADERS
# =========================================================================

def _grade_task1(pid: str, submitted: dict, progress: EpisodeProgress, episode_id: str) -> GraderResult:
    key = TASK1_ANSWER_KEYS.get(pid, {})
    correct_decision = key.get("decision")
    agent_decision_str = submitted.get("decision", "")

    elig_score = 1.0 if progress.eligibility_verified else 0.0
    cov_score = 1.0 if progress.cpt_coverage_checked else 0.0

    try:
        agent_decision = AuthorizationDecision(agent_decision_str)
        decision_correct = agent_decision == correct_decision
    except ValueError:
        agent_decision = None
        decision_correct = False

    if not decision_correct:
        elig_score *= 0.5
        cov_score *= 0.5

    rationale = submitted.get("rationale", "")
    correct_section = key.get("correct_policy_section", "")
    if correct_section and correct_section.lower() in rationale.lower():
        rat_score = 1.0
    elif key.get("insurer", "") in rationale.lower():
        rat_score = 0.5
    else:
        rat_score = 0.0

    components = [
        GraderComponentScore(component_name="eligibility_status", weight=0.40, score=elig_score, weighted_score=0.40 * elig_score, passed=elig_score > 0.5, feedback=f"Eligibility verified: {progress.eligibility_verified}"),
        GraderComponentScore(component_name="procedure_coverage", weight=0.40, score=cov_score, weighted_score=0.40 * cov_score, passed=cov_score > 0.5, feedback=f"CPT coverage checked: {progress.cpt_coverage_checked}"),
        GraderComponentScore(component_name="policy_rationale", weight=0.20, score=rat_score, weighted_score=0.20 * rat_score, passed=rat_score > 0.5, feedback=f"Rationale quality: {rat_score}"),
    ]
    final = sum(c.weighted_score for c in components)

    return GraderResult(
        task_id=TaskID.VERIFICATION, episode_id=episode_id,
        final_score=round(final, 4), components=components,
        decision_made=agent_decision, decision_correct=decision_correct,
        feedback=f"Decision: {agent_decision_str} | Correct: {correct_decision.value if correct_decision else 'N/A'} | Score: {final:.2f}",
    )


def _grade_task2(pid: str, submitted: dict, progress: EpisodeProgress, episode_id: str) -> GraderResult:
    key = TASK2_ANSWER_KEYS.get(pid, {})
    correct_decision = key.get("decision")
    agent_decision_str = submitted.get("decision", "")

    try:
        agent_decision = AuthorizationDecision(agent_decision_str)
        decision_correct = agent_decision == correct_decision
    except ValueError:
        agent_decision = None
        decision_correct = False

    ev_score = 1.0 if progress.pt_sessions_extracted else 0.0

    dur_score = 0.0
    if progress.policy_retrieved:
        dur_score = 0.5
    if decision_correct:
        dur_score = 1.0

    rf_score = 0.0
    if progress.red_flags_checked:
        rf_score = 1.0

    dec_score = 1.0 if decision_correct else 0.0

    components = [
        GraderComponentScore(component_name="evidence_extraction", weight=0.35, score=ev_score, weighted_score=0.35 * ev_score, passed=ev_score > 0.5, feedback=f"PT sessions extracted: {progress.pt_sessions_extracted}"),
        GraderComponentScore(component_name="policy_duration_logic", weight=0.30, score=dur_score, weighted_score=0.30 * dur_score, passed=dur_score > 0.5, feedback=f"Duration logic score: {dur_score}"),
        GraderComponentScore(component_name="red_flag_recognition", weight=0.20, score=rf_score, weighted_score=0.20 * rf_score, passed=rf_score > 0.5, feedback=f"Red flags checked: {progress.red_flags_checked}"),
        GraderComponentScore(component_name="final_decision_accuracy", weight=0.15, score=dec_score, weighted_score=0.15 * dec_score, passed=decision_correct, feedback=f"Decision correct: {decision_correct}"),
    ]
    final = sum(c.weighted_score for c in components)

    return GraderResult(
        task_id=TaskID.MRI_NECESSITY, episode_id=episode_id,
        final_score=round(final, 4), components=components,
        decision_made=agent_decision, decision_correct=decision_correct,
        feedback=f"Decision: {agent_decision_str} | Correct: {correct_decision.value if correct_decision else 'N/A'} | Score: {final:.2f}",
    )


def _grade_task3(pid: str, submitted: dict, progress: EpisodeProgress, ep: dict, episode_id: str) -> GraderResult:
    key = TASK3_ANSWER_KEYS.get(pid, {})
    correct_decision = key.get("decision")
    agent_decision_str = submitted.get("decision", "")

    try:
        agent_decision = AuthorizationDecision(agent_decision_str)
        decision_correct = agent_decision == correct_decision
    except ValueError:
        agent_decision = None
        decision_correct = False

    # Metric identification (40%)
    metric_score = 0.0
    if progress.lab_values_extracted:
        metric_score = 0.5
        rationale = submitted.get("rationale", "")
        qv = key.get("qualifying_value")
        if qv is not None and str(int(qv)) in rationale:
            metric_score = 1.0
        elif key.get("exception_type") and key["exception_type"].replace("_", " ") in rationale.lower():
            metric_score = 0.75

    # Rationale mapping (30%)
    rat_score = 0.0
    correct_clause = key.get("correct_exception_clause", "") or ""
    rationale = submitted.get("rationale", "")
    policy_cited = submitted.get("policy_section_cited", "")
    if correct_clause:
        if correct_clause.lower() in rationale.lower() or correct_clause.lower() in policy_cited.lower():
            rat_score = 1.0
        elif key.get("insurer", "") in rationale.lower() and "exception" in rationale.lower():
            rat_score = 0.5

    # Appeal letter quality (30%)
    letter_score = 0.0
    letter = ep.get("appeal_letter", "")
    if letter:
        checks = 0
        patient_data = ep.get("patient_data", {})
        if any(dx.get("code", "") in letter for dx in patient_data.get("diagnosis_codes", [])):
            checks += 1
        for lab in patient_data.get("lab_results", []):
            if str(lab.get("value", "")) in letter:
                checks += 1
                break
        if correct_clause and any(word in letter.lower() for word in correct_clause.lower().split()[:3]):
            checks += 1
        if "dear" in letter.lower() or "to:" in letter.lower():
            checks += 1
        if "npi" in letter.lower() or "respectfully" in letter.lower():
            checks += 1
        letter_score = checks / 5.0

    components = [
        GraderComponentScore(component_name="metric_identification", weight=0.40, score=metric_score, weighted_score=0.40 * metric_score, passed=metric_score > 0.5, feedback=f"Metric identification: {metric_score}"),
        GraderComponentScore(component_name="rationale_mapping", weight=0.30, score=rat_score, weighted_score=0.30 * rat_score, passed=rat_score > 0.5, feedback=f"Rationale mapping: {rat_score}"),
        GraderComponentScore(component_name="appeal_letter_quality", weight=0.30, score=letter_score, weighted_score=0.30 * letter_score, passed=letter_score > 0.5, feedback=f"Appeal letter score: {letter_score}"),
    ]
    final = sum(c.weighted_score for c in components)

    return GraderResult(
        task_id=TaskID.CGM_APPEAL, episode_id=episode_id,
        final_score=round(final, 4), components=components,
        decision_made=agent_decision, decision_correct=decision_correct,
        feedback=f"Decision: {agent_decision_str} | Correct: {correct_decision.value if correct_decision else 'N/A'} | Score: {final:.2f}",
        appeal_letter_score=round(letter_score, 4),
    )

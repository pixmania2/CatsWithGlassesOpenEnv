from datetime import datetime

from models import PTPAObservation
from environment.rewards import compute_reward


def parse_date(date_str):
    return datetime.strptime(date_str, "%Y-%m-%d")


def compute_pt_weeks(patient):
    sessions = patient.get("pt_sessions", [])

    if len(sessions) < 2:
        return 0

    dates = [parse_date(s["session_date"]) for s in sessions]
    duration_days = (max(dates) - min(dates)).days

    return round(duration_days / 7, 2)


def check_red_flag(patient):
    exams = patient.get("physical_exam", [])

    for exam in exams:
        if "True Locking" in exam.get("red_flags", []):
            return True

    return False


def get_required_weeks(patient, ipd):
    insurer = patient["insurance"]["insurer"]
    cpt = patient["requested_procedure"]["cpt_code"]

    return ipd[insurer]["prior_auth_criteria"][cpt]["pt_required_weeks"]


# --------------------------------------------------
# MAIN HANDLER (THIS WAS MISSING / WRONG)
# --------------------------------------------------

def handle_task2_action(action, state, prs, ipd):
    patient = prs[state.patient.patient_id]

    if action.action_type == "extract_pt_sessions":
        count = len(patient.get("pt_sessions", []))

        return PTPAObservation(
            result=f"Extracted {count} PT sessions",
            success=True,
            reward=compute_reward("evidence_reward"),
            step_count=state.step_count,
            done=False
        )

    elif action.action_type == "check_red_flags":
        has_flag = check_red_flag(patient)

        return PTPAObservation(
            result=f"Red flag present={has_flag}",
            success=True,
            reward=compute_reward("logic_reward"),
            step_count=state.step_count,
            done=False
        )

    elif action.action_type == "compare_policy_duration":
        weeks = compute_pt_weeks(patient)
        required = get_required_weeks(patient, ipd)

        meets = weeks >= required

        return PTPAObservation(
            result=f"PT duration={weeks}, required={required}, meets={meets}",
            success=True,
            reward=compute_reward("logic_reward"),
            step_count=state.step_count,
            done=False
        )

    elif action.action_type == "submit_decision":
        weeks = compute_pt_weeks(patient)
        required = get_required_weeks(patient, ipd)
        has_flag = check_red_flag(patient)

        # FINAL DECISION LOGIC
        if has_flag:
            correct = action.parameters["decision"] == "approve"
        else:
            correct = (weeks >= required and action.parameters["decision"] == "approve") or \
                      (weeks < required and action.parameters["decision"] == "deny")

        return PTPAObservation(
            result=f"Decision correct={correct}",
            success=True,
            reward=compute_reward("success_reward") if correct else 0.0,
            step_count=state.step_count,
            done=True
        )

    else:
        return PTPAObservation(
            result="Invalid action",
            success=False,
            reward=0.0,
            step_count=state.step_count,
            done=False
        )
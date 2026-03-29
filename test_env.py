from environment.engine import EnvironmentEngine
from models import PTPAAction, TaskID


engine = EnvironmentEngine()

# =====================================================
# TASK 1 VALIDATION
# =====================================================

print("\n========== TASK 1 ==========")

for pid in ["PAT-001", "PAT-002", "PAT-003"]:
    print(f"\n--- Testing {pid} ---")

    engine.reset(TaskID.VERIFICATION, pid)

    # -------------------------
    # ELIGIBILITY
    # -------------------------
    eligibility_obs = engine.step(PTPAAction(
        action_type="check_eligibility",
        patient_id=pid,
        task_id=TaskID.VERIFICATION,
        parameters={}
    ))
    print(eligibility_obs.result)
    eligibility_result = eligibility_obs.result

    # -------------------------
    # COVERAGE
    # -------------------------
    coverage_obs = engine.step(PTPAAction(
        action_type="check_cpt_coverage",
        patient_id=pid,
        task_id=TaskID.VERIFICATION,
        parameters={}
    ))
    print(coverage_obs.result)
    coverage_result = coverage_obs.result

    # -------------------------
    # DECISION LOGIC (CORRECT)
    # -------------------------
    if "active=False" in eligibility_result:
        decision = "deny"
    elif "covered=True" in coverage_result:
        decision = "approve"
    else:
        decision = "deny"

    # -------------------------
    # SUBMIT
    # -------------------------
    obs = engine.step(PTPAAction(
        action_type="submit_decision",
        patient_id=pid,
        task_id=TaskID.VERIFICATION,
        parameters={
            "decision": decision,
            "policy_section_cited": "Section 4.2 Covered Services"
        }
    ))

    print(obs.result)


# =====================================================
# TASK 2 VALIDATION
# =====================================================

print("\n========== TASK 2 ==========")

for pid in ["PAT-006", "PAT-007", "PAT-011"]:
    print(f"\n--- Testing {pid} ---")

    engine.reset(TaskID.MRI_NECESSITY, pid)

    # -------------------------
    # PT EXTRACTION
    # -------------------------
    obs = engine.step(PTPAAction(
        action_type="extract_pt_sessions",
        patient_id=pid,
        task_id=TaskID.MRI_NECESSITY,
        parameters={}
    ))
    print(obs.result)

    # -------------------------
    # RED FLAGS
    # -------------------------
    obs = engine.step(PTPAAction(
        action_type="check_red_flags",
        patient_id=pid,
        task_id=TaskID.MRI_NECESSITY,
        parameters={}
    ))
    print(obs.result)
    red_flag_result = obs.result

    # -------------------------
    # PT DURATION
    # -------------------------
    obs = engine.step(PTPAAction(
        action_type="compare_policy_duration",
        patient_id=pid,
        task_id=TaskID.MRI_NECESSITY,
        parameters={}
    ))
    print(obs.result)
    duration_result = obs.result

    # -------------------------
    # DECISION LOGIC (CORRECT)
    # -------------------------
    if "Red flag present=True" in red_flag_result:
        decision = "approve"
    elif "meets=True" in duration_result:
        decision = "approve"
    else:
        decision = "deny"

    # -------------------------
    # SUBMIT
    # -------------------------
    obs = engine.step(PTPAAction(
        action_type="submit_decision",
        patient_id=pid,
        task_id=TaskID.MRI_NECESSITY,
        parameters={
            "decision": decision
        }
    ))

    print(obs.result)
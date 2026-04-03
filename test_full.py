"""
Full validation test — all 15 patients, all 3 tasks, server endpoints.
Run: python test_full.py
"""
import sys

# Force data reload
if "environment.engine" in sys.modules:
    del sys.modules["environment.engine"]

from environment.engine import PTPAEngine, _PATIENTS, _POLICIES
from models import PTPAAction, ActionType, TaskID
from tasks import TASK1_ANSWER_KEYS, TASK2_ANSWER_KEYS, TASK3_ANSWER_KEYS

engine = PTPAEngine()
failures = []
passes = 0


def check(condition, msg):
    global passes
    if condition:
        passes += 1
    else:
        failures.append(msg)
        print(f"  FAIL: {msg}")


# =====================================================
# 1. DATA INTEGRITY
# =====================================================
print("=" * 60)
print("1. DATA INTEGRITY")
print("=" * 60)

check(len(_PATIENTS) >= 15, f"Expected >= 15 patients, got {len(_PATIENTS)}")
check(len(_POLICIES) >= 3, f"Expected >= 3 policies, got {len(_POLICIES)}")
check("united" in _POLICIES, "Missing united policy")

for pid in list(TASK1_ANSWER_KEYS) + list(TASK2_ANSWER_KEYS) + list(TASK3_ANSWER_KEYS):
    check(pid in _PATIENTS, f"Missing patient fixture: {pid}")

# Insurer alignment
for pid, key in TASK1_ANSWER_KEYS.items():
    if pid in _PATIENTS:
        data_ins = _PATIENTS[pid].get("insurance", {}).get("insurer", "")
        check(data_ins == key["insurer"], f"{pid}: insurer mismatch data={data_ins} key={key['insurer']}")

for pid, key in TASK2_ANSWER_KEYS.items():
    if pid in _PATIENTS:
        data_ins = _PATIENTS[pid].get("insurance", {}).get("insurer", "")
        check(data_ins == key["insurer"], f"{pid}: insurer mismatch data={data_ins} key={key['insurer']}")

for pid, key in TASK3_ANSWER_KEYS.items():
    if pid in _PATIENTS:
        data_ins = _PATIENTS[pid].get("insurance", {}).get("insurer", "")
        check(data_ins == key["insurer"], f"{pid}: insurer mismatch data={data_ins} key={key['insurer']}")

print(f"  Data integrity: {passes} checks passed")


# =====================================================
# 2. TASK 1 — VERIFICATION (all 5 patients)
# =====================================================
print("\n" + "=" * 60)
print("2. TASK 1 — VERIFICATION")
print("=" * 60)

for pid in ["PAT-001", "PAT-002", "PAT-003", "PAT-004", "PAT-005"]:
    key = TASK1_ANSWER_KEYS[pid]
    p = _PATIENTS[pid]
    eid = f"t1-{pid}"

    obs, state = engine.reset(eid, TaskID.VERIFICATION, seed=42, patient_id=pid)
    check(state.patient.patient_id == pid, f"{pid}: wrong patient assigned")

    # Eligibility
    obs, r, d, s = engine.step(eid, PTPAAction(
        action_type=ActionType.CHECK_ELIGIBILITY, patient_id=pid,
        task_id=TaskID.VERIFICATION,
        parameters={"member_id": state.patient.member_id, "insurer": state.patient.insurer},
    ))

    # CPT Coverage
    obs, r, d, s = engine.step(eid, PTPAAction(
        action_type=ActionType.CHECK_CPT_COVERAGE, patient_id=pid,
        task_id=TaskID.VERIFICATION,
        parameters={"cpt_code": state.patient.requested_cpt, "icd10_code": state.patient.primary_icd10, "insurer": state.patient.insurer},
    ))

    # Determine correct decision
    decision = key["decision"].value

    # Submit
    obs, r, d, s = engine.step(eid, PTPAAction(
        action_type=ActionType.SUBMIT_DECISION, patient_id=pid,
        task_id=TaskID.VERIFICATION,
        parameters={"decision": decision, "rationale": f"Based on eligibility and coverage per {key.get('correct_policy_section', 'Section 4.2 Covered Services')}."},
    ))
    check(d, f"{pid}: episode should be done after submit")

    result = engine.grade(eid)
    check(result.decision_correct, f"{pid}: decision should be correct (expected {decision})")
    check(result.final_score >= 0.6, f"{pid}: score {result.final_score} too low")
    print(f"  {pid}: score={result.final_score:.2f} correct={result.decision_correct} decision={decision}")


# =====================================================
# 3. TASK 2 — MRI NECESSITY (all 5 patients)
# =====================================================
print("\n" + "=" * 60)
print("3. TASK 2 — MRI NECESSITY")
print("=" * 60)

for pid in ["PAT-006", "PAT-007", "PAT-008", "PAT-009", "PAT-010"]:
    key = TASK2_ANSWER_KEYS[pid]
    eid = f"t2-{pid}"

    obs, state = engine.reset(eid, TaskID.MRI_NECESSITY, seed=42, patient_id=pid)

    # Extract PT sessions
    obs, r, d, s = engine.step(eid, PTPAAction(
        action_type=ActionType.EXTRACT_PT_SESSIONS, patient_id=pid,
        task_id=TaskID.MRI_NECESSITY, parameters={},
    ))

    # Check red flags
    obs, r, d, s = engine.step(eid, PTPAAction(
        action_type=ActionType.CHECK_RED_FLAGS, patient_id=pid,
        task_id=TaskID.MRI_NECESSITY, parameters={},
    ))
    has_rf = len(obs.red_flags) > 0
    expected_rf = key.get("red_flag_present", False)
    check(has_rf == expected_rf, f"{pid}: red_flag expected={expected_rf} got={has_rf}")

    decision = key["decision"].value
    obs, r, d, s = engine.step(eid, PTPAAction(
        action_type=ActionType.SUBMIT_DECISION, patient_id=pid,
        task_id=TaskID.MRI_NECESSITY,
        parameters={"decision": decision, "rationale": f"Based on PT duration analysis and red flag check for {pid}. Policy requirement evaluation complete."},
    ))

    result = engine.grade(eid)
    check(result.decision_correct, f"{pid}: decision should be correct (expected {decision})")
    check(result.final_score >= 0.5, f"{pid}: score {result.final_score} too low")
    print(f"  {pid}: score={result.final_score:.2f} correct={result.decision_correct} decision={decision} rf={has_rf}")


# =====================================================
# 4. TASK 3 — CGM APPEAL (all 5 patients)
# =====================================================
print("\n" + "=" * 60)
print("4. TASK 3 — CGM APPEAL")
print("=" * 60)

for pid in ["PAT-011", "PAT-012", "PAT-013", "PAT-014", "PAT-015"]:
    key = TASK3_ANSWER_KEYS[pid]
    eid = f"t3-{pid}"

    obs, state = engine.reset(eid, TaskID.CGM_APPEAL, seed=42, patient_id=pid)

    # Extract labs
    obs, r, d, s = engine.step(eid, PTPAAction(
        action_type=ActionType.EXTRACT_LAB_VALUES, patient_id=pid,
        task_id=TaskID.CGM_APPEAL,
        parameters={"lab_tests": ["HbA1c", "fasting_glucose", "glucose_reading"]},
    ))

    # Check step therapy
    obs, r, d, s = engine.step(eid, PTPAAction(
        action_type=ActionType.CHECK_STEP_THERAPY, patient_id=pid,
        task_id=TaskID.CGM_APPEAL,
        parameters={"device_requested": "CGM", "insurer": state.patient.insurer},
    ))

    decision = key["decision"].value
    qv = key.get("qualifying_value", "")
    exc = key.get("correct_exception_clause", "")
    rationale = f"Based on lab analysis. Qualifying value: {qv}. {exc}. Decision: {decision}."

    # Generate appeal letter for appeal decisions
    if decision == "appeal":
        obs, r, d, s = engine.step(eid, PTPAAction(
            action_type=ActionType.GENERATE_APPEAL_LETTER, patient_id=pid,
            task_id=TaskID.CGM_APPEAL,
            parameters={
                "evidence_found": [f"Qualifying value: {qv}", f"Exception: {exc}"],
                "exception_clause": exc,
            },
        ))

    obs, r, d, s = engine.step(eid, PTPAAction(
        action_type=ActionType.SUBMIT_DECISION, patient_id=pid,
        task_id=TaskID.CGM_APPEAL,
        parameters={"decision": decision, "rationale": rationale, "policy_section_cited": exc},
    ))

    result = engine.grade(eid)
    check(result.decision_correct, f"{pid}: decision should be correct (expected {decision})")
    print(f"  {pid}: score={result.final_score:.2f} correct={result.decision_correct} decision={decision}")


# =====================================================
# 5. SERVER ENDPOINT CHECKS
# =====================================================
print("\n" + "=" * 60)
print("5. SERVER IMPORTS & MODELS")
print("=" * 60)

try:
    from server.session import SessionStore
    store = SessionStore()
    check(True, "")
    print("  SessionStore: OK")
except Exception as e:
    check(False, f"SessionStore import failed: {e}")

try:
    from tasks import get_all_tasks
    tasks = get_all_tasks()
    check(len(tasks) == 3, f"Expected 3 tasks, got {len(tasks)}")
    print(f"  Tasks: {len(tasks)} loaded")
except Exception as e:
    check(False, f"get_all_tasks failed: {e}")

try:
    from environment.task3_cgm_appeal import check_dawn_phenomenon, check_hypoglycemic_unawareness
    dawn = check_dawn_phenomenon(_PATIENTS["PAT-011"].get("lab_results", []))
    check(dawn["met"], "PAT-011 should meet dawn phenomenon threshold")
    hypo = check_hypoglycemic_unawareness(_PATIENTS["PAT-012"].get("lab_results", []))
    check(hypo["met"], "PAT-012 should meet hypoglycemic unawareness threshold")
    print(f"  task3_cgm_appeal: OK (PAT-011 dawn={dawn['met']}, PAT-012 hypo={hypo['met']})")
except Exception as e:
    check(False, f"task3_cgm_appeal import failed: {e}")

try:
    import yaml
    with open("openenv.yaml") as f:
        manifest = yaml.safe_load(f)
    check("name" in manifest, "openenv.yaml missing 'name'")
    check("version" in manifest, "openenv.yaml missing 'version'")
    print(f"  openenv.yaml: OK (name={manifest.get('name')}, version={manifest.get('version')})")
except Exception as e:
    check(False, f"openenv.yaml check failed: {e}")


# =====================================================
# SUMMARY
# =====================================================
print("\n" + "=" * 60)
print(f"RESULTS: {passes} passed, {len(failures)} failed")
print("=" * 60)
if failures:
    print("\nFailures:")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
else:
    print("\nAll checks passed!")
    sys.exit(0)

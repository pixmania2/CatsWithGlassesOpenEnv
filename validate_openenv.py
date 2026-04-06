"""
validate_openenv.py — Pre-submission validator for OpenEnv hackathon.

Simulates the automated checks from the judging criteria:
  1. HF Space deploys and responds to reset()
  2. OpenEnv spec compliance (openenv.yaml, typed models, endpoints)
  3. Dockerfile builds
  4. Baseline reproduces
  5. 3+ tasks with graders (scores 0.0–1.0)
  6. /baseline, /grader, /tasks endpoints

Usage:
    python validate_openenv.py                              # test local (localhost:8000)
    python validate_openenv.py --url https://YOUR.hf.space  # test live HF Space
"""

import sys
import os
import yaml
import httpx

URL = "http://localhost:8000"
if "--url" in sys.argv:
    URL = sys.argv[sys.argv.index("--url") + 1]

passed = 0
failed = 0
errors = []


def check(ok, label, detail=""):
    global passed, failed
    if ok:
        passed += 1
        print(f"  PASS  {label}")
    else:
        failed += 1
        errors.append(f"{label}: {detail}")
        print(f"  FAIL  {label} — {detail}")


print("=" * 60)
print(f"OpenEnv Pre-Submission Validator")
print(f"Target: {URL}")
print("=" * 60)

client = httpx.Client(base_url=URL, timeout=30)

# ---------------------------------------------------------------
# 1. HF Space deploys — must return 200 and respond to reset()
# ---------------------------------------------------------------
print("\n--- 1. Deployment & Health ---")
try:
    r = client.get("/health")
    check(r.status_code == 200, "GET /health returns 200", f"got {r.status_code}")
    d = r.json()
    check(d.get("status") == "healthy", "Health status is 'healthy'", f"got {d.get('status')}")
except Exception as e:
    check(False, "GET /health reachable", str(e))

try:
    r = client.post("/reset")
    check(r.status_code == 200, "POST /reset (empty body) returns 200", f"got {r.status_code}")
    d = r.json()
    check("episode_id" in d, "Reset returns episode_id")
    check("initial_observation" in d, "Reset returns initial_observation")
    check("state" in d, "Reset returns state")
except Exception as e:
    check(False, "POST /reset (empty body)", str(e))

# ---------------------------------------------------------------
# 2. OpenEnv spec compliance
# ---------------------------------------------------------------
print("\n--- 2. OpenEnv Spec Compliance ---")

# openenv.yaml
try:
    with open("openenv.yaml") as f:
        manifest = yaml.safe_load(f)
    check(True, "openenv.yaml exists and parses")
    check("name" in manifest, "openenv.yaml has 'name'", f"keys: {list(manifest.keys())}")
    check("version" in manifest, "openenv.yaml has 'version'")
    check("tasks" in manifest, "openenv.yaml has 'tasks'")
    check("endpoints" in manifest, "openenv.yaml has 'endpoints'")
    check("baseline" in manifest, "openenv.yaml has 'baseline'")
except Exception as e:
    check(False, "openenv.yaml", str(e))

# inference.py
check(os.path.exists("inference.py"), "inference.py exists at repo root")

# Dockerfile
check(os.path.exists("Dockerfile"), "Dockerfile exists")

# Typed models
try:
    r = client.post("/reset", json={"task_id": "task1_verification", "seed": 42})
    d = r.json()
    state = d.get("state", {})
    check("task_id" in state, "State has task_id")
    check("status" in state, "State has status")
    check("step_count" in state, "State has step_count")
    check("patient" in state, "State has patient")
    check("progress" in state, "State has progress")

    eid = d["episode_id"]
    pid = state["patient"]["patient_id"]

    # step()
    r = client.post("/step", json={
        "episode_id": eid,
        "action": {"action_type": "check_eligibility", "patient_id": pid, "task_id": "task1_verification",
                    "parameters": {"member_id": state["patient"]["member_id"], "insurer": state["patient"]["insurer"]}}
    })
    sd = r.json()
    check("observation" in sd, "Step returns observation")
    check("reward" in sd, "Step returns reward")
    check("done" in sd, "Step returns done")
    check("state" in sd, "Step returns state")
    check(isinstance(sd.get("reward"), (int, float)), "Reward is numeric", f"got {type(sd.get('reward'))}")

    # state()
    r = client.get(f"/state?episode_id={eid}")
    check(r.status_code == 200, "GET /state returns 200")
except Exception as e:
    check(False, "Spec compliance endpoints", str(e))

# ---------------------------------------------------------------
# 3. 3+ tasks with graders (scores 0.0–1.0)
# ---------------------------------------------------------------
print("\n--- 3. Tasks & Graders ---")
try:
    r = client.get("/tasks")
    check(r.status_code == 200, "GET /tasks returns 200")
    td = r.json()
    tasks = td.get("tasks", [])
    check(len(tasks) >= 3, f"3+ tasks defined", f"got {len(tasks)}")

    for t in tasks:
        check("task_id" in t, f"Task '{t.get('task_id', '?')}' has task_id")
        check("available_actions" in t, f"Task '{t.get('task_id', '?')}' has available_actions")
except Exception as e:
    check(False, "GET /tasks", str(e))

# Grade each task
for task_id in ["task1_verification", "task2_mri_necessity", "task3_cgm_appeal"]:
    try:
        r = client.post("/reset", json={"task_id": task_id, "seed": 42})
        d = r.json()
        eid = d["episode_id"]
        pid = d["state"]["patient"]["patient_id"]

        # Submit a decision to end the episode
        client.post("/step", json={
            "episode_id": eid,
            "action": {"action_type": "submit_decision", "patient_id": pid, "task_id": task_id,
                        "parameters": {"decision": "approve", "rationale": "Validation test — submitting for grader check."}}
        })

        r = client.post("/grader", json={"episode_id": eid})
        check(r.status_code == 200, f"POST /grader ({task_id}) returns 200", f"got {r.status_code}")
        gd = r.json()
        score = gd.get("final_score")
        check(isinstance(score, (int, float)) and 0.0 <= score <= 1.0,
              f"Grader score in 0.0–1.0 ({task_id})", f"got {score}")
        check(len(gd.get("components", [])) > 0,
              f"Grader has components ({task_id})")
    except Exception as e:
        check(False, f"Grader {task_id}", str(e))

# ---------------------------------------------------------------
# 4. Baseline reproduces
# ---------------------------------------------------------------
print("\n--- 4. Baseline ---")
try:
    r = client.post("/baseline", timeout=60)
    check(r.status_code == 200, "POST /baseline returns 200", f"got {r.status_code}")
    bd = r.json()
    check("overall_score" in bd, "Baseline has overall_score")
    check("task_results" in bd, "Baseline has task_results")
    check("model_used" in bd, "Baseline has model_used")
    trs = bd.get("task_results", [])
    check(len(trs) >= 3, f"Baseline covers 3+ tasks", f"got {len(trs)}")
    for tr in trs:
        s = tr.get("final_score")
        check(isinstance(s, (int, float)) and 0.0 <= s <= 1.0,
              f"Baseline score valid ({tr.get('task_id', '?')})", f"got {s}")
except Exception as e:
    check(False, "POST /baseline", str(e))

# ---------------------------------------------------------------
# 5. Additional endpoints
# ---------------------------------------------------------------
print("\n--- 5. Additional Endpoints ---")
try:
    r = client.get("/validate")
    check(r.status_code == 200, "GET /validate returns 200")
except Exception as e:
    check(False, "GET /validate", str(e))

try:
    r = client.get("/info")
    check(r.status_code == 200, "GET /info returns 200")
except Exception as e:
    check(False, "GET /info", str(e))

# ---------------------------------------------------------------
# Summary
# ---------------------------------------------------------------
print("\n" + "=" * 60)
print(f"RESULTS: {passed} passed, {failed} failed")
print("=" * 60)
if errors:
    print("\nFailures:")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
else:
    print("\nAll checks passed!")
    sys.exit(0)

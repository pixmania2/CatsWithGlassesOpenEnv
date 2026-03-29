print("🚀 GENERATOR STARTED")
import json
import os
import random
from datetime import datetime, timedelta

OUTPUT_DIR = "data/prs"
os.makedirs(OUTPUT_DIR, exist_ok=True)


# --------------------------------------------------
# HELPERS
# --------------------------------------------------

def random_date(start_days_ago=120):
    base = datetime.today() - timedelta(days=random.randint(0, start_days_ago))
    return base.strftime("%Y-%m-%d")


def generate_pt_sessions(weeks):
    sessions = []
    start = datetime.today() - timedelta(days=weeks * 7)

    for i in range(weeks * 2):  # ~2 sessions per week
        session_date = start + timedelta(days=i * 3)
        sessions.append({
            "session_date": session_date.strftime("%Y-%m-%d"),
            "session_number": i + 1,
            "therapist_notes": "PT session conducted",
            "pain_score": random.randint(4, 8),
            "improved": random.choice([True, False])
        })

    return sessions


def base_patient(pid, insurer):
    return {
        "patient_id": pid,

        "demographics": {
            "name": f"Patient {pid}",
            "dob": "1975-01-01",
            "gender": random.choice(["male", "female"])
        },

        "insurance": {
            "member_id": f"MBR-{random.randint(100000,999999)}",
            "insurer": insurer,
            "plan_id": f"{insurer.upper()}-PLAN",
            "active": True
        },

        "vitals": {
            "bmi": round(random.uniform(22, 32), 1)
        },

        "diagnosis_codes": [
            {"code": "M17.11", "primary": True}
        ],

        "progress_notes": [],
        "physical_exam": [],
        "lab_results": [],
        "pt_sessions": [],
        "pharmacy_history": [],
        "imaging_history": [],

        "requested_procedure": {
            "cpt_code": "73721"
        }
    }


# --------------------------------------------------
# GENERATION LOGIC
# --------------------------------------------------

def generate_patients():
    patients = []

    insurers = ["aetna", "cigna", "cms"]

    # ---------------------------
    # TASK 1 (Basic Eligibility)
    # ---------------------------
    for i in range(1, 6):
        p = base_patient(f"PAT-{i:03}", random.choice(insurers))

        if i == 2:
            p["insurance"]["active"] = False  # inactive

        if i == 3:
            p["requested_procedure"]["cpt_code"] = "99999"  # not covered

        patients.append(p)

    # ---------------------------
    # TASK 2 (PT Duration)
    # ---------------------------
    for i in range(6, 11):
        insurer = random.choice(insurers)
        p = base_patient(f"PAT-{i:03}", insurer)

        required_weeks = 3 if insurer == "aetna" else 6

        if i % 2 == 0:
            weeks = required_weeks + 1  # meets requirement
        else:
            weeks = max(1, required_weeks - 2)  # insufficient

        p["pt_sessions"] = generate_pt_sessions(weeks)

        p["progress_notes"].append({
            "date": random_date(),
            "note": f"Patient undergoing PT for {weeks} weeks"
        })

        patients.append(p)

    # ---------------------------
    # TASK 2 (Red Flag Bypass)
    # ---------------------------
    for i in range(11, 14):
        p = base_patient(f"PAT-{i:03}", random.choice(insurers))

        p["pt_sessions"] = generate_pt_sessions(2)  # insufficient

        p["physical_exam"].append({
            "date": random_date(),
            "findings": ["Joint stiffness"],
            "red_flags": ["True Locking"]
        })

        patients.append(p)

    # ---------------------------
    # TASK 3 (Diabetes / CGM)
    # ---------------------------
    for i in range(14, 21):
        p = base_patient(f"PAT-{i:03}", random.choice(insurers))

        # labs
        fasting = random.choice([180, 210, 230])
        low = random.choice([None, 50, 45])

        p["lab_results"] = [
            {"test_name": "fasting_glucose", "value": fasting, "unit": "mg/dL"},
            {"test_name": "HbA1c", "value": round(random.uniform(7.5, 9.5), 1), "unit": "%"}
        ]

        if low:
            p["lab_results"].append({
                "test_name": "glucose",
                "value": low,
                "unit": "mg/dL"
            })

        # meds
        p["pharmacy_history"] = [
            {
                "medication": "Insulin",
                "frequency": f"{random.randint(1,4)} times daily"
            }
        ]

        p["diagnosis_codes"] = [
            {"code": "E11.9", "primary": True}
        ]

        p["requested_procedure"] = {
            "cpt_code": "95250"  # CGM
        }

        patients.append(p)

    return patients


# --------------------------------------------------
# SAVE
# --------------------------------------------------

def save_patients(patients):
    # 🔥 clear old files
    for file in os.listdir(OUTPUT_DIR):
        if file.endswith(".json"):
            os.remove(os.path.join(OUTPUT_DIR, file))

    for p in patients:
        path = os.path.join(OUTPUT_DIR, f"{p['patient_id']}.json")
        with open(path, "w") as f:
            json.dump(p, f, indent=2)

    print(f"✅ Generated {len(patients)} patients")


if __name__ == "__main__":
    patients = generate_patients()
    save_patients(patients)
"""
engine.py — Core Environment Engine for the PTPA OpenEnv Environment

Implements reset(), step(), get_state(), and grade() with embedded
synthetic patient data and insurance policy data so the full server
pipeline works end-to-end.
"""

from __future__ import annotations

import copy
import random
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from models import (
    ActionType,
    AuthorizationDecision,
    Difficulty,
    EpisodeProgress,
    EpisodeStatus,
    EvidenceItem,
    GraderComponentScore,
    GraderResult,
    PatientRecord,
    PolicyRule,
    PRSSection,
    PTSession,
    PTPAAction,
    PTPAObservation,
    PTPAState,
    RedFlagItem,
    TaskID,
)
from tasks import (
    ALL_TASKS,
    APPEAL_LETTER_JUDGE_RUBRIC,
    CGM_EXCEPTION_THRESHOLDS,
    MAX_STEPS,
    TASK1_ANSWER_KEYS,
    TASK2_ANSWER_KEYS,
    TASK3_ANSWER_KEYS,
    get_max_steps,
    get_task,
)
from environment.rewards import compute_step_reward, no_reward


# =========================================================================
# EMBEDDED PATIENT RECORD SYSTEM (PRS)
# =========================================================================

_PATIENTS: Dict[str, Dict[str, Any]] = {
    # ----- TASK 1 patients (PAT-001 to PAT-005) -----
    "PAT-001": {
        "patient_id": "PAT-001",
        "demographics": {"name": "John Carter", "dob": "1965-04-12", "gender": "M"},
        "insurance": {
            "member_id": "MBR-881234",
            "insurer": "aetna",
            "plan_id": "AETNA-GOLD-PPO",
            "active_status": True,
            "effective_date": "2024-01-01",
            "termination_date": None,
        },
        "vitals": {"height_cm": 178, "weight_kg": 88, "bmi": 27.8, "bp": "138/85"},
        "diagnosis_codes": [{"code": "M17.11", "description": "Primary osteoarthritis, right knee"}],
        "progress_notes": [
            {"date": "2024-06-01", "note": "Patient reports persistent right knee pain, 6/10 severity, worsening over 3 months. Stiffness in morning lasting ~30 min.", "provider": "Dr. Sarah Mitchell"},
        ],
        "physical_exam": [
            {"date": "2024-06-01", "findings": "Crepitus on flexion. ROM limited to 110 degrees. Mild effusion. No locking or instability. Neurovascular intact."},
        ],
        "lab_results": [],
        "pt_sessions": [],
        "pharmacy_history": [
            {"medication": "Ibuprofen 600mg", "start_date": "2024-04-01", "duration_days": 60, "adherence": "good"},
        ],
        "imaging_history": [
            {"type": "X-ray", "date": "2024-05-15", "findings": "Mild joint space narrowing, no fracture."},
        ],
        "requested_procedure": {"cpt_code": "73721", "description": "MRI right knee without contrast"},
        "attending_physician": "Dr. Sarah Mitchell",
    },
    "PAT-002": {
        "patient_id": "PAT-002",
        "demographics": {"name": "Maria Gonzalez", "dob": "1978-09-22", "gender": "F"},
        "insurance": {
            "member_id": "MBR-556789",
            "insurer": "cigna",
            "plan_id": "CIGNA-HMO-STANDARD",
            "active_status": False,
            "effective_date": "2023-01-01",
            "termination_date": "2024-03-31",
        },
        "vitals": {"height_cm": 163, "weight_kg": 65, "bmi": 24.5, "bp": "122/78"},
        "diagnosis_codes": [{"code": "M54.5", "description": "Low back pain"}],
        "progress_notes": [
            {"date": "2024-07-10", "note": "Chronic low back pain, unresponsive to conservative therapy. Requesting lumbar MRI.", "provider": "Dr. James Lee"},
        ],
        "physical_exam": [
            {"date": "2024-07-10", "findings": "Paravertebral tenderness L4-L5. SLR negative bilaterally. No motor deficits."},
        ],
        "lab_results": [],
        "pt_sessions": [],
        "pharmacy_history": [
            {"medication": "Naproxen 500mg", "start_date": "2024-03-01", "duration_days": 90, "adherence": "fair"},
        ],
        "imaging_history": [],
        "requested_procedure": {"cpt_code": "72148", "description": "MRI lumbar spine without contrast"},
        "attending_physician": "Dr. James Lee",
    },
    "PAT-003": {
        "patient_id": "PAT-003",
        "demographics": {"name": "Robert Kim", "dob": "1982-01-15", "gender": "M"},
        "insurance": {
            "member_id": "MBR-334455",
            "insurer": "united",
            "plan_id": "UHC-CHOICE-PLUS",
            "active_status": True,
            "effective_date": "2024-01-01",
            "termination_date": None,
        },
        "vitals": {"height_cm": 175, "weight_kg": 82, "bmi": 26.8, "bp": "130/82"},
        "diagnosis_codes": [{"code": "M75.10", "description": "Rotator cuff syndrome, unspecified shoulder"}],
        "progress_notes": [
            {"date": "2024-08-01", "note": "Right shoulder pain with overhead activities. Failed 4 weeks of PT. Requesting shoulder MRI.", "provider": "Dr. Emily Tanaka"},
        ],
        "physical_exam": [
            {"date": "2024-08-01", "findings": "Positive Neer and Hawkins impingement tests. ROM decreased in abduction. No instability."},
        ],
        "lab_results": [],
        "pt_sessions": [
            {"session_date": "2024-06-15", "session_number": 1, "therapist_notes": "Initial eval. ROM exercises started.", "pain_score": 7},
            {"session_date": "2024-07-01", "session_number": 4, "therapist_notes": "Moderate improvement in ROM. Continued strengthening.", "pain_score": 6},
        ],
        "pharmacy_history": [
            {"medication": "Meloxicam 15mg", "start_date": "2024-05-01", "duration_days": 60, "adherence": "good"},
        ],
        "imaging_history": [],
        "requested_procedure": {"cpt_code": "73221", "description": "MRI right shoulder without contrast"},
        "attending_physician": "Dr. Emily Tanaka",
    },
    "PAT-004": {
        "patient_id": "PAT-004",
        "demographics": {"name": "Dorothy Williams", "dob": "1955-11-03", "gender": "F"},
        "insurance": {
            "member_id": "MBR-112233",
            "insurer": "cms",
            "plan_id": "MEDICARE-PART-B",
            "active_status": True,
            "effective_date": "2020-11-01",
            "termination_date": None,
        },
        "vitals": {"height_cm": 160, "weight_kg": 72, "bmi": 28.1, "bp": "142/88"},
        "diagnosis_codes": [{"code": "M17.11", "description": "Primary osteoarthritis, right knee"}],
        "progress_notes": [
            {"date": "2024-05-20", "note": "Progressive right knee pain, difficulty with stairs. Conservative measures exhausted. MRI requested.", "provider": "Dr. Alan Brooks"},
        ],
        "physical_exam": [
            {"date": "2024-05-20", "findings": "Bilateral knee crepitus, right > left. Varus deformity. ROM 5-100 degrees right knee."},
        ],
        "lab_results": [],
        "pt_sessions": [],
        "pharmacy_history": [
            {"medication": "Acetaminophen 1000mg", "start_date": "2024-01-01", "duration_days": 140, "adherence": "good"},
        ],
        "imaging_history": [
            {"type": "X-ray", "date": "2024-04-10", "findings": "Moderate medial compartment narrowing. Osteophytes present."},
        ],
        "requested_procedure": {"cpt_code": "73721", "description": "MRI right knee without contrast"},
        "attending_physician": "Dr. Alan Brooks",
    },
    "PAT-005": {
        "patient_id": "PAT-005",
        "demographics": {"name": "Thomas Patel", "dob": "1990-06-30", "gender": "M"},
        "insurance": {
            "member_id": "MBR-998877",
            "insurer": "aetna",
            "plan_id": "AETNA-BASIC-EPO",
            "active_status": True,
            "effective_date": "2024-01-01",
            "termination_date": None,
        },
        "vitals": {"height_cm": 180, "weight_kg": 78, "bmi": 24.1, "bp": "118/74"},
        "diagnosis_codes": [{"code": "G43.909", "description": "Migraine, unspecified, not intractable"}],
        "progress_notes": [
            {"date": "2024-09-01", "note": "Frequent migraines, 3-4 per month. Requesting brain MRI to rule out structural cause.", "provider": "Dr. Nora Reyes"},
        ],
        "physical_exam": [
            {"date": "2024-09-01", "findings": "Cranial nerves II-XII intact. No focal neurological deficits. No papilledema."},
        ],
        "lab_results": [],
        "pt_sessions": [],
        "pharmacy_history": [
            {"medication": "Sumatriptan 50mg", "start_date": "2024-03-01", "duration_days": 180, "adherence": "good"},
        ],
        "imaging_history": [],
        "requested_procedure": {"cpt_code": "70553", "description": "MRI brain with and without contrast"},
        "attending_physician": "Dr. Nora Reyes",
    },

    # ----- TASK 2 patients (PAT-006 to PAT-010) -----
    "PAT-006": {
        "patient_id": "PAT-006",
        "demographics": {"name": "Linda Morrison", "dob": "1970-03-18", "gender": "F"},
        "insurance": {
            "member_id": "MBR-667788",
            "insurer": "aetna",
            "plan_id": "AETNA-GOLD-PPO",
            "active_status": True,
            "effective_date": "2024-01-01",
            "termination_date": None,
        },
        "vitals": {"height_cm": 165, "weight_kg": 75, "bmi": 27.5, "bp": "135/82"},
        "diagnosis_codes": [{"code": "M17.11", "description": "Primary osteoarthritis, right knee"}],
        "progress_notes": [
            {"date": "2024-03-01", "note": "Right knee pain worsening despite PT. No locking or instability.", "provider": "Dr. Sarah Mitchell"},
            {"date": "2024-04-15", "note": "Completed 4 weeks of PT. Pain persists at 6/10. Requesting MRI.", "provider": "Dr. Sarah Mitchell"},
        ],
        "physical_exam": [
            {"date": "2024-04-15", "findings": "Crepitus present. No effusion. ROM 10-120. No locking. Neurovascular intact. Stable valgus/varus."},
        ],
        "lab_results": [],
        "pt_sessions": [
            {"session_date": "2024-03-04", "session_number": 1, "therapist_notes": "Initial eval. Quad strengthening, ROM exercises.", "functional_outcome": "Baseline", "pain_score": 7, "improved": False},
            {"session_date": "2024-03-08", "session_number": 2, "therapist_notes": "Continued ROM. Added stationary bike.", "functional_outcome": "Minimal improvement", "pain_score": 7, "improved": False},
            {"session_date": "2024-03-13", "session_number": 3, "therapist_notes": "Progressed to closed-chain exercises.", "functional_outcome": "Slight improvement", "pain_score": 6, "improved": True},
            {"session_date": "2024-03-18", "session_number": 4, "therapist_notes": "Pain with stair climbing persists.", "functional_outcome": "Plateau", "pain_score": 6, "improved": False},
            {"session_date": "2024-03-22", "session_number": 5, "therapist_notes": "Added balance training. Knee still catching.", "functional_outcome": "No change", "pain_score": 6, "improved": False},
            {"session_date": "2024-03-27", "session_number": 6, "therapist_notes": "Functional decline noted.", "functional_outcome": "Declined", "pain_score": 7, "improved": False},
            {"session_date": "2024-04-01", "session_number": 7, "therapist_notes": "Patient frustrated. Recommends imaging.", "functional_outcome": "No progress", "pain_score": 7, "improved": False},
            {"session_date": "2024-04-05", "session_number": 8, "therapist_notes": "Discharged from PT. Recommend MRI.", "functional_outcome": "Failed conservative therapy", "pain_score": 7, "improved": False},
        ],
        "pharmacy_history": [
            {"medication": "Ibuprofen 600mg", "start_date": "2024-02-15", "duration_days": 60, "adherence": "good"},
        ],
        "imaging_history": [
            {"type": "X-ray", "date": "2024-02-20", "findings": "Mild-moderate medial joint space narrowing."},
        ],
        "requested_procedure": {"cpt_code": "73721", "description": "MRI right knee without contrast"},
        "attending_physician": "Dr. Sarah Mitchell",
    },
    "PAT-007": {
        "patient_id": "PAT-007",
        "demographics": {"name": "James O'Brien", "dob": "1985-07-25", "gender": "M"},
        "insurance": {
            "member_id": "MBR-445566",
            "insurer": "cigna",
            "plan_id": "CIGNA-OPEN-ACCESS",
            "active_status": True,
            "effective_date": "2024-01-01",
            "termination_date": None,
        },
        "vitals": {"height_cm": 183, "weight_kg": 90, "bmi": 26.9, "bp": "128/80"},
        "diagnosis_codes": [{"code": "M23.211", "description": "Derangement of anterior horn of medial meniscus, right knee"}],
        "progress_notes": [
            {"date": "2024-05-10", "note": "Acute right knee injury during basketball. Knee locked in flexion for 20 minutes. Severe pain.", "provider": "Dr. Kevin Park"},
            {"date": "2024-05-20", "note": "True Locking episode witnessed in clinic. Knee locked at 45 degrees for 5 minutes. Suspected torn meniscus with mechanical block.", "provider": "Dr. Kevin Park"},
        ],
        "physical_exam": [
            {"date": "2024-05-20", "findings": "TRUE LOCKING observed — knee locked at 45 degrees flexion, unable to extend for 5 minutes. Positive McMurray test. Joint line tenderness medial. Effusion 2+. HIGH CLINICAL URGENCY."},
        ],
        "lab_results": [],
        "pt_sessions": [
            {"session_date": "2024-05-13", "session_number": 1, "therapist_notes": "Initial eval post-injury. Very limited ROM.", "functional_outcome": "Unable to complete exercises", "pain_score": 8, "improved": False},
            {"session_date": "2024-05-15", "session_number": 2, "therapist_notes": "Locking episode during session. Session terminated.", "functional_outcome": "Worsened", "pain_score": 9, "improved": False},
            {"session_date": "2024-05-17", "session_number": 3, "therapist_notes": "Patient unable to bear weight. Recommends urgent imaging.", "functional_outcome": "Cannot participate", "pain_score": 9, "improved": False},
            {"session_date": "2024-05-22", "session_number": 4, "therapist_notes": "Discharged — requires MRI before further PT.", "functional_outcome": "Failed", "pain_score": 8, "improved": False},
        ],
        "pharmacy_history": [
            {"medication": "Naproxen 500mg", "start_date": "2024-05-10", "duration_days": 14, "adherence": "good"},
        ],
        "imaging_history": [
            {"type": "X-ray", "date": "2024-05-10", "findings": "No fracture. Possible effusion."},
        ],
        "requested_procedure": {"cpt_code": "73721", "description": "MRI right knee without contrast"},
        "attending_physician": "Dr. Kevin Park",
    },
    "PAT-008": {
        "patient_id": "PAT-008",
        "demographics": {"name": "Susan Chen", "dob": "1975-12-08", "gender": "F"},
        "insurance": {
            "member_id": "MBR-778899",
            "insurer": "cigna",
            "plan_id": "CIGNA-HMO-STANDARD",
            "active_status": True,
            "effective_date": "2024-01-01",
            "termination_date": None,
        },
        "vitals": {"height_cm": 158, "weight_kg": 60, "bmi": 24.0, "bp": "120/76"},
        "diagnosis_codes": [{"code": "M17.11", "description": "Primary osteoarthritis, right knee"}],
        "progress_notes": [
            {"date": "2024-06-20", "note": "Mild right knee pain. Started PT 2 weeks ago. Requesting early MRI.", "provider": "Dr. Lisa Wang"},
        ],
        "physical_exam": [
            {"date": "2024-06-20", "findings": "Mild crepitus. Full ROM. No effusion. No locking. No instability. Neurovascular intact."},
        ],
        "lab_results": [],
        "pt_sessions": [
            {"session_date": "2024-06-10", "session_number": 1, "therapist_notes": "Initial eval. Mild symptoms. Started exercises.", "functional_outcome": "Baseline", "pain_score": 4, "improved": False},
            {"session_date": "2024-06-14", "session_number": 2, "therapist_notes": "Good progress. Pain decreasing.", "functional_outcome": "Improving", "pain_score": 3, "improved": True},
            {"session_date": "2024-06-19", "session_number": 3, "therapist_notes": "Continued improvement.", "functional_outcome": "Improving", "pain_score": 3, "improved": True},
        ],
        "pharmacy_history": [
            {"medication": "Ibuprofen 400mg", "start_date": "2024-06-01", "duration_days": 30, "adherence": "good"},
        ],
        "imaging_history": [],
        "requested_procedure": {"cpt_code": "73721", "description": "MRI right knee without contrast"},
        "attending_physician": "Dr. Lisa Wang",
    },
    "PAT-009": {
        "patient_id": "PAT-009",
        "demographics": {"name": "Richard Thompson", "dob": "1960-02-14", "gender": "M"},
        "insurance": {
            "member_id": "MBR-223344",
            "insurer": "cms",
            "plan_id": "MEDICARE-PART-B",
            "active_status": True,
            "effective_date": "2020-02-01",
            "termination_date": None,
        },
        "vitals": {"height_cm": 175, "weight_kg": 95, "bmi": 31.0, "bp": "145/90"},
        "diagnosis_codes": [{"code": "M54.5", "description": "Low back pain"}, {"code": "M51.16", "description": "Lumbar disc degeneration"}],
        "progress_notes": [
            {"date": "2024-04-01", "note": "Chronic LBP with radiculopathy. 7.5 weeks of PT completed. No improvement. Requesting lumbar MRI.", "provider": "Dr. Alan Brooks"},
        ],
        "physical_exam": [
            {"date": "2024-04-01", "findings": "Positive SLR right at 40 degrees. Decreased ankle reflex right. Paraspinal muscle spasm L4-S1. No red flags."},
        ],
        "lab_results": [],
        "pt_sessions": [
            {"session_date": f"2024-02-{5+i*3:02d}", "session_number": i+1, "therapist_notes": f"Session {i+1}. {'Improving' if i < 5 else 'Plateau — no further gains'}.", "functional_outcome": "Improving" if i < 5 else "Plateau", "pain_score": max(4, 7 - i * 0.3), "improved": i < 5}
            for i in range(15)
        ],
        "pharmacy_history": [
            {"medication": "Meloxicam 15mg", "start_date": "2024-01-15", "duration_days": 90, "adherence": "good"},
            {"medication": "Gabapentin 300mg", "start_date": "2024-02-01", "duration_days": 60, "adherence": "good"},
        ],
        "imaging_history": [
            {"type": "X-ray", "date": "2024-01-20", "findings": "Disc space narrowing L4-L5, L5-S1. Mild spondylosis."},
        ],
        "requested_procedure": {"cpt_code": "72148", "description": "MRI lumbar spine without contrast"},
        "attending_physician": "Dr. Alan Brooks",
    },
    "PAT-010": {
        "patient_id": "PAT-010",
        "demographics": {"name": "Angela Davis", "dob": "1988-10-05", "gender": "F"},
        "insurance": {
            "member_id": "MBR-556677",
            "insurer": "aetna",
            "plan_id": "AETNA-GOLD-PPO",
            "active_status": True,
            "effective_date": "2024-01-01",
            "termination_date": None,
        },
        "vitals": {"height_cm": 170, "weight_kg": 68, "bmi": 23.5, "bp": "118/72"},
        "diagnosis_codes": [{"code": "M17.11", "description": "Primary osteoarthritis, right knee"}],
        "progress_notes": [
            {"date": "2024-07-15", "note": "New onset knee pain 2 weeks ago. Only completed 1.5 weeks of PT. Wants MRI.", "provider": "Dr. Sarah Mitchell"},
        ],
        "physical_exam": [
            {"date": "2024-07-15", "findings": "Mild tenderness. Full ROM. No effusion. No locking. No red flags."},
        ],
        "lab_results": [],
        "pt_sessions": [
            {"session_date": "2024-07-05", "session_number": 1, "therapist_notes": "Initial eval. Mild symptoms.", "functional_outcome": "Baseline", "pain_score": 4, "improved": False},
            {"session_date": "2024-07-12", "session_number": 2, "therapist_notes": "Some improvement. Continue exercises.", "functional_outcome": "Improving", "pain_score": 3, "improved": True},
        ],
        "pharmacy_history": [
            {"medication": "Ibuprofen 400mg", "start_date": "2024-07-01", "duration_days": 14, "adherence": "good"},
        ],
        "imaging_history": [],
        "requested_procedure": {"cpt_code": "73721", "description": "MRI right knee without contrast"},
        "attending_physician": "Dr. Sarah Mitchell",
    },

    # ----- TASK 3 patients (PAT-011 to PAT-015) -----
    "PAT-011": {
        "patient_id": "PAT-011",
        "demographics": {"name": "Harold Jenkins", "dob": "1958-08-20", "gender": "M"},
        "insurance": {
            "member_id": "MBR-101112",
            "insurer": "cms",
            "plan_id": "MEDICARE-PART-B",
            "active_status": True,
            "effective_date": "2019-08-01",
            "termination_date": None,
        },
        "vitals": {"height_cm": 172, "weight_kg": 88, "bmi": 29.8, "bp": "140/88"},
        "diagnosis_codes": [{"code": "E11.65", "description": "Type 2 diabetes with hyperglycemia"}, {"code": "E11.649", "description": "Type 2 DM with hypoglycemia without coma"}],
        "progress_notes": [
            {"date": "2024-06-01", "note": "Patient has Dawn Phenomenon — fasting glucose consistently > 200 mg/dL despite optimized insulin regimen. CGM would allow real-time monitoring.", "provider": "Dr. Patricia Hernandez"},
        ],
        "physical_exam": [
            {"date": "2024-06-01", "findings": "Peripheral neuropathy bilateral feet. Monofilament sensation decreased. No active ulcers."},
        ],
        "lab_results": [
            {"test": "HbA1c", "value": 8.4, "unit": "%", "date": "2024-05-15", "reference_range": "< 7.0%"},
            {"test": "HbA1c", "value": 8.1, "unit": "%", "date": "2024-02-10", "reference_range": "< 7.0%"},
            {"test": "fasting_glucose", "value": 215, "unit": "mg/dL", "date": "2024-05-28", "reference_range": "70-100 mg/dL"},
            {"test": "fasting_glucose", "value": 228, "unit": "mg/dL", "date": "2024-05-29", "reference_range": "70-100 mg/dL"},
            {"test": "fasting_glucose", "value": 210, "unit": "mg/dL", "date": "2024-05-30", "reference_range": "70-100 mg/dL"},
            {"test": "eGFR", "value": 62, "unit": "mL/min/1.73m2", "date": "2024-05-15", "reference_range": "> 60"},
        ],
        "pt_sessions": [],
        "pharmacy_history": [
            {"medication": "Insulin Glargine 30 units", "start_date": "2024-01-01", "duration_days": 180, "adherence": "good", "route": "subcutaneous", "frequency": "once daily"},
            {"medication": "Insulin Lispro 8 units", "start_date": "2024-01-01", "duration_days": 180, "adherence": "good", "route": "subcutaneous", "frequency": "3x daily with meals"},
            {"medication": "Metformin 1000mg", "start_date": "2023-01-01", "duration_days": 540, "adherence": "good", "route": "oral", "frequency": "twice daily"},
        ],
        "imaging_history": [],
        "requested_procedure": {"cpt_code": "E2101", "description": "Continuous Glucose Monitor (CGM) receiver"},
        "attending_physician": "Dr. Patricia Hernandez",
    },
    "PAT-012": {
        "patient_id": "PAT-012",
        "demographics": {"name": "Betty Nakamura", "dob": "1972-04-16", "gender": "F"},
        "insurance": {
            "member_id": "MBR-131415",
            "insurer": "aetna",
            "plan_id": "AETNA-GOLD-PPO",
            "active_status": True,
            "effective_date": "2024-01-01",
            "termination_date": None,
        },
        "vitals": {"height_cm": 157, "weight_kg": 62, "bmi": 25.1, "bp": "125/78"},
        "diagnosis_codes": [{"code": "E10.641", "description": "Type 1 DM with hypoglycemia with coma"}],
        "progress_notes": [
            {"date": "2024-07-01", "note": "Recurrent hypoglycemic episodes. Patient unaware of lows — found unresponsive by family member twice in past 3 months. Glucose < 54 mg/dL documented.", "provider": "Dr. Michael Chang"},
        ],
        "physical_exam": [
            {"date": "2024-07-01", "findings": "Alert and oriented. No focal deficits. Hypoglycemic unawareness confirmed by history."},
        ],
        "lab_results": [
            {"test": "HbA1c", "value": 7.2, "unit": "%", "date": "2024-06-15", "reference_range": "< 7.0%"},
            {"test": "glucose_reading", "value": 48, "unit": "mg/dL", "date": "2024-06-20", "reference_range": "70-180 mg/dL", "note": "Level 2 hypoglycemic event — patient unaware"},
            {"test": "glucose_reading", "value": 42, "unit": "mg/dL", "date": "2024-05-08", "reference_range": "70-180 mg/dL", "note": "Found unresponsive, glucose 42"},
            {"test": "glucose_reading", "value": 51, "unit": "mg/dL", "date": "2024-04-22", "reference_range": "70-180 mg/dL", "note": "Hypoglycemic episode during sleep"},
            {"test": "fasting_glucose", "value": 95, "unit": "mg/dL", "date": "2024-06-20", "reference_range": "70-100 mg/dL"},
            {"test": "eGFR", "value": 88, "unit": "mL/min/1.73m2", "date": "2024-06-15", "reference_range": "> 60"},
        ],
        "pt_sessions": [],
        "pharmacy_history": [
            {"medication": "Insulin Glargine 22 units", "start_date": "2023-06-01", "duration_days": 400, "adherence": "good", "route": "subcutaneous", "frequency": "once daily"},
            {"medication": "Insulin Aspart 6 units", "start_date": "2023-06-01", "duration_days": 400, "adherence": "good", "route": "subcutaneous", "frequency": "3x daily with meals"},
        ],
        "imaging_history": [],
        "requested_procedure": {"cpt_code": "K0553", "description": "CGM receiver"},
        "attending_physician": "Dr. Michael Chang",
    },
    "PAT-013": {
        "patient_id": "PAT-013",
        "demographics": {"name": "Frank Okafor", "dob": "1968-11-30", "gender": "M"},
        "insurance": {
            "member_id": "MBR-161718",
            "insurer": "cigna",
            "plan_id": "CIGNA-OPEN-ACCESS",
            "active_status": True,
            "effective_date": "2024-01-01",
            "termination_date": None,
        },
        "vitals": {"height_cm": 180, "weight_kg": 98, "bmi": 30.2, "bp": "148/92"},
        "diagnosis_codes": [{"code": "E11.65", "description": "Type 2 diabetes with hyperglycemia"}],
        "progress_notes": [
            {"date": "2024-08-01", "note": "HbA1c 8.9% despite 3+ months of adherent insulin therapy. Glycemic variability uncontrolled. CGM requested for titration.", "provider": "Dr. Rachel Green"},
        ],
        "physical_exam": [
            {"date": "2024-08-01", "findings": "Obese male. Acanthosis nigricans. Peripheral pulses intact. Monofilament intact."},
        ],
        "lab_results": [
            {"test": "HbA1c", "value": 8.9, "unit": "%", "date": "2024-07-20", "reference_range": "< 7.0%"},
            {"test": "HbA1c", "value": 8.6, "unit": "%", "date": "2024-04-15", "reference_range": "< 7.0%"},
            {"test": "HbA1c", "value": 8.8, "unit": "%", "date": "2024-01-10", "reference_range": "< 7.0%"},
            {"test": "fasting_glucose", "value": 178, "unit": "mg/dL", "date": "2024-07-20", "reference_range": "70-100 mg/dL"},
            {"test": "eGFR", "value": 72, "unit": "mL/min/1.73m2", "date": "2024-07-20", "reference_range": "> 60"},
        ],
        "pt_sessions": [],
        "pharmacy_history": [
            {"medication": "Insulin Glargine 40 units", "start_date": "2024-01-01", "duration_days": 210, "adherence": "good", "route": "subcutaneous", "frequency": "once daily"},
            {"medication": "Insulin Lispro 10 units", "start_date": "2024-01-01", "duration_days": 210, "adherence": "good", "route": "subcutaneous", "frequency": "3x daily with meals"},
            {"medication": "Metformin 1000mg", "start_date": "2023-01-01", "duration_days": 580, "adherence": "good", "route": "oral", "frequency": "twice daily"},
        ],
        "imaging_history": [],
        "requested_procedure": {"cpt_code": "E2101", "description": "CGM receiver"},
        "attending_physician": "Dr. Rachel Green",
    },
    "PAT-014": {
        "patient_id": "PAT-014",
        "demographics": {"name": "Carol Sanders", "dob": "1980-05-22", "gender": "F"},
        "insurance": {
            "member_id": "MBR-192021",
            "insurer": "cms",
            "plan_id": "MEDICARE-PART-B",
            "active_status": True,
            "effective_date": "2021-05-01",
            "termination_date": None,
        },
        "vitals": {"height_cm": 162, "weight_kg": 85, "bmi": 32.4, "bp": "138/86"},
        "diagnosis_codes": [{"code": "E11.65", "description": "Type 2 diabetes with hyperglycemia"}],
        "progress_notes": [
            {"date": "2024-08-15", "note": "Patient requests CGM. Currently on oral medications only. No insulin therapy.", "provider": "Dr. Patricia Hernandez"},
        ],
        "physical_exam": [
            {"date": "2024-08-15", "findings": "Obese female. No peripheral neuropathy. Good foot care."},
        ],
        "lab_results": [
            {"test": "HbA1c", "value": 7.8, "unit": "%", "date": "2024-08-01", "reference_range": "< 7.0%"},
            {"test": "fasting_glucose", "value": 155, "unit": "mg/dL", "date": "2024-08-01", "reference_range": "70-100 mg/dL"},
            {"test": "eGFR", "value": 80, "unit": "mL/min/1.73m2", "date": "2024-08-01", "reference_range": "> 60"},
        ],
        "pt_sessions": [],
        "pharmacy_history": [
            {"medication": "Metformin 1000mg", "start_date": "2023-01-01", "duration_days": 600, "adherence": "good", "route": "oral", "frequency": "twice daily"},
            {"medication": "Glipizide 10mg", "start_date": "2023-06-01", "duration_days": 420, "adherence": "fair", "route": "oral", "frequency": "once daily"},
        ],
        "imaging_history": [],
        "requested_procedure": {"cpt_code": "E2101", "description": "CGM receiver"},
        "attending_physician": "Dr. Patricia Hernandez",
    },
    "PAT-015": {
        "patient_id": "PAT-015",
        "demographics": {"name": "George Alvarez", "dob": "1962-01-10", "gender": "M"},
        "insurance": {
            "member_id": "MBR-222324",
            "insurer": "cms",
            "plan_id": "MEDICARE-PART-B",
            "active_status": True,
            "effective_date": "2020-01-01",
            "termination_date": None,
        },
        "vitals": {"height_cm": 170, "weight_kg": 92, "bmi": 31.8, "bp": "144/90"},
        "diagnosis_codes": [{"code": "E11.65", "description": "Type 2 diabetes with hyperglycemia"}, {"code": "E11.649", "description": "Type 2 DM with hypoglycemia without coma"}],
        "progress_notes": [
            {"date": "2024-09-01", "note": "Fasting glucose consistently > 200 mg/dL on consecutive mornings. Dawn Phenomenon suspected. CGM needed for overnight monitoring and insulin titration.", "provider": "Dr. Patricia Hernandez"},
        ],
        "physical_exam": [
            {"date": "2024-09-01", "findings": "Peripheral neuropathy bilateral. Mild retinopathy noted on last ophthalmology exam."},
        ],
        "lab_results": [
            {"test": "HbA1c", "value": 8.4, "unit": "%", "date": "2024-08-15", "reference_range": "< 7.0%"},
            {"test": "HbA1c", "value": 8.2, "unit": "%", "date": "2024-05-10", "reference_range": "< 7.0%"},
            {"test": "fasting_glucose", "value": 215, "unit": "mg/dL", "date": "2024-08-28", "reference_range": "70-100 mg/dL"},
            {"test": "fasting_glucose", "value": 222, "unit": "mg/dL", "date": "2024-08-29", "reference_range": "70-100 mg/dL"},
            {"test": "fasting_glucose", "value": 208, "unit": "mg/dL", "date": "2024-08-30", "reference_range": "70-100 mg/dL"},
            {"test": "eGFR", "value": 58, "unit": "mL/min/1.73m2", "date": "2024-08-15", "reference_range": "> 60"},
        ],
        "pt_sessions": [],
        "pharmacy_history": [
            {"medication": "Insulin Glargine 35 units", "start_date": "2024-01-01", "duration_days": 240, "adherence": "good", "route": "subcutaneous", "frequency": "once daily"},
            {"medication": "Insulin Lispro 10 units", "start_date": "2024-01-01", "duration_days": 240, "adherence": "good", "route": "subcutaneous", "frequency": "3x daily with meals"},
            {"medication": "Metformin 1000mg", "start_date": "2022-06-01", "duration_days": 820, "adherence": "good", "route": "oral", "frequency": "twice daily"},
        ],
        "imaging_history": [],
        "requested_procedure": {"cpt_code": "K0553", "description": "CGM receiver"},
        "attending_physician": "Dr. Patricia Hernandez",
    },
}

# =========================================================================
# EMBEDDED INSURANCE POLICY DATABASE (IPD)
# =========================================================================

_POLICIES: Dict[str, Dict[str, Any]] = {
    "aetna": {
        "eligibility": {"plan_ids": ["AETNA-GOLD-PPO", "AETNA-BASIC-EPO"], "active_check": True},
        "covered_services": {
            "73721": {"covered": True, "icd10": ["M17.11", "M23.211", "M23.311"], "section": "Section 4.2 Covered Services"},
            "72148": {"covered": True, "icd10": ["M54.5", "M51.16"], "section": "Section 4.2 Covered Services"},
            "73221": {"covered": True, "icd10": ["M75.10", "M75.11"], "section": "Section 4.2 Covered Services"},
            "70553": {"covered": False, "icd10": [], "section": "Section 5.1 Prior Authorization Required", "note": "Brain MRI for migraine requires additional clinical criteria not met"},
        },
        "prior_auth_criteria": {
            "73721": {"conservative_therapy_weeks": 3, "requires_xray": True, "description": "Aetna CPB 0171 — MRI Extremities Criteria: 3 weeks conservative therapy required"},
            "72148": {"conservative_therapy_weeks": 3, "requires_xray": True, "description": "Aetna CPB — Lumbar MRI: 3 weeks conservative therapy required"},
        },
        "step_therapy_rules": {
            "CGM": {"min_daily_insulin_injections": 2, "description": "Patient must be on multi-dose insulin regimen (≥2 daily injections)"},
        },
        "exception_criteria": {
            "CGM": {
                "hypoglycemic_unawareness": {"threshold": "< 54 mg/dL", "description": "Aetna CPB 0515 — CGM Exception: Level 2 Hypoglycemic Events", "requires": "Documented glucose < 54 mg/dL with unawareness"},
            },
        },
        "appeal_process": {"filing_deadline_days": 180, "levels": ["Internal Appeal", "External Review"]},
    },
    "cigna": {
        "eligibility": {"plan_ids": ["CIGNA-HMO-STANDARD", "CIGNA-OPEN-ACCESS"], "active_check": True},
        "covered_services": {
            "73721": {"covered": True, "icd10": ["M17.11", "M23.211"], "section": "Section 4.2 Covered Services"},
            "72148": {"covered": True, "icd10": ["M54.5", "M51.16"], "section": "Section 4.2 Covered Services"},
        },
        "prior_auth_criteria": {
            "73721": {"conservative_therapy_weeks": 6, "requires_xray": True, "description": "Cigna Clinical Policy Bulletin MRI Extremities: 6 weeks conservative therapy required", "red_flag_bypass": ["True Locking", "Suspected tumor", "Suspected infection", "Progressive neurological deficit", "Fracture on X-ray"]},
            "72148": {"conservative_therapy_weeks": 6, "requires_xray": True, "description": "Cigna CPB Lumbar MRI: 6 weeks conservative therapy required"},
        },
        "step_therapy_rules": {
            "CGM": {"min_daily_insulin_injections": 2, "description": "Multi-dose insulin required before CGM approval"},
        },
        "exception_criteria": {
            "CGM": {
                "glycemic_variability": {"threshold": "> 7.0% HbA1c despite 3 months adherence", "description": "Cigna CPG CGM Coverage Exception — Inadequate Glycemic Control", "requires": "HbA1c > 7.0% with documented 3-month insulin adherence"},
            },
        },
        "appeal_process": {"filing_deadline_days": 90, "levels": ["Internal Appeal", "External Review"]},
    },
    "cms": {
        "eligibility": {"plan_ids": ["MEDICARE-PART-B"], "active_check": True},
        "covered_services": {
            "73721": {"covered": True, "icd10": ["M17.11"], "section": "Section 4.2 Covered Services"},
            "72148": {"covered": True, "icd10": ["M54.5", "M51.16"], "section": "Section 4.2 Covered Services"},
            "E2101": {"covered": True, "icd10": ["E11.65", "E11.649", "E10.641"], "section": "Section 4.2 Covered Services", "note": "CGM — requires medical necessity"},
            "K0553": {"covered": True, "icd10": ["E11.65", "E11.649", "E10.641"], "section": "Section 4.2 Covered Services", "note": "CGM — requires medical necessity"},
        },
        "prior_auth_criteria": {
            "73721": {"conservative_therapy_weeks": 6, "requires_xray": False, "description": "CMS LCD L33642 — Knee MRI: 6 weeks conservative therapy"},
            "72148": {"conservative_therapy_weeks": 6, "requires_xray": False, "description": "CMS LCD L33642 — Lumbar MRI Criteria: 6 weeks conservative therapy"},
        },
        "step_therapy_rules": {
            "CGM": {"min_daily_insulin_injections": 2, "description": "CMS requires multi-dose insulin (≥2 daily injections) or insulin pump therapy"},
        },
        "exception_criteria": {
            "CGM": {
                "dawn_phenomenon": {"threshold": "> 200 mg/dL fasting glucose", "description": "CMS LCD L33822 — CGM Exception: Problematic Hypoglycemia / Dawn Phenomenon", "requires": "Fasting glucose > 200 mg/dL on consecutive mornings"},
                "hypoglycemic_unawareness": {"threshold": "< 54 mg/dL", "description": "CMS LCD L33822 — CGM Exception: Level 2 Hypoglycemic Events", "requires": "Documented glucose < 54 mg/dL"},
            },
        },
        "appeal_process": {"filing_deadline_days": 120, "levels": ["Redetermination", "Reconsideration", "ALJ Hearing"]},
    },
    "united": {
        "eligibility": {"plan_ids": ["UHC-CHOICE-PLUS"], "active_check": True},
        "covered_services": {
            "73721": {"covered": True, "icd10": ["M17.11"], "section": "Section 4.2 Covered Services"},
            "73221": {"covered": False, "icd10": [], "section": "Section 4.2 Covered Services", "note": "Shoulder MRI not covered under this plan tier"},
        },
        "prior_auth_criteria": {
            "73721": {"conservative_therapy_weeks": 6, "requires_xray": True, "description": "UHC MRI Policy: 6 weeks conservative therapy required"},
        },
        "step_therapy_rules": {},
        "exception_criteria": {},
        "appeal_process": {"filing_deadline_days": 180, "levels": ["Internal Appeal", "External Review"]},
    },
}

# Task -> patient pool mapping
_TASK_PATIENTS = {
    TaskID.VERIFICATION:  ["PAT-001", "PAT-002", "PAT-003", "PAT-004", "PAT-005"],
    TaskID.MRI_NECESSITY: ["PAT-006", "PAT-007", "PAT-008", "PAT-009", "PAT-010"],
    TaskID.CGM_APPEAL:    ["PAT-011", "PAT-012", "PAT-013", "PAT-014", "PAT-015"],
}


# =========================================================================
# ENGINE
# =========================================================================

class PTPAEngine:
    """
    Core environment engine. Manages episode state internally
    and processes actions against embedded PRS/IPD data.
    """

    def __init__(self) -> None:
        # episode_id -> internal episode data
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

        # pick patient
        pool = _TASK_PATIENTS[task_id]
        if patient_id and patient_id in pool:
            pid = patient_id
        else:
            pid = rng.choice(pool)

        patient_data = copy.deepcopy(_PATIENTS[pid])
        ins = patient_data["insurance"]
        proc = patient_data["requested_procedure"]
        demo = patient_data["demographics"]

        patient_record = PatientRecord(
            patient_id=pid,
            name=demo["name"],
            dob=demo["dob"],
            member_id=ins["member_id"],
            insurer=ins["insurer"],
            plan_id=ins["plan_id"],
            primary_icd10=patient_data["diagnosis_codes"][0]["code"],
            requested_cpt=proc["cpt_code"],
            attending_physician=patient_data.get("attending_physician", "Unknown"),
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
            progress=EpisodeProgress(repeated_queries=0),
            seed=seed if seed is not None else rng.randint(0, 99999),
            created_at=datetime.utcnow().isoformat(),
        )

        # store internal data
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
                f"Patient: {demo['name']} (ID: {pid})\n"
                f"Insurer: {ins['insurer'].upper()} | Plan: {ins['plan_id']}\n"
                f"Diagnosis: {patient_data['diagnosis_codes'][0]['description']} ({patient_data['diagnosis_codes'][0]['code']})\n"
                f"Requested: {proc['description']} (CPT {proc['cpt_code']})\n"
                f"You have {state.max_steps} steps. Use the available actions to gather evidence and submit your decision."
            ),
            success=True,
            reward=0.0,
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
            obs = PTPAObservation(result="", success=False, reward=0.0, error="Episode not found", done=True)
            raise KeyError(f"Episode not found: {episode_id}")

        state: PTPAState = ep["state"]
        patient_data = ep["patient_data"]
        queried: set = ep["queried_sections"]
        progress: EpisodeProgress = state.progress

        state.step_count += 1
        at = action.action_type.value

        # Dispatch to handler
        handler = _ACTION_HANDLERS.get(action.action_type)
        if handler is None:
            obs = PTPAObservation(
                result=f"Unknown action type: {at}",
                success=False,
                reward=0.0,
                error=f"Invalid action type: {at}",
                step_count=state.step_count,
            )
            reward, reason = no_reward("Invalid action")
        else:
            obs, new_info = handler(action, patient_data, ep, progress)
            obs.step_count = state.step_count

            section_key = f"{at}:{action.parameters.get('section', '')}"
            reward, reason = compute_step_reward(
                action_type=at,
                action_succeeded=obs.success,
                new_info_found=new_info,
                queried_sections=queried,
                current_section=section_key,
            )
            if new_info:
                queried.add(section_key)

        # Check done
        done = False
        if progress.decision_submitted:
            done = True
        if state.step_count >= state.max_steps:
            done = True

        obs.done = done
        obs.reward = reward
        obs.reward_reason = reason
        progress.total_reward_so_far += reward

        if done:
            state.status = EpisodeStatus.GRADING

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


# =========================================================================
# ACTION HANDLERS
# =========================================================================

def _handle_query_patient_record(
    action: PTPAAction, patient: dict, ep: dict, progress: EpisodeProgress
) -> Tuple[PTPAObservation, bool]:
    section = action.parameters.get("section", "")
    data = patient.get(section)
    if data is None:
        return PTPAObservation(result=f"Unknown PRS section: {section}", success=False, reward=0.0, error=f"Invalid section: {section}"), False

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
                label=lab.get("test", ""),
                value=lab.get("value"),
                unit=lab.get("unit"),
                date=lab.get("date"),
                source_section="lab_results",
                clinically_significant=True,
            ))

    return PTPAObservation(result=result, success=True, reward=0.0, found_evidence=evidence), new_info


def _handle_query_policy_database(
    action: PTPAAction, patient: dict, ep: dict, progress: EpisodeProgress
) -> Tuple[PTPAObservation, bool]:
    insurer = action.parameters.get("insurer", "").lower()
    section = action.parameters.get("section", "")
    policy = _POLICIES.get(insurer)
    if policy is None:
        return PTPAObservation(result=f"Unknown insurer: {insurer}", success=False, reward=0.0, error=f"Insurer not found: {insurer}"), False

    section_data = policy.get(section)
    if section_data is None:
        return PTPAObservation(result=f"Policy section '{section}' not found for {insurer}", success=False, reward=0.0), False

    progress.policy_retrieved = True
    cpt = action.parameters.get("cpt_code")

    if isinstance(section_data, dict) and cpt and cpt in section_data:
        detail = section_data[cpt]
        result = f"Policy [{insurer.upper()}] section '{section}' for CPT {cpt}:\n  {detail}"
        rule = PolicyRule(insurer=insurer, section=section, rule_id=f"{insurer}-{section}-{cpt}", description=str(detail))
    else:
        result = f"Policy [{insurer.upper()}] section '{section}':\n  {section_data}"
        rule = PolicyRule(insurer=insurer, section=section, rule_id=f"{insurer}-{section}", description=str(section_data))

    return PTPAObservation(result=result, success=True, reward=0.0, policy_rule=rule), True


def _handle_check_eligibility(
    action: PTPAAction, patient: dict, ep: dict, progress: EpisodeProgress
) -> Tuple[PTPAObservation, bool]:
    member_id = action.parameters.get("member_id", "")
    insurer = action.parameters.get("insurer", "").lower()

    ins = patient["insurance"]
    actual_member = ins["member_id"]
    actual_insurer = ins["insurer"]
    active = ins["active_status"]

    if member_id != actual_member:
        return PTPAObservation(result=f"Member ID {member_id} not found for insurer {insurer}.", success=True, reward=0.0), True

    progress.eligibility_verified = True
    status_str = "ACTIVE" if active else f"INACTIVE (terminated {ins.get('termination_date', 'N/A')})"
    result = (
        f"Eligibility check for {member_id} ({insurer.upper()}):\n"
        f"  Status: {status_str}\n"
        f"  Plan: {ins['plan_id']}\n"
        f"  Effective: {ins['effective_date']}"
    )
    return PTPAObservation(result=result, success=True, reward=0.0), True


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
        return PTPAObservation(result=result, success=True, reward=0.0), True

    covered = entry.get("covered", False)
    covered_icd10 = entry.get("icd10", [])
    section_ref = entry.get("section", "")

    icd_match = icd10 in covered_icd10 if covered_icd10 else True
    final_covered = covered and icd_match

    result = (
        f"CPT Coverage Check [{insurer.upper()}]:\n"
        f"  CPT: {cpt} | ICD-10: {icd10}\n"
        f"  Covered: {'YES' if final_covered else 'NO'}\n"
        f"  Policy Section: {section_ref}\n"
    )
    if entry.get("note"):
        result += f"  Note: {entry['note']}\n"

    evidence = [EvidenceItem(
        evidence_type="policy_rule",
        label=f"CPT {cpt} coverage",
        value="covered" if final_covered else "not covered",
        unit=None,
        date=None,
        source_section=section_ref,
        clinically_significant=True,
    )]
    return PTPAObservation(result=result, success=True, reward=0.0, found_evidence=evidence), True


def _handle_extract_pt_sessions(
    action: PTPAAction, patient: dict, ep: dict, progress: EpisodeProgress
) -> Tuple[PTPAObservation, bool]:
    sessions_raw = patient.get("pt_sessions", [])
    progress.pt_sessions_extracted = True

    if not sessions_raw:
        return PTPAObservation(result="No physical therapy sessions found in patient record.", success=True, reward=0.0), False

    pt_sessions = []
    lines = []
    for s in sessions_raw:
        pt = PTSession(
            session_date=s["session_date"],
            session_number=s["session_number"],
            therapist_notes=s["therapist_notes"],
            functional_outcome=s.get("functional_outcome"),
            pain_score=s.get("pain_score"),
            improved=s.get("improved", False),
        )
        pt_sessions.append(pt)
        lines.append(f"  Session {pt.session_number} ({pt.session_date}): {pt.therapist_notes}")

    first = sessions_raw[0]["session_date"]
    last = sessions_raw[-1]["session_date"]
    result = (
        f"Physical Therapy Sessions ({len(sessions_raw)} total):\n"
        f"  Date range: {first} to {last}\n"
        + "\n".join(lines)
    )

    evidence = [EvidenceItem(
        evidence_type="pt_session",
        label="PT session history",
        value=f"{len(sessions_raw)} sessions from {first} to {last}",
        unit=None,
        date=None,
        source_section="pt_sessions",
        clinically_significant=True,
    )]

    return PTPAObservation(result=result, success=True, reward=0.0, pt_sessions=pt_sessions, found_evidence=evidence), True


def _handle_check_red_flags(
    action: PTPAAction, patient: dict, ep: dict, progress: EpisodeProgress
) -> Tuple[PTPAObservation, bool]:
    progress.red_flags_checked = True
    exam_notes = patient.get("physical_exam", [])
    progress_notes = patient.get("progress_notes", [])

    red_flags: List[RedFlagItem] = []
    all_text = " ".join(
        [e.get("findings", "") for e in exam_notes]
        + [n.get("note", "") for n in progress_notes]
    ).upper()

    if "TRUE LOCKING" in all_text or "LOCKED" in all_text:
        red_flags.append(RedFlagItem(
            flag_name="True Locking",
            description="Knee locked in flexion — suspected torn meniscus with mechanical block",
            bypasses_requirement="Conservative therapy duration requirement",
            severity="critical",
        ))
    if "TUMOR" in all_text or "MASS" in all_text:
        red_flags.append(RedFlagItem(flag_name="Suspected Tumor", description="Possible mass/tumor on imaging or exam", bypasses_requirement="Conservative therapy", severity="critical"))
    if "INFECTION" in all_text:
        red_flags.append(RedFlagItem(flag_name="Suspected Infection", description="Signs of joint infection", bypasses_requirement="Conservative therapy", severity="critical"))
    if "PROGRESSIVE NEUROLOGICAL" in all_text or "NEUROLOGICAL DEFICIT" in all_text:
        red_flags.append(RedFlagItem(flag_name="Progressive Neurological Deficit", description="Progressive neurological symptoms", bypasses_requirement="Conservative therapy", severity="critical"))
    if "FRACTURE" in all_text:
        red_flags.append(RedFlagItem(flag_name="Fracture", description="Fracture identified on imaging", bypasses_requirement="Conservative therapy", severity="high"))

    if red_flags:
        lines = [f"  - {rf.flag_name}: {rf.description} (BYPASSES: {rf.bypasses_requirement})" for rf in red_flags]
        result = f"RED FLAGS DETECTED ({len(red_flags)}):\n" + "\n".join(lines)
    else:
        result = "No clinical red flags detected. Standard policy requirements apply."

    return PTPAObservation(result=result, success=True, reward=0.0, red_flags=red_flags), True


def _handle_compare_policy_duration(
    action: PTPAAction, patient: dict, ep: dict, progress: EpisodeProgress
) -> Tuple[PTPAObservation, bool]:
    weeks = action.parameters.get("weeks_of_pt_found", 0)
    insurer = action.parameters.get("insurer", "").lower()
    cpt = action.parameters.get("cpt_code", "")

    policy = _POLICIES.get(insurer, {})
    criteria = policy.get("prior_auth_criteria", {}).get(cpt, {})
    required_weeks = criteria.get("conservative_therapy_weeks", 6)

    met = weeks >= required_weeks
    result = (
        f"Policy Duration Comparison [{insurer.upper()}] CPT {cpt}:\n"
        f"  Required: {required_weeks} weeks of conservative therapy\n"
        f"  Documented: {weeks} weeks\n"
        f"  Requirement Met: {'YES' if met else 'NO'}"
    )

    evidence = [EvidenceItem(
        evidence_type="policy_rule",
        label="PT duration comparison",
        value=f"{weeks} vs {required_weeks} weeks",
        unit=None,
        date=None,
        source_section=None,
        clinically_significant=True,
    )]
    return PTPAObservation(result=result, success=True, reward=0.0, found_evidence=evidence), True


def _handle_extract_lab_values(
    action: PTPAAction, patient: dict, ep: dict, progress: EpisodeProgress
) -> Tuple[PTPAObservation, bool]:
    requested_tests = action.parameters.get("lab_tests", [])
    progress.lab_values_extracted = True

    labs = patient.get("lab_results", [])
    if not labs:
        return PTPAObservation(result="No lab results found in patient record.", success=True, reward=0.0), False

    found = []
    evidence = []
    for lab in labs:
        test_name = lab.get("test", "")
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
        return PTPAObservation(result=f"No matching lab results for: {requested_tests}", success=True, reward=0.0), False

    lines = [f"  {l['test']}: {l['value']} {l.get('unit','')} ({l.get('date','')}) [ref: {l.get('reference_range','')}]" for l in found]
    result = f"Lab Values ({len(found)} results):\n" + "\n".join(lines)
    return PTPAObservation(result=result, success=True, reward=0.0, found_evidence=evidence), True


def _handle_check_step_therapy(
    action: PTPAAction, patient: dict, ep: dict, progress: EpisodeProgress
) -> Tuple[PTPAObservation, bool]:
    device = action.parameters.get("device_requested", "CGM")
    insurer = action.parameters.get("insurer", "").lower()
    progress.step_therapy_checked = True

    pharmacy = patient.get("pharmacy_history", [])
    insulin_injections = 0
    for med in pharmacy:
        name = med.get("medication", "").lower()
        freq = med.get("frequency", "").lower()
        if "insulin" in name and ("subcutaneous" in med.get("route", "").lower() or "inject" in freq):
            if "daily" in freq:
                if "once" in freq:
                    insulin_injections += 1
                elif "3x" in freq or "three" in freq:
                    insulin_injections += 3
                elif "twice" in freq or "2x" in freq:
                    insulin_injections += 2
                else:
                    insulin_injections += 1

    policy = _POLICIES.get(insurer, {})
    step_rules = policy.get("step_therapy_rules", {}).get(device, {})
    required = step_rules.get("min_daily_insulin_injections", 2)
    met = insulin_injections >= required

    result = (
        f"Step Therapy Check [{insurer.upper()}] for {device}:\n"
        f"  Required: ≥{required} daily insulin injections\n"
        f"  Found: {insulin_injections} daily insulin administrations\n"
        f"  Step Therapy Met: {'YES' if met else 'NO'}"
    )
    if not met:
        result += "\n  Note: Patient does not meet insulin injection requirement for CGM coverage."

    evidence = [EvidenceItem(
        evidence_type="policy_rule",
        label="Step therapy compliance",
        value="met" if met else "not met",
        unit=None,
        date=None,
        source_section=None,
        clinically_significant=True,
    )]
    return PTPAObservation(result=result, success=True, reward=0.0, found_evidence=evidence), True


def _handle_generate_appeal_letter(
    action: PTPAAction, patient: dict, ep: dict, progress: EpisodeProgress
) -> Tuple[PTPAObservation, bool]:
    evidence_found = action.parameters.get("evidence_found", [])
    exception_clause = action.parameters.get("exception_clause", "")
    physician_name = action.parameters.get("physician_name", patient.get("attending_physician", ""))
    physician_npi = action.parameters.get("physician_npi", "1234567890")

    demo = patient["demographics"]
    ins = patient["insurance"]
    proc = patient["requested_procedure"]
    dx = patient["diagnosis_codes"][0]

    letter = (
        f"LETTER OF MEDICAL NECESSITY\n"
        f"{'='*50}\n"
        f"Date: {datetime.utcnow().strftime('%Y-%m-%d')}\n"
        f"To: {ins['insurer'].upper()} Medical Review Department\n"
        f"Re: Appeal for {proc['description']} (CPT {proc['cpt_code']})\n"
        f"Patient: {demo['name']} | Member ID: {ins['member_id']}\n"
        f"Diagnosis: {dx['description']} (ICD-10: {dx['code']})\n\n"
        f"Dear Medical Review Team,\n\n"
        f"I am writing to appeal the denial of {proc['description']} for my patient "
        f"{demo['name']}. Based on the following clinical evidence, this patient meets "
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

    return PTPAObservation(result=result, success=True, reward=0.0), True


def _handle_submit_decision(
    action: PTPAAction, patient: dict, ep: dict, progress: EpisodeProgress
) -> Tuple[PTPAObservation, bool]:
    decision = action.parameters.get("decision", "")
    rationale = action.parameters.get("rationale", "")

    if len(rationale) < 20:
        return PTPAObservation(
            result="Rationale must be at least 20 characters.",
            success=False,
            reward=0.0,
            error="Rationale too short (min 20 chars)",
        ), False

    progress.decision_submitted = True
    ep["submitted_decision"] = action.parameters

    result = (
        f"Decision submitted: {decision.upper()}\n"
        f"Rationale: {rationale}\n"
        f"Episode complete. Call POST /grader to receive your score."
    )
    return PTPAObservation(result=result, success=True, reward=0.0), True


# Handler registry
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

    # Eligibility (40%)
    elig_score = 1.0 if progress.eligibility_verified else 0.0

    # Procedure coverage (40%)
    cov_score = 1.0 if progress.cpt_coverage_checked else 0.0

    # Check decision correctness
    try:
        agent_decision = AuthorizationDecision(agent_decision_str)
        decision_correct = agent_decision == correct_decision
    except ValueError:
        agent_decision = None
        decision_correct = False

    if not decision_correct:
        elig_score *= 0.5
        cov_score *= 0.5

    # Rationale (20%)
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
        task_id=TaskID.VERIFICATION,
        episode_id=episode_id,
        final_score=round(final, 4),
        components=components,
        decision_made=agent_decision,
        decision_correct=decision_correct,
        feedback=f"Decision: {agent_decision_str} | Correct: {correct_decision.value if correct_decision else 'N/A'} | Score: {final:.2f}",
        appeal_letter_score=None,
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

    # Evidence extraction (35%)
    ev_score = 1.0 if progress.pt_sessions_extracted else 0.0

    # Policy duration logic (30%)
    dur_score = 0.0
    if progress.policy_retrieved:
        dur_score = 0.5
    if decision_correct:
        dur_score = 1.0

    # Red flag recognition (20%)
    rf_score = 0.0
    has_rf = key.get("red_flag_present", False)
    if progress.red_flags_checked:
        rf_score = 1.0  # correctly checked

    # Final decision (15%)
    dec_score = 1.0 if decision_correct else 0.0

    components = [
        GraderComponentScore(component_name="evidence_extraction", weight=0.35, score=ev_score, weighted_score=0.35 * ev_score, passed=ev_score > 0.5, feedback=f"PT sessions extracted: {progress.pt_sessions_extracted}"),
        GraderComponentScore(component_name="policy_duration_logic", weight=0.30, score=dur_score, weighted_score=0.30 * dur_score, passed=dur_score > 0.5, feedback=f"Duration logic score: {dur_score}"),
        GraderComponentScore(component_name="red_flag_recognition", weight=0.20, score=rf_score, weighted_score=0.20 * rf_score, passed=rf_score > 0.5, feedback=f"Red flags checked: {progress.red_flags_checked}, present: {has_rf}"),
        GraderComponentScore(component_name="final_decision_accuracy", weight=0.15, score=dec_score, weighted_score=0.15 * dec_score, passed=decision_correct, feedback=f"Decision correct: {decision_correct}"),
    ]
    final = sum(c.weighted_score for c in components)

    return GraderResult(
        task_id=TaskID.MRI_NECESSITY,
        episode_id=episode_id,
        final_score=round(final, 4),
        components=components,
        decision_made=agent_decision,
        decision_correct=decision_correct,
        feedback=f"Decision: {agent_decision_str} | Correct: {correct_decision.value if correct_decision else 'N/A'} | Score: {final:.2f}",
        appeal_letter_score=None,
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
        if qv and str(int(qv)) in rationale:
            metric_score = 1.0
        elif key.get("exception_type") and key["exception_type"].replace("_", " ") in rationale.lower():
            metric_score = 0.75

    # Rationale mapping (30%)
    rat_score = 0.0
    correct_clause = key.get("correct_exception_clause", "")
    rationale = submitted.get("rationale", "")
    policy_cited = submitted.get("policy_section_cited", "")
    if correct_clause:
        if correct_clause.lower() in rationale.lower() or correct_clause.lower() in policy_cited.lower():
            rat_score = 1.0
        elif key.get("insurer", "") in rationale.lower() and "exception" in rationale.lower():
            rat_score = 0.5

    # Appeal letter quality (30%) — keyword-based fallback for LLM judge
    letter_score = 0.0
    letter = ep.get("appeal_letter", "")
    if letter:
        checks = 0
        if any(dx["code"] in letter for dx in ep["patient_data"].get("diagnosis_codes", [])):
            checks += 1  # ICD codes
        if any(str(lab.get("value")) in letter for lab in ep["patient_data"].get("lab_results", [])):
            checks += 1  # Lab values
        if correct_clause and any(word in letter.lower() for word in correct_clause.lower().split()):
            checks += 1  # Exception clause
        if "dear" in letter.lower() or "to:" in letter.lower():
            checks += 1  # Professional format
        if "npi" in letter.lower() or "respectfully" in letter.lower():
            checks += 1  # Physician attestation
        letter_score = checks / 5.0

    components = [
        GraderComponentScore(component_name="metric_identification", weight=0.40, score=metric_score, weighted_score=0.40 * metric_score, passed=metric_score > 0.5, feedback=f"Metric identification: {metric_score}"),
        GraderComponentScore(component_name="rationale_mapping", weight=0.30, score=rat_score, weighted_score=0.30 * rat_score, passed=rat_score > 0.5, feedback=f"Rationale mapping: {rat_score}"),
        GraderComponentScore(component_name="appeal_letter_quality", weight=0.30, score=letter_score, weighted_score=0.30 * letter_score, passed=letter_score > 0.5, feedback=f"Appeal letter score: {letter_score}"),
    ]
    final = sum(c.weighted_score for c in components)

    return GraderResult(
        task_id=TaskID.CGM_APPEAL,
        episode_id=episode_id,
        final_score=round(final, 4),
        components=components,
        decision_made=agent_decision,
        decision_correct=decision_correct,
        feedback=f"Decision: {agent_decision_str} | Correct: {correct_decision.value if correct_decision else 'N/A'} | Score: {final:.2f}",
        appeal_letter_score=round(letter_score, 4),
    )

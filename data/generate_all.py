"""
generate_all.py  –  Generate PAT-021 … PAT-050 patient JSON files.

  Task 1  (PAT-021 – PAT-025)  Coverage-eligibility checks
  Task 2  (PAT-026 – PAT-030)  PT / red-flag medical-necessity
  Task 3  (PAT-031 – PAT-035)  CGM step-therapy / exception criteria
  Task 4  (PAT-036 – PAT-050)  Peer-to-Peer Review (denial rebuttals)

Usage:
    python data/generate_all.py
"""

import json
import os

OUT = os.path.join(os.path.dirname(__file__), "prs")

patients = {}

# ──────────────────────────────────────────────────────────────────────
# TASK 1 – Coverage / Eligibility  (PAT-021 … PAT-025)
# ──────────────────────────────────────────────────────────────────────

patients["PAT-021"] = {
    "patient_id": "PAT-021",
    "demographics": {
        "name": "Priya Sharma",
        "dob": "1974-03-28",
        "gender": "female"
    },
    "insurance": {
        "member_id": "MBR-310021",
        "insurer": "cigna",
        "plan_id": "CIGNA-OPEN-ACCESS",
        "active": True
    },
    "vitals": {
        "height_cm": 162,
        "weight_kg": 68,
        "bmi": 25.9,
        "bp": "128/78"
    },
    "diagnosis_codes": [
        {
            "code": "M54.5",
            "description": "Low back pain",
            "primary": True
        }
    ],
    "progress_notes": [
        {
            "date": "2024-09-10",
            "note": "Chronic lumbar pain radiating to left leg, worsening over 4 months. Conservative therapy ongoing."
        }
    ],
    "physical_exam": [
        {
            "date": "2024-09-10",
            "findings": "Paravertebral tenderness L3-L5. Positive SLR left at 50 degrees. No motor deficit."
        }
    ],
    "lab_results": [],
    "pt_sessions": [],
    "pharmacy_history": [
        {
            "medication": "Naproxen 500mg",
            "start_date": "2024-05-01",
            "duration_days": 120
        }
    ],
    "imaging_history": [
        {
            "type": "X-ray",
            "date": "2024-06-15",
            "findings": "Mild disc space narrowing L4-L5."
        }
    ],
    "requested_procedure": {
        "cpt_code": "72148",
        "description": "MRI lumbar spine without contrast"
    },
    "attending_physician": "Dr. James Lee"
}

patients["PAT-022"] = {
    "patient_id": "PAT-022",
    "demographics": {
        "name": "David Okonkwo",
        "dob": "1969-07-14",
        "gender": "male"
    },
    "insurance": {
        "member_id": "MBR-310022",
        "insurer": "aetna",
        "plan_id": "AETNA-GOLD-PPO",
        "active": True
    },
    "vitals": {
        "height_cm": 185,
        "weight_kg": 96,
        "bmi": 28.0,
        "bp": "142/88"
    },
    "diagnosis_codes": [
        {
            "code": "M75.10",
            "description": "Rotator cuff syndrome, unspecified shoulder",
            "primary": True
        }
    ],
    "progress_notes": [
        {
            "date": "2024-08-20",
            "note": "Right shoulder pain with overhead activities for 3 months. Weakness on external rotation."
        }
    ],
    "physical_exam": [
        {
            "date": "2024-08-20",
            "findings": "Positive Neer impingement. Positive empty can test. ROM abduction limited to 120 degrees."
        }
    ],
    "lab_results": [],
    "pt_sessions": [],
    "pharmacy_history": [
        {
            "medication": "Meloxicam 15mg",
            "start_date": "2024-06-01",
            "duration_days": 80
        }
    ],
    "imaging_history": [
        {
            "type": "X-ray",
            "date": "2024-07-10",
            "findings": "No fracture. Mild subacromial spurring."
        }
    ],
    "requested_procedure": {
        "cpt_code": "73221",
        "description": "MRI right shoulder without contrast"
    },
    "attending_physician": "Dr. Emily Tanaka"
}

patients["PAT-023"] = {
    "patient_id": "PAT-023",
    "demographics": {
        "name": "Fatima Al-Rashid",
        "dob": "1980-12-05",
        "gender": "female"
    },
    "insurance": {
        "member_id": "MBR-310023",
        "insurer": "cms",
        "plan_id": "MEDICARE-PART-B",
        "active": False
    },
    "vitals": {
        "height_cm": 158,
        "weight_kg": 72,
        "bmi": 28.8,
        "bp": "130/82"
    },
    "diagnosis_codes": [
        {
            "code": "M17.11",
            "description": "Primary osteoarthritis, right knee",
            "primary": True
        }
    ],
    "progress_notes": [
        {
            "date": "2024-10-01",
            "note": "Right knee pain with weight bearing. Requesting MRI for surgical planning."
        }
    ],
    "physical_exam": [
        {
            "date": "2024-10-01",
            "findings": "Crepitus bilateral knees. ROM 5-115 degrees right. Mild valgus deformity."
        }
    ],
    "lab_results": [],
    "pt_sessions": [],
    "pharmacy_history": [
        {
            "medication": "Acetaminophen 1000mg",
            "start_date": "2024-07-01",
            "duration_days": 90
        }
    ],
    "imaging_history": [
        {
            "type": "X-ray",
            "date": "2024-08-15",
            "findings": "Moderate medial joint space narrowing right knee."
        }
    ],
    "requested_procedure": {
        "cpt_code": "73721",
        "description": "MRI right knee without contrast"
    },
    "attending_physician": "Dr. Alan Brooks"
}

patients["PAT-024"] = {
    "patient_id": "PAT-024",
    "demographics": {
        "name": "Marcus Jefferson",
        "dob": "1988-05-19",
        "gender": "male"
    },
    "insurance": {
        "member_id": "MBR-310024",
        "insurer": "united",
        "plan_id": "UHC-CHOICE-PLUS",
        "active": True
    },
    "vitals": {
        "height_cm": 180,
        "weight_kg": 84,
        "bmi": 25.9,
        "bp": "124/76"
    },
    "diagnosis_codes": [
        {
            "code": "G43.909",
            "description": "Migraine, unspecified",
            "primary": True
        }
    ],
    "progress_notes": [
        {
            "date": "2024-09-15",
            "note": "Chronic migraines 3-4 times per week. Failed multiple prophylactic agents. Requesting brain MRI to rule out secondary cause."
        }
    ],
    "physical_exam": [
        {
            "date": "2024-09-15",
            "findings": "Cranial nerves II-XII intact. No papilledema. No focal neurological deficits."
        }
    ],
    "lab_results": [],
    "pt_sessions": [],
    "pharmacy_history": [
        {
            "medication": "Topiramate 100mg",
            "start_date": "2024-03-01",
            "duration_days": 180
        },
        {
            "medication": "Sumatriptan 100mg",
            "start_date": "2024-01-01",
            "duration_days": 240
        }
    ],
    "imaging_history": [],
    "requested_procedure": {
        "cpt_code": "70553",
        "description": "MRI brain with and without contrast"
    },
    "attending_physician": "Dr. Nora Reyes"
}

patients["PAT-025"] = {
    "patient_id": "PAT-025",
    "demographics": {
        "name": "Yuki Tanaka",
        "dob": "1958-09-02",
        "gender": "female"
    },
    "insurance": {
        "member_id": "MBR-310025",
        "insurer": "cigna",
        "plan_id": "CIGNA-HMO-STANDARD",
        "active": True
    },
    "vitals": {
        "height_cm": 155,
        "weight_kg": 65,
        "bmi": 27.1,
        "bp": "136/80"
    },
    "diagnosis_codes": [
        {
            "code": "M17.11",
            "description": "Primary osteoarthritis, right knee",
            "primary": True
        }
    ],
    "progress_notes": [
        {
            "date": "2024-10-05",
            "note": "Progressive right knee pain limiting ADLs. Stair climbing severely affected. Requesting MRI."
        }
    ],
    "physical_exam": [
        {
            "date": "2024-10-05",
            "findings": "Bony enlargement medial compartment. Crepitus on flexion/extension. ROM 0-110. Mild effusion."
        }
    ],
    "lab_results": [],
    "pt_sessions": [],
    "pharmacy_history": [
        {
            "medication": "Diclofenac 75mg",
            "start_date": "2024-06-01",
            "duration_days": 120
        }
    ],
    "imaging_history": [
        {
            "type": "X-ray",
            "date": "2024-08-01",
            "findings": "Moderate-severe medial joint space narrowing. Osteophyte formation."
        }
    ],
    "requested_procedure": {
        "cpt_code": "73721",
        "description": "MRI right knee without contrast"
    },
    "attending_physician": "Dr. Kevin Park"
}

# ──────────────────────────────────────────────────────────────────────
# TASK 2 – PT duration / Red-flag bypass  (PAT-026 … PAT-030)
# ──────────────────────────────────────────────────────────────────────

patients["PAT-026"] = {
    "patient_id": "PAT-026",
    "demographics": {
        "name": "Ahmed Hassan",
        "dob": "1971-06-22",
        "gender": "male"
    },
    "insurance": {
        "member_id": "MBR-310026",
        "insurer": "cigna",
        "plan_id": "CIGNA-OPEN-ACCESS",
        "active": True
    },
    "vitals": {
        "height_cm": 176,
        "weight_kg": 85,
        "bmi": 27.4,
        "bp": "134/84"
    },
    "diagnosis_codes": [
        {
            "code": "M17.11",
            "description": "Primary osteoarthritis, right knee",
            "primary": True
        }
    ],
    "progress_notes": [
        {
            "date": "2024-03-15",
            "note": "Right knee pain persistent after 7 weeks of structured PT. No significant improvement."
        },
        {
            "date": "2024-04-28",
            "note": "Completed full PT course. Pain persists 6/10. Requesting MRI to evaluate internal derangement."
        }
    ],
    "physical_exam": [
        {
            "date": "2024-04-28",
            "findings": "Medial joint line tenderness. Crepitus. ROM 5-115. No effusion. No locking."
        }
    ],
    "lab_results": [],
    "pt_sessions": [
        {"session_date": "2024-03-04", "session_number": 1, "therapist_notes": "Initial eval. ROM exercises.", "pain_score": 7, "improved": False},
        {"session_date": "2024-03-08", "session_number": 2, "therapist_notes": "Quad strengthening.", "pain_score": 7, "improved": False},
        {"session_date": "2024-03-12", "session_number": 3, "therapist_notes": "Stationary bike added.", "pain_score": 6, "improved": True},
        {"session_date": "2024-03-15", "session_number": 4, "therapist_notes": "Hamstring stretching.", "pain_score": 6, "improved": False},
        {"session_date": "2024-03-19", "session_number": 5, "therapist_notes": "Closed-chain exercises.", "pain_score": 6, "improved": False},
        {"session_date": "2024-03-22", "session_number": 6, "therapist_notes": "Balance training.", "pain_score": 6, "improved": False},
        {"session_date": "2024-03-26", "session_number": 7, "therapist_notes": "Step-ups initiated.", "pain_score": 6, "improved": False},
        {"session_date": "2024-03-29", "session_number": 8, "therapist_notes": "No further gains.", "pain_score": 6, "improved": False},
        {"session_date": "2024-04-02", "session_number": 9, "therapist_notes": "Plateau reached.", "pain_score": 6, "improved": False},
        {"session_date": "2024-04-05", "session_number": 10, "therapist_notes": "Recommends advanced imaging.", "pain_score": 6, "improved": False},
        {"session_date": "2024-04-09", "session_number": 11, "therapist_notes": "Maintenance only.", "pain_score": 6, "improved": False},
        {"session_date": "2024-04-12", "session_number": 12, "therapist_notes": "Aquatic therapy trial.", "pain_score": 6, "improved": False},
        {"session_date": "2024-04-16", "session_number": 13, "therapist_notes": "No change.", "pain_score": 6, "improved": False},
        {"session_date": "2024-04-19", "session_number": 14, "therapist_notes": "Discharged from PT. MRI recommended.", "pain_score": 6, "improved": False}
    ],
    "pharmacy_history": [
        {
            "medication": "Ibuprofen 600mg",
            "start_date": "2024-02-01",
            "duration_days": 90
        }
    ],
    "imaging_history": [
        {
            "type": "X-ray",
            "date": "2024-02-20",
            "findings": "Mild medial joint space narrowing."
        }
    ],
    "requested_procedure": {
        "cpt_code": "73721",
        "description": "MRI right knee without contrast"
    },
    "attending_physician": "Dr. Lisa Wang"
}

patients["PAT-027"] = {
    "patient_id": "PAT-027",
    "demographics": {
        "name": "Elena Vasquez",
        "dob": "1966-11-08",
        "gender": "female"
    },
    "insurance": {
        "member_id": "MBR-310027",
        "insurer": "aetna",
        "plan_id": "AETNA-GOLD-PPO",
        "active": True
    },
    "vitals": {
        "height_cm": 165,
        "weight_kg": 72,
        "bmi": 26.4,
        "bp": "140/86"
    },
    "diagnosis_codes": [
        {
            "code": "M54.5",
            "description": "Low back pain",
            "primary": True
        },
        {
            "code": "G54.4",
            "description": "Lumbosacral root disorder",
            "primary": False
        }
    ],
    "progress_notes": [
        {
            "date": "2024-07-01",
            "note": "Acute low back pain with left leg weakness. Unable to dorsiflex left foot. Only 2 weeks of PT completed."
        },
        {
            "date": "2024-07-10",
            "note": "Neurological Deficit confirmed: left foot drop 2/5 dorsiflexion. Urgent MRI needed."
        }
    ],
    "physical_exam": [
        {
            "date": "2024-07-10",
            "findings": "Left foot drop — dorsiflexion 2/5. Absent left ankle jerk. Positive SLR left at 25 degrees. Sensory loss L5 dermatome.",
            "red_flags": [
                "Neurological Deficit"
            ]
        }
    ],
    "lab_results": [],
    "pt_sessions": [
        {"session_date": "2024-06-28", "session_number": 1, "therapist_notes": "Initial eval. Significant radiculopathy.", "pain_score": 8, "improved": False},
        {"session_date": "2024-07-02", "session_number": 2, "therapist_notes": "Unable to perform exercises due to weakness.", "pain_score": 9, "improved": False},
        {"session_date": "2024-07-05", "session_number": 3, "therapist_notes": "Worsening deficit. Referred back to physician.", "pain_score": 9, "improved": False},
        {"session_date": "2024-07-09", "session_number": 4, "therapist_notes": "Discharged. Imaging urgently needed.", "pain_score": 9, "improved": False}
    ],
    "pharmacy_history": [
        {
            "medication": "Gabapentin 300mg",
            "start_date": "2024-06-25",
            "duration_days": 21
        },
        {
            "medication": "Methylprednisolone dose pack",
            "start_date": "2024-07-01",
            "duration_days": 6
        }
    ],
    "imaging_history": [
        {
            "type": "X-ray",
            "date": "2024-06-26",
            "findings": "Disc space narrowing L4-L5 and L5-S1."
        }
    ],
    "requested_procedure": {
        "cpt_code": "72148",
        "description": "MRI lumbar spine without contrast"
    },
    "attending_physician": "Dr. James Lee"
}

patients["PAT-028"] = {
    "patient_id": "PAT-028",
    "demographics": {
        "name": "Wei Zhang",
        "dob": "1976-02-18",
        "gender": "male"
    },
    "insurance": {
        "member_id": "MBR-310028",
        "insurer": "cms",
        "plan_id": "MEDICARE-PART-B",
        "active": True
    },
    "vitals": {
        "height_cm": 172,
        "weight_kg": 78,
        "bmi": 26.4,
        "bp": "126/78"
    },
    "diagnosis_codes": [
        {
            "code": "M54.5",
            "description": "Low back pain",
            "primary": True
        }
    ],
    "progress_notes": [
        {
            "date": "2024-08-20",
            "note": "Low back pain 3 weeks. Started PT two weeks ago. Wants MRI now."
        }
    ],
    "physical_exam": [
        {
            "date": "2024-08-20",
            "findings": "Paravertebral muscle spasm L3-L5. Negative SLR bilaterally. Full strength lower extremities. No red flags."
        }
    ],
    "lab_results": [],
    "pt_sessions": [
        {"session_date": "2024-08-05", "session_number": 1, "therapist_notes": "Initial eval. Core stabilization.", "pain_score": 6, "improved": False},
        {"session_date": "2024-08-09", "session_number": 2, "therapist_notes": "Stretching program.", "pain_score": 6, "improved": False},
        {"session_date": "2024-08-12", "session_number": 3, "therapist_notes": "Mild improvement.", "pain_score": 5, "improved": True},
        {"session_date": "2024-08-16", "session_number": 4, "therapist_notes": "Continued strengthening.", "pain_score": 5, "improved": False},
        {"session_date": "2024-08-19", "session_number": 5, "therapist_notes": "Progressive exercises.", "pain_score": 5, "improved": False},
        {"session_date": "2024-08-22", "session_number": 6, "therapist_notes": "Ongoing. Patient wants to stop for imaging.", "pain_score": 5, "improved": False}
    ],
    "pharmacy_history": [
        {
            "medication": "Naproxen 500mg",
            "start_date": "2024-08-01",
            "duration_days": 30
        }
    ],
    "imaging_history": [],
    "requested_procedure": {
        "cpt_code": "72148",
        "description": "MRI lumbar spine without contrast"
    },
    "attending_physician": "Dr. Alan Brooks"
}

patients["PAT-029"] = {
    "patient_id": "PAT-029",
    "demographics": {
        "name": "Olivia Mensah",
        "dob": "1983-04-11",
        "gender": "female"
    },
    "insurance": {
        "member_id": "MBR-310029",
        "insurer": "aetna",
        "plan_id": "AETNA-BASIC-EPO",
        "active": True
    },
    "vitals": {
        "height_cm": 168,
        "weight_kg": 74,
        "bmi": 26.2,
        "bp": "122/76"
    },
    "diagnosis_codes": [
        {
            "code": "M17.11",
            "description": "Primary osteoarthritis, right knee",
            "primary": True
        }
    ],
    "progress_notes": [
        {
            "date": "2024-06-01",
            "note": "Right knee pain 3 months. Completed 5 weeks of PT with minimal improvement."
        },
        {
            "date": "2024-07-05",
            "note": "PT plateau. Pain persists at 5/10. Requesting MRI."
        }
    ],
    "physical_exam": [
        {
            "date": "2024-07-05",
            "findings": "Medial joint line tenderness. Positive McMurray. ROM 0-120. No effusion. No locking."
        }
    ],
    "lab_results": [],
    "pt_sessions": [
        {"session_date": "2024-05-27", "session_number": 1, "therapist_notes": "Initial eval.", "pain_score": 6, "improved": False},
        {"session_date": "2024-05-30", "session_number": 2, "therapist_notes": "Quad sets, SLR.", "pain_score": 6, "improved": False},
        {"session_date": "2024-06-03", "session_number": 3, "therapist_notes": "Step exercises.", "pain_score": 6, "improved": False},
        {"session_date": "2024-06-06", "session_number": 4, "therapist_notes": "Mini squats.", "pain_score": 5, "improved": True},
        {"session_date": "2024-06-10", "session_number": 5, "therapist_notes": "Bike added.", "pain_score": 5, "improved": False},
        {"session_date": "2024-06-13", "session_number": 6, "therapist_notes": "Balance board.", "pain_score": 5, "improved": False},
        {"session_date": "2024-06-17", "session_number": 7, "therapist_notes": "Lateral step-downs.", "pain_score": 5, "improved": False},
        {"session_date": "2024-06-20", "session_number": 8, "therapist_notes": "No further gains.", "pain_score": 5, "improved": False},
        {"session_date": "2024-06-24", "session_number": 9, "therapist_notes": "Recommends imaging.", "pain_score": 5, "improved": False},
        {"session_date": "2024-06-27", "session_number": 10, "therapist_notes": "Discharged. MRI advised.", "pain_score": 5, "improved": False}
    ],
    "pharmacy_history": [
        {
            "medication": "Ibuprofen 400mg",
            "start_date": "2024-05-01",
            "duration_days": 60
        }
    ],
    "imaging_history": [
        {
            "type": "X-ray",
            "date": "2024-05-10",
            "findings": "Mild medial joint space narrowing right knee."
        }
    ],
    "requested_procedure": {
        "cpt_code": "73721",
        "description": "MRI right knee without contrast"
    },
    "attending_physician": "Dr. Sarah Mitchell"
}

patients["PAT-030"] = {
    "patient_id": "PAT-030",
    "demographics": {
        "name": "Dmitri Volkov",
        "dob": "1979-08-30",
        "gender": "male"
    },
    "insurance": {
        "member_id": "MBR-310030",
        "insurer": "cigna",
        "plan_id": "CIGNA-OPEN-ACCESS",
        "active": True
    },
    "vitals": {
        "height_cm": 182,
        "weight_kg": 92,
        "bmi": 27.8,
        "bp": "138/86"
    },
    "diagnosis_codes": [
        {
            "code": "M46.46",
            "description": "Discitis, unspecified, lumbar region",
            "primary": True
        },
        {
            "code": "M54.5",
            "description": "Low back pain",
            "primary": False
        }
    ],
    "progress_notes": [
        {
            "date": "2024-09-01",
            "note": "Low back pain with fevers 101.2 F for 5 days. Elevated ESR/CRP. Suspected vertebral infection. Only 4 weeks PT."
        },
        {
            "date": "2024-09-08",
            "note": "Worsening pain at rest. Night sweats. Urgent MRI needed to rule out discitis/osteomyelitis."
        }
    ],
    "physical_exam": [
        {
            "date": "2024-09-08",
            "findings": "Severe midline tenderness L3-L4. Paraspinal muscle guarding. Temperature 101.4 F. No neurological deficit.",
            "red_flags": [
                "Suspected Infection"
            ]
        }
    ],
    "lab_results": [
        {
            "test_name": "ESR",
            "test": "ESR",
            "value": 68,
            "unit": "mm/hr",
            "date": "2024-09-05",
            "reference_range": "0-20 mm/hr"
        },
        {
            "test_name": "CRP",
            "test": "CRP",
            "value": 8.4,
            "unit": "mg/dL",
            "date": "2024-09-05",
            "reference_range": "< 0.5 mg/dL"
        },
        {
            "test_name": "WBC",
            "test": "WBC",
            "value": 14.2,
            "unit": "K/uL",
            "date": "2024-09-05",
            "reference_range": "4.5-11.0 K/uL"
        }
    ],
    "pt_sessions": [
        {"session_date": "2024-08-05", "session_number": 1, "therapist_notes": "Initial eval.", "pain_score": 7, "improved": False},
        {"session_date": "2024-08-09", "session_number": 2, "therapist_notes": "Gentle ROM.", "pain_score": 7, "improved": False},
        {"session_date": "2024-08-14", "session_number": 3, "therapist_notes": "Patient reports fevers.", "pain_score": 8, "improved": False},
        {"session_date": "2024-08-19", "session_number": 4, "therapist_notes": "Worsening. Referred back to MD.", "pain_score": 8, "improved": False},
        {"session_date": "2024-08-23", "session_number": 5, "therapist_notes": "Unable to continue. Fever 101 F.", "pain_score": 9, "improved": False},
        {"session_date": "2024-08-28", "session_number": 6, "therapist_notes": "Discharged from PT. Imaging needed urgently.", "pain_score": 9, "improved": False},
        {"session_date": "2024-09-01", "session_number": 7, "therapist_notes": "Session cancelled. Sent to physician.", "pain_score": 9, "improved": False},
        {"session_date": "2024-09-04", "session_number": 8, "therapist_notes": "No further PT until imaging obtained.", "pain_score": 9, "improved": False}
    ],
    "pharmacy_history": [
        {
            "medication": "Naproxen 500mg",
            "start_date": "2024-08-01",
            "duration_days": 30
        }
    ],
    "imaging_history": [
        {
            "type": "X-ray",
            "date": "2024-08-03",
            "findings": "Endplate irregularity L3-L4. Cannot exclude infection."
        }
    ],
    "requested_procedure": {
        "cpt_code": "72148",
        "description": "MRI lumbar spine without contrast"
    },
    "attending_physician": "Dr. James Lee"
}

# ──────────────────────────────────────────────────────────────────────
# TASK 3 – CGM step-therapy / exception  (PAT-031 … PAT-035)
# ──────────────────────────────────────────────────────────────────────

patients["PAT-031"] = {
    "patient_id": "PAT-031",
    "demographics": {
        "name": "Nina Patel",
        "dob": "1964-01-25",
        "gender": "female"
    },
    "insurance": {
        "member_id": "MBR-310031",
        "insurer": "aetna",
        "plan_id": "AETNA-GOLD-PPO",
        "active": True
    },
    "vitals": {
        "height_cm": 160,
        "weight_kg": 82,
        "bmi": 32.0,
        "bp": "144/90"
    },
    "diagnosis_codes": [
        {
            "code": "E11.65",
            "description": "Type 2 diabetes with hyperglycemia",
            "primary": True
        }
    ],
    "progress_notes": [
        {
            "date": "2024-08-10",
            "note": "Dawn Phenomenon confirmed. Fasting glucose consistently > 200 mg/dL despite optimized basal insulin. CGM needed to titrate overnight dosing."
        }
    ],
    "physical_exam": [
        {
            "date": "2024-08-10",
            "findings": "Peripheral neuropathy bilateral feet. Diminished monofilament sensation."
        }
    ],
    "lab_results": [
        {
            "test_name": "HbA1c",
            "test": "HbA1c",
            "value": 8.8,
            "unit": "%",
            "date": "2024-07-20",
            "reference_range": "< 7.0%"
        },
        {
            "test_name": "fasting_glucose",
            "test": "fasting_glucose",
            "value": 225,
            "unit": "mg/dL",
            "date": "2024-08-05",
            "reference_range": "70-100 mg/dL"
        },
        {
            "test_name": "fasting_glucose",
            "test": "fasting_glucose",
            "value": 231,
            "unit": "mg/dL",
            "date": "2024-08-06",
            "reference_range": "70-100 mg/dL"
        },
        {
            "test_name": "fasting_glucose",
            "test": "fasting_glucose",
            "value": 218,
            "unit": "mg/dL",
            "date": "2024-08-07",
            "reference_range": "70-100 mg/dL"
        }
    ],
    "pt_sessions": [],
    "pharmacy_history": [
        {
            "medication": "Insulin Glargine 38 units",
            "frequency": "1 times daily",
            "route": "subcutaneous",
            "start_date": "2024-01-01",
            "duration_days": 220
        },
        {
            "medication": "Insulin Lispro 10 units",
            "frequency": "3 times daily",
            "route": "subcutaneous",
            "start_date": "2024-01-01",
            "duration_days": 220
        },
        {
            "medication": "Metformin 1000mg",
            "frequency": "2 times daily",
            "route": "oral",
            "start_date": "2022-06-01",
            "duration_days": 800
        }
    ],
    "imaging_history": [],
    "requested_procedure": {
        "cpt_code": "E2101",
        "description": "Continuous Glucose Monitor (CGM)"
    },
    "attending_physician": "Dr. Patricia Hernandez"
}

patients["PAT-032"] = {
    "patient_id": "PAT-032",
    "demographics": {
        "name": "Sandra Osei",
        "dob": "1970-07-14",
        "gender": "female"
    },
    "insurance": {
        "member_id": "MBR-310032",
        "insurer": "cms",
        "plan_id": "MEDICARE-PART-B",
        "active": True
    },
    "vitals": {
        "height_cm": 167,
        "weight_kg": 76,
        "bmi": 27.2,
        "bp": "130/80"
    },
    "diagnosis_codes": [
        {
            "code": "E11.649",
            "description": "Type 2 DM with hypoglycemia without coma",
            "primary": True
        }
    ],
    "progress_notes": [
        {
            "date": "2024-09-05",
            "note": "Hypoglycemic unawareness. Multiple documented glucose readings < 54 mg/dL. Patient unable to recognize symptoms. CGM urgently needed."
        }
    ],
    "physical_exam": [
        {
            "date": "2024-09-05",
            "findings": "Hypoglycemic unawareness confirmed on clinical testing. Autonomic neuropathy suspected."
        }
    ],
    "lab_results": [
        {
            "test_name": "HbA1c",
            "test": "HbA1c",
            "value": 7.1,
            "unit": "%",
            "date": "2024-08-20",
            "reference_range": "< 7.0%"
        },
        {
            "test_name": "glucose_reading",
            "test": "glucose_reading",
            "value": 38,
            "unit": "mg/dL",
            "date": "2024-08-25",
            "reference_range": "70-180 mg/dL"
        },
        {
            "test_name": "glucose_reading",
            "test": "glucose_reading",
            "value": 45,
            "unit": "mg/dL",
            "date": "2024-08-18",
            "reference_range": "70-180 mg/dL"
        },
        {
            "test_name": "glucose_reading",
            "test": "glucose_reading",
            "value": 51,
            "unit": "mg/dL",
            "date": "2024-08-10",
            "reference_range": "70-180 mg/dL"
        }
    ],
    "pt_sessions": [],
    "pharmacy_history": [
        {
            "medication": "Insulin Glargine 28 units",
            "frequency": "1 times daily",
            "route": "subcutaneous",
            "start_date": "2023-09-01",
            "duration_days": 370
        },
        {
            "medication": "Insulin Aspart 8 units",
            "frequency": "3 times daily",
            "route": "subcutaneous",
            "start_date": "2023-09-01",
            "duration_days": 370
        },
        {
            "medication": "Metformin 500mg",
            "frequency": "2 times daily",
            "route": "oral",
            "start_date": "2022-01-01",
            "duration_days": 980
        }
    ],
    "imaging_history": [],
    "requested_procedure": {
        "cpt_code": "E2101",
        "description": "Continuous Glucose Monitor (CGM)"
    },
    "attending_physician": "Dr. Michael Chang"
}

patients["PAT-033"] = {
    "patient_id": "PAT-033",
    "demographics": {
        "name": "Kenji Watanabe",
        "dob": "1961-10-03",
        "gender": "male"
    },
    "insurance": {
        "member_id": "MBR-310033",
        "insurer": "cigna",
        "plan_id": "CIGNA-OPEN-ACCESS",
        "active": True
    },
    "vitals": {
        "height_cm": 174,
        "weight_kg": 90,
        "bmi": 29.7,
        "bp": "140/88"
    },
    "diagnosis_codes": [
        {
            "code": "E11.65",
            "description": "Type 2 diabetes with hyperglycemia",
            "primary": True
        }
    ],
    "progress_notes": [
        {
            "date": "2024-07-20",
            "note": "Glycemic variability despite adherent multi-dose insulin regimen. HbA1c 9.2%. CGM requested for pattern analysis and dose optimization."
        }
    ],
    "physical_exam": [
        {
            "date": "2024-07-20",
            "findings": "Obese male. Background diabetic retinopathy. Microalbuminuria on last urine."
        }
    ],
    "lab_results": [
        {
            "test_name": "HbA1c",
            "test": "HbA1c",
            "value": 9.2,
            "unit": "%",
            "date": "2024-07-10",
            "reference_range": "< 7.0%"
        },
        {
            "test_name": "HbA1c",
            "test": "HbA1c",
            "value": 8.8,
            "unit": "%",
            "date": "2024-04-05",
            "reference_range": "< 7.0%"
        },
        {
            "test_name": "fasting_glucose",
            "test": "fasting_glucose",
            "value": 198,
            "unit": "mg/dL",
            "date": "2024-07-10",
            "reference_range": "70-100 mg/dL"
        }
    ],
    "pt_sessions": [],
    "pharmacy_history": [
        {
            "medication": "Insulin Glargine 42 units",
            "frequency": "1 times daily",
            "route": "subcutaneous",
            "start_date": "2023-12-01",
            "duration_days": 230
        },
        {
            "medication": "Insulin Lispro 12 units",
            "frequency": "3 times daily",
            "route": "subcutaneous",
            "start_date": "2023-12-01",
            "duration_days": 230
        },
        {
            "medication": "Metformin 1000mg",
            "frequency": "2 times daily",
            "route": "oral",
            "start_date": "2022-03-01",
            "duration_days": 870
        }
    ],
    "imaging_history": [],
    "requested_procedure": {
        "cpt_code": "E2101",
        "description": "Continuous Glucose Monitor (CGM)"
    },
    "attending_physician": "Dr. Rachel Green"
}

patients["PAT-034"] = {
    "patient_id": "PAT-034",
    "demographics": {
        "name": "Lucille Fontaine",
        "dob": "1973-03-17",
        "gender": "female"
    },
    "insurance": {
        "member_id": "MBR-310034",
        "insurer": "aetna",
        "plan_id": "AETNA-BASIC-EPO",
        "active": True
    },
    "vitals": {
        "height_cm": 164,
        "weight_kg": 88,
        "bmi": 32.7,
        "bp": "148/92"
    },
    "diagnosis_codes": [
        {
            "code": "E11.65",
            "description": "Type 2 diabetes with hyperglycemia",
            "primary": True
        }
    ],
    "progress_notes": [
        {
            "date": "2024-09-10",
            "note": "Requests CGM. Currently on oral medications only — Metformin and Glipizide. Not on insulin. No documented hypoglycemic events."
        }
    ],
    "physical_exam": [
        {
            "date": "2024-09-10",
            "findings": "Obese female. No neuropathy. No retinopathy. Good peripheral pulses."
        }
    ],
    "lab_results": [
        {
            "test_name": "HbA1c",
            "test": "HbA1c",
            "value": 8.0,
            "unit": "%",
            "date": "2024-08-20",
            "reference_range": "< 7.0%"
        },
        {
            "test_name": "fasting_glucose",
            "test": "fasting_glucose",
            "value": 168,
            "unit": "mg/dL",
            "date": "2024-08-20",
            "reference_range": "70-100 mg/dL"
        }
    ],
    "pt_sessions": [],
    "pharmacy_history": [
        {
            "medication": "Metformin 1000mg",
            "frequency": "2 times daily",
            "route": "oral",
            "start_date": "2023-01-01",
            "duration_days": 620
        },
        {
            "medication": "Glipizide 10mg",
            "frequency": "1 times daily",
            "route": "oral",
            "start_date": "2023-06-01",
            "duration_days": 470
        }
    ],
    "imaging_history": [],
    "requested_procedure": {
        "cpt_code": "E2101",
        "description": "Continuous Glucose Monitor (CGM)"
    },
    "attending_physician": "Dr. Patricia Hernandez"
}

patients["PAT-035"] = {
    "patient_id": "PAT-035",
    "demographics": {
        "name": "Ibrahim Diallo",
        "dob": "1957-06-08",
        "gender": "male"
    },
    "insurance": {
        "member_id": "MBR-310035",
        "insurer": "cms",
        "plan_id": "MEDICARE-PART-B",
        "active": True
    },
    "vitals": {
        "height_cm": 178,
        "weight_kg": 94,
        "bmi": 29.7,
        "bp": "150/92"
    },
    "diagnosis_codes": [
        {
            "code": "E11.65",
            "description": "Type 2 diabetes with hyperglycemia",
            "primary": True
        }
    ],
    "progress_notes": [
        {
            "date": "2024-10-01",
            "note": "Dawn Phenomenon. Fasting glucose consistently > 200 mg/dL despite maximized basal insulin. CGM needed for overnight glucose profiling."
        }
    ],
    "physical_exam": [
        {
            "date": "2024-10-01",
            "findings": "Peripheral neuropathy bilateral. Charcot changes left foot. Diminished pedal pulses."
        }
    ],
    "lab_results": [
        {
            "test_name": "HbA1c",
            "test": "HbA1c",
            "value": 9.0,
            "unit": "%",
            "date": "2024-09-15",
            "reference_range": "< 7.0%"
        },
        {
            "test_name": "fasting_glucose",
            "test": "fasting_glucose",
            "value": 218,
            "unit": "mg/dL",
            "date": "2024-09-25",
            "reference_range": "70-100 mg/dL"
        },
        {
            "test_name": "fasting_glucose",
            "test": "fasting_glucose",
            "value": 224,
            "unit": "mg/dL",
            "date": "2024-09-26",
            "reference_range": "70-100 mg/dL"
        },
        {
            "test_name": "fasting_glucose",
            "test": "fasting_glucose",
            "value": 212,
            "unit": "mg/dL",
            "date": "2024-09-27",
            "reference_range": "70-100 mg/dL"
        }
    ],
    "pt_sessions": [],
    "pharmacy_history": [
        {
            "medication": "Insulin Glargine 40 units",
            "frequency": "1 times daily",
            "route": "subcutaneous",
            "start_date": "2023-10-01",
            "duration_days": 365
        },
        {
            "medication": "Insulin Lispro 12 units",
            "frequency": "3 times daily",
            "route": "subcutaneous",
            "start_date": "2023-10-01",
            "duration_days": 365
        },
        {
            "medication": "Metformin 1000mg",
            "frequency": "2 times daily",
            "route": "oral",
            "start_date": "2021-06-01",
            "duration_days": 1200
        }
    ],
    "imaging_history": [],
    "requested_procedure": {
        "cpt_code": "K0553",
        "description": "CGM receiver"
    },
    "attending_physician": "Dr. Patricia Hernandez"
}

# ──────────────────────────────────────────────────────────────────────
# TASK 4 – Peer-to-Peer Review / Denial Rebuttals  (PAT-036 … PAT-050)
# ──────────────────────────────────────────────────────────────────────

# --- PAT-036: aetna, knee MRI denied "insufficient PT", has 5 wks (>=3 req) → SUCCEED ---
patients["PAT-036"] = {
    "patient_id": "PAT-036",
    "demographics": {
        "name": "Carlos Rivera",
        "dob": "1977-02-14",
        "gender": "male"
    },
    "insurance": {
        "member_id": "MBR-310036",
        "insurer": "aetna",
        "plan_id": "AETNA-GOLD-PPO",
        "active": True
    },
    "vitals": {
        "height_cm": 178,
        "weight_kg": 88,
        "bmi": 27.8,
        "bp": "132/82"
    },
    "diagnosis_codes": [
        {
            "code": "M17.11",
            "description": "Primary osteoarthritis, right knee",
            "primary": True
        }
    ],
    "progress_notes": [
        {
            "date": "2024-05-01",
            "note": "Right knee pain worsening despite 5 weeks of PT. Functional limitation."
        },
        {
            "date": "2024-06-10",
            "note": "Prior authorization for knee MRI denied by Aetna. Preparing rebuttal with documentation of 5-week PT course."
        }
    ],
    "physical_exam": [
        {
            "date": "2024-06-10",
            "findings": "Medial joint line tenderness. Positive McMurray. ROM 0-115. Mild effusion."
        }
    ],
    "lab_results": [],
    "pt_sessions": [
        {"session_date": "2024-04-01", "session_number": 1, "therapist_notes": "Initial eval. ROM deficit.", "pain_score": 7, "improved": False},
        {"session_date": "2024-04-04", "session_number": 2, "therapist_notes": "Quad strengthening.", "pain_score": 7, "improved": False},
        {"session_date": "2024-04-08", "session_number": 3, "therapist_notes": "Step exercises.", "pain_score": 6, "improved": True},
        {"session_date": "2024-04-11", "session_number": 4, "therapist_notes": "Balance training.", "pain_score": 6, "improved": False},
        {"session_date": "2024-04-15", "session_number": 5, "therapist_notes": "Closed-chain exercises.", "pain_score": 6, "improved": False},
        {"session_date": "2024-04-18", "session_number": 6, "therapist_notes": "Functional testing.", "pain_score": 6, "improved": False},
        {"session_date": "2024-04-22", "session_number": 7, "therapist_notes": "Plateau reached.", "pain_score": 6, "improved": False},
        {"session_date": "2024-04-25", "session_number": 8, "therapist_notes": "No further gains.", "pain_score": 6, "improved": False},
        {"session_date": "2024-04-29", "session_number": 9, "therapist_notes": "Recommends imaging.", "pain_score": 6, "improved": False},
        {"session_date": "2024-05-02", "session_number": 10, "therapist_notes": "Discharged from PT. MRI advised.", "pain_score": 6, "improved": False}
    ],
    "pharmacy_history": [
        {
            "medication": "Ibuprofen 600mg",
            "start_date": "2024-03-01",
            "duration_days": 90
        }
    ],
    "imaging_history": [
        {
            "type": "X-ray",
            "date": "2024-03-15",
            "findings": "Mild medial joint space narrowing. No fracture."
        }
    ],
    "requested_procedure": {
        "cpt_code": "73721",
        "description": "MRI right knee without contrast"
    },
    "attending_physician": "Dr. Sarah Mitchell",
    "denial_letter": {
        "date": "2024-06-05",
        "insurer": "aetna",
        "reason": "Prior authorization denied: Insufficient physical therapy. Documentation does not demonstrate adequate conservative therapy trial prior to advanced imaging.",
        "denial_code": "PA-4021",
        "reviewer": "Dr. Howard Stein"
    }
}

# --- PAT-037: cigna, lumbar MRI denied "no imaging", X-ray shows disc narrowing → SUCCEED ---
patients["PAT-037"] = {
    "patient_id": "PAT-037",
    "demographics": {
        "name": "Mei-Lin Wu",
        "dob": "1968-05-22",
        "gender": "female"
    },
    "insurance": {
        "member_id": "MBR-310037",
        "insurer": "cigna",
        "plan_id": "CIGNA-OPEN-ACCESS",
        "active": True
    },
    "vitals": {
        "height_cm": 160,
        "weight_kg": 62,
        "bmi": 24.2,
        "bp": "126/78"
    },
    "diagnosis_codes": [
        {
            "code": "M54.5",
            "description": "Low back pain",
            "primary": True
        },
        {
            "code": "M51.16",
            "description": "Intervertebral disc disorders with radiculopathy, lumbar region",
            "primary": False
        }
    ],
    "progress_notes": [
        {
            "date": "2024-07-15",
            "note": "Chronic low back pain with left leg radiculopathy. X-ray reveals disc narrowing L4-L5. 7 weeks PT completed with no improvement."
        },
        {
            "date": "2024-08-20",
            "note": "Denial received from Cigna citing no prior imaging. X-ray was performed 2024-06-01 and documented in chart. Preparing rebuttal."
        }
    ],
    "physical_exam": [
        {
            "date": "2024-08-20",
            "findings": "Positive SLR left at 35 degrees. Diminished left patellar reflex. Paravertebral spasm L4-L5."
        }
    ],
    "lab_results": [],
    "pt_sessions": [
        {"session_date": "2024-06-03", "session_number": 1, "therapist_notes": "Initial eval.", "pain_score": 7, "improved": False},
        {"session_date": "2024-06-07", "session_number": 2, "therapist_notes": "Core stabilization.", "pain_score": 7, "improved": False},
        {"session_date": "2024-06-10", "session_number": 3, "therapist_notes": "McKenzie exercises.", "pain_score": 7, "improved": False},
        {"session_date": "2024-06-14", "session_number": 4, "therapist_notes": "Traction trial.", "pain_score": 6, "improved": True},
        {"session_date": "2024-06-17", "session_number": 5, "therapist_notes": "Aquatic therapy.", "pain_score": 6, "improved": False},
        {"session_date": "2024-06-21", "session_number": 6, "therapist_notes": "No further gains.", "pain_score": 7, "improved": False},
        {"session_date": "2024-06-24", "session_number": 7, "therapist_notes": "Worsening radiculopathy.", "pain_score": 7, "improved": False},
        {"session_date": "2024-06-28", "session_number": 8, "therapist_notes": "Plateau.", "pain_score": 7, "improved": False},
        {"session_date": "2024-07-01", "session_number": 9, "therapist_notes": "Declining function.", "pain_score": 7, "improved": False},
        {"session_date": "2024-07-05", "session_number": 10, "therapist_notes": "Discharged. Imaging recommended.", "pain_score": 7, "improved": False},
        {"session_date": "2024-07-08", "session_number": 11, "therapist_notes": "Maintenance only.", "pain_score": 7, "improved": False},
        {"session_date": "2024-07-12", "session_number": 12, "therapist_notes": "Final visit. Awaiting MRI.", "pain_score": 7, "improved": False}
    ],
    "pharmacy_history": [
        {
            "medication": "Naproxen 500mg",
            "start_date": "2024-05-01",
            "duration_days": 90
        },
        {
            "medication": "Gabapentin 300mg",
            "start_date": "2024-06-15",
            "duration_days": 60
        }
    ],
    "imaging_history": [
        {
            "type": "X-ray",
            "date": "2024-06-01",
            "findings": "Disc space narrowing L4-L5. Moderate osteophyte formation. Endplate sclerosis."
        }
    ],
    "requested_procedure": {
        "cpt_code": "72148",
        "description": "MRI lumbar spine without contrast"
    },
    "attending_physician": "Dr. James Lee",
    "denial_letter": {
        "date": "2024-08-15",
        "insurer": "cigna",
        "reason": "Prior authorization denied: No prior imaging studies on file. Cigna policy requires plain radiographs before advanced imaging.",
        "denial_code": "PA-4037",
        "reviewer": "Dr. Barbara Collins"
    }
}

# --- PAT-038: cms, CGM denied "oral meds only", truly no insulin → FAIL ---
patients["PAT-038"] = {
    "patient_id": "PAT-038",
    "demographics": {
        "name": "Margaret Kowalski",
        "dob": "1972-09-11",
        "gender": "female"
    },
    "insurance": {
        "member_id": "MBR-310038",
        "insurer": "cms",
        "plan_id": "MEDICARE-PART-B",
        "active": True
    },
    "vitals": {
        "height_cm": 163,
        "weight_kg": 90,
        "bmi": 33.9,
        "bp": "142/88"
    },
    "diagnosis_codes": [
        {
            "code": "E11.65",
            "description": "Type 2 diabetes with hyperglycemia",
            "primary": True
        }
    ],
    "progress_notes": [
        {
            "date": "2024-08-15",
            "note": "Patient requests CGM for glucose monitoring. Currently on oral medications only. No insulin therapy. Physician agrees CGM would be helpful for self-management."
        },
        {
            "date": "2024-09-20",
            "note": "CMS denied CGM authorization. Patient not on insulin. Denial appears clinically appropriate — step therapy not met and no exception criteria apply."
        }
    ],
    "physical_exam": [
        {
            "date": "2024-09-20",
            "findings": "Obese female. No peripheral neuropathy. Good foot exam. No retinopathy."
        }
    ],
    "lab_results": [
        {
            "test_name": "HbA1c",
            "test": "HbA1c",
            "value": 7.6,
            "unit": "%",
            "date": "2024-08-01",
            "reference_range": "< 7.0%"
        },
        {
            "test_name": "fasting_glucose",
            "test": "fasting_glucose",
            "value": 152,
            "unit": "mg/dL",
            "date": "2024-08-01",
            "reference_range": "70-100 mg/dL"
        }
    ],
    "pt_sessions": [],
    "pharmacy_history": [
        {
            "medication": "Metformin 1000mg",
            "frequency": "2 times daily",
            "route": "oral",
            "start_date": "2022-06-01",
            "duration_days": 810
        },
        {
            "medication": "Glipizide 10mg",
            "frequency": "1 times daily",
            "route": "oral",
            "start_date": "2023-03-01",
            "duration_days": 540
        }
    ],
    "imaging_history": [],
    "requested_procedure": {
        "cpt_code": "E2101",
        "description": "Continuous Glucose Monitor (CGM)"
    },
    "attending_physician": "Dr. Patricia Hernandez",
    "denial_letter": {
        "date": "2024-09-15",
        "insurer": "cms",
        "reason": "Prior authorization denied: Patient is managed with oral hypoglycemic agents only. CMS LCD L33822 requires insulin therapy (minimum 2 injections daily) for CGM coverage. No exception criteria met.",
        "denial_code": "PA-4038",
        "reviewer": "Dr. Janet Moore"
    }
}

# --- PAT-039: aetna, shoulder MRI denied "no conservative therapy", 6 wks PT + steroid → SUCCEED ---
patients["PAT-039"] = {
    "patient_id": "PAT-039",
    "demographics": {
        "name": "Terrence Washington",
        "dob": "1965-11-28",
        "gender": "male"
    },
    "insurance": {
        "member_id": "MBR-310039",
        "insurer": "aetna",
        "plan_id": "AETNA-GOLD-PPO",
        "active": True
    },
    "vitals": {
        "height_cm": 183,
        "weight_kg": 95,
        "bmi": 28.4,
        "bp": "136/84"
    },
    "diagnosis_codes": [
        {
            "code": "M75.10",
            "description": "Rotator cuff syndrome, unspecified shoulder",
            "primary": True
        }
    ],
    "progress_notes": [
        {
            "date": "2024-04-15",
            "note": "Left shoulder pain 4 months. Completed 6 weeks PT and received subacromial corticosteroid injection with transient relief only."
        },
        {
            "date": "2024-06-01",
            "note": "PA denied by Aetna citing no conservative therapy. Documented PT and injection in original submission. Preparing rebuttal."
        }
    ],
    "physical_exam": [
        {
            "date": "2024-06-01",
            "findings": "Positive Neer and Hawkins impingement. Empty can test positive. ROM: forward flexion 130, abduction 110. Supraspinatus weakness 4/5."
        }
    ],
    "lab_results": [],
    "pt_sessions": [
        {"session_date": "2024-02-26", "session_number": 1, "therapist_notes": "Initial eval. Rotator cuff protocol.", "pain_score": 7, "improved": False},
        {"session_date": "2024-03-01", "session_number": 2, "therapist_notes": "Pendulum exercises. Isometrics.", "pain_score": 7, "improved": False},
        {"session_date": "2024-03-04", "session_number": 3, "therapist_notes": "AAROM progressing.", "pain_score": 6, "improved": True},
        {"session_date": "2024-03-08", "session_number": 4, "therapist_notes": "Theraband resistance.", "pain_score": 6, "improved": False},
        {"session_date": "2024-03-11", "session_number": 5, "therapist_notes": "Scapular stabilization.", "pain_score": 6, "improved": False},
        {"session_date": "2024-03-15", "session_number": 6, "therapist_notes": "Functional activities.", "pain_score": 6, "improved": False},
        {"session_date": "2024-03-18", "session_number": 7, "therapist_notes": "Progress limited by pain.", "pain_score": 6, "improved": False},
        {"session_date": "2024-03-22", "session_number": 8, "therapist_notes": "Eccentric loading.", "pain_score": 6, "improved": False},
        {"session_date": "2024-03-25", "session_number": 9, "therapist_notes": "Plateau. Injection recommended.", "pain_score": 6, "improved": False},
        {"session_date": "2024-03-29", "session_number": 10, "therapist_notes": "Post-injection, mild relief.", "pain_score": 5, "improved": True},
        {"session_date": "2024-04-01", "session_number": 11, "therapist_notes": "Transient relief fading.", "pain_score": 6, "improved": False},
        {"session_date": "2024-04-05", "session_number": 12, "therapist_notes": "Discharged. MRI recommended.", "pain_score": 6, "improved": False}
    ],
    "pharmacy_history": [
        {
            "medication": "Meloxicam 15mg",
            "start_date": "2024-02-01",
            "duration_days": 90
        },
        {
            "medication": "Subacromial corticosteroid injection (Triamcinolone 40mg)",
            "start_date": "2024-03-27",
            "duration_days": 1
        }
    ],
    "imaging_history": [
        {
            "type": "X-ray",
            "date": "2024-02-15",
            "findings": "Subacromial spurring. No fracture. Mild AC joint arthrosis."
        }
    ],
    "requested_procedure": {
        "cpt_code": "73221",
        "description": "MRI left shoulder without contrast"
    },
    "attending_physician": "Dr. Emily Tanaka",
    "denial_letter": {
        "date": "2024-05-25",
        "insurer": "aetna",
        "reason": "Prior authorization denied: No documentation of conservative therapy including physical therapy or anti-inflammatory medications prior to advanced imaging request.",
        "denial_code": "PA-4039",
        "reviewer": "Dr. Richard Blume"
    }
}

# --- PAT-040: cigna, knee MRI denied "no red flags", TRUE LOCKING → SUCCEED ---
patients["PAT-040"] = {
    "patient_id": "PAT-040",
    "demographics": {
        "name": "Aisha Nkomo",
        "dob": "1984-08-16",
        "gender": "female"
    },
    "insurance": {
        "member_id": "MBR-310040",
        "insurer": "cigna",
        "plan_id": "CIGNA-OPEN-ACCESS",
        "active": True
    },
    "vitals": {
        "height_cm": 170,
        "weight_kg": 72,
        "bmi": 24.9,
        "bp": "118/74"
    },
    "diagnosis_codes": [
        {
            "code": "M23.211",
            "description": "Derangement anterior horn medial meniscus, right knee",
            "primary": True
        }
    ],
    "progress_notes": [
        {
            "date": "2024-06-10",
            "note": "Right knee acute injury playing soccer. Knee locked in full flexion for 30 minutes. Witnessed true mechanical locking."
        },
        {
            "date": "2024-07-15",
            "note": "Cigna denied MRI citing no red flags. Patient clearly has True Locking documented in exam and PT notes. Rebuttal needed."
        }
    ],
    "physical_exam": [
        {
            "date": "2024-06-15",
            "findings": "TRUE LOCKING observed in clinic. Knee locked at 40 degrees flexion, unable to fully extend for 15 minutes. Positive McMurray. Effusion 2+. Joint line tenderness medial.",
            "red_flags": [
                "True Locking"
            ]
        }
    ],
    "lab_results": [],
    "pt_sessions": [
        {"session_date": "2024-06-12", "session_number": 1, "therapist_notes": "Post-injury eval. Locking episode during session.", "pain_score": 8, "improved": False},
        {"session_date": "2024-06-14", "session_number": 2, "therapist_notes": "Unable to extend knee fully.", "pain_score": 8, "improved": False},
        {"session_date": "2024-06-17", "session_number": 3, "therapist_notes": "Mechanical block present. Cannot proceed.", "pain_score": 9, "improved": False},
        {"session_date": "2024-06-20", "session_number": 4, "therapist_notes": "Discharged. MRI urgently needed.", "pain_score": 8, "improved": False}
    ],
    "pharmacy_history": [
        {
            "medication": "Naproxen 500mg",
            "start_date": "2024-06-10",
            "duration_days": 21
        }
    ],
    "imaging_history": [
        {
            "type": "X-ray",
            "date": "2024-06-11",
            "findings": "No fracture. Joint effusion suspected."
        }
    ],
    "requested_procedure": {
        "cpt_code": "73721",
        "description": "MRI right knee without contrast"
    },
    "attending_physician": "Dr. Kevin Park",
    "denial_letter": {
        "date": "2024-07-10",
        "insurer": "cigna",
        "reason": "Prior authorization denied: No clinical red flags identified. Patient has not completed minimum 6 weeks of conservative therapy per Cigna musculoskeletal imaging guidelines.",
        "denial_code": "PA-4040",
        "reviewer": "Dr. William Nguyen"
    }
}

# --- PAT-041: cms, lumbar MRI denied "insufficient PT", only 2 weeks → FAIL ---
patients["PAT-041"] = {
    "patient_id": "PAT-041",
    "demographics": {
        "name": "Raymond Boucher",
        "dob": "1960-04-22",
        "gender": "male"
    },
    "insurance": {
        "member_id": "MBR-310041",
        "insurer": "cms",
        "plan_id": "MEDICARE-PART-B",
        "active": True
    },
    "vitals": {
        "height_cm": 175,
        "weight_kg": 88,
        "bmi": 28.7,
        "bp": "138/84"
    },
    "diagnosis_codes": [
        {
            "code": "M54.5",
            "description": "Low back pain",
            "primary": True
        }
    ],
    "progress_notes": [
        {
            "date": "2024-07-20",
            "note": "Low back pain 3 weeks. Started PT 2 weeks ago. Requesting lumbar MRI."
        },
        {
            "date": "2024-08-25",
            "note": "CMS denied MRI: insufficient PT. Only 2 weeks completed vs 6 required. No red flags present. Denial appears appropriate."
        }
    ],
    "physical_exam": [
        {
            "date": "2024-08-25",
            "findings": "Mild paravertebral tenderness L4-L5. Negative SLR bilaterally. Full motor strength. No neurological deficits. No red flags."
        }
    ],
    "lab_results": [],
    "pt_sessions": [
        {"session_date": "2024-07-08", "session_number": 1, "therapist_notes": "Initial eval. Core exercises.", "pain_score": 5, "improved": False},
        {"session_date": "2024-07-12", "session_number": 2, "therapist_notes": "Stretching program.", "pain_score": 5, "improved": False},
        {"session_date": "2024-07-15", "session_number": 3, "therapist_notes": "Some improvement.", "pain_score": 4, "improved": True},
        {"session_date": "2024-07-19", "session_number": 4, "therapist_notes": "Patient wants to stop for imaging.", "pain_score": 4, "improved": False}
    ],
    "pharmacy_history": [
        {
            "medication": "Ibuprofen 400mg",
            "start_date": "2024-07-01",
            "duration_days": 30
        }
    ],
    "imaging_history": [],
    "requested_procedure": {
        "cpt_code": "72148",
        "description": "MRI lumbar spine without contrast"
    },
    "attending_physician": "Dr. Alan Brooks",
    "denial_letter": {
        "date": "2024-08-20",
        "insurer": "cms",
        "reason": "Prior authorization denied: Insufficient conservative therapy. CMS LCD L33642 requires minimum 6 weeks of structured physical therapy before lumbar MRI authorization. Only 2 weeks documented.",
        "denial_code": "PA-4041",
        "reviewer": "Dr. Patricia Wells"
    }
}

# --- PAT-042: aetna, CGM denied "no exception criteria", glucose 45 (<54) → SUCCEED ---
patients["PAT-042"] = {
    "patient_id": "PAT-042",
    "demographics": {
        "name": "Sonia Ramirez",
        "dob": "1975-12-03",
        "gender": "female"
    },
    "insurance": {
        "member_id": "MBR-310042",
        "insurer": "aetna",
        "plan_id": "AETNA-GOLD-PPO",
        "active": True
    },
    "vitals": {
        "height_cm": 157,
        "weight_kg": 64,
        "bmi": 26.0,
        "bp": "124/76"
    },
    "diagnosis_codes": [
        {
            "code": "E10.641",
            "description": "Type 1 DM with hypoglycemia with coma",
            "primary": True
        }
    ],
    "progress_notes": [
        {
            "date": "2024-06-15",
            "note": "Recurrent hypoglycemic episodes. Glucose documented at 45 mg/dL. Hypoglycemic unawareness. CGM urgently needed."
        },
        {
            "date": "2024-07-20",
            "note": "Aetna denied CGM citing no exception criteria met. Glucose of 45 < 54 threshold clearly meets Aetna CPB 0515 exception. Preparing rebuttal."
        }
    ],
    "physical_exam": [
        {
            "date": "2024-07-20",
            "findings": "Hypoglycemic unawareness confirmed. Autonomic neuropathy signs present."
        }
    ],
    "lab_results": [
        {
            "test_name": "HbA1c",
            "test": "HbA1c",
            "value": 7.4,
            "unit": "%",
            "date": "2024-06-01",
            "reference_range": "< 7.0%"
        },
        {
            "test_name": "glucose_reading",
            "test": "glucose_reading",
            "value": 45,
            "unit": "mg/dL",
            "date": "2024-06-10",
            "reference_range": "70-180 mg/dL"
        },
        {
            "test_name": "glucose_reading",
            "test": "glucose_reading",
            "value": 50,
            "unit": "mg/dL",
            "date": "2024-05-28",
            "reference_range": "70-180 mg/dL"
        },
        {
            "test_name": "glucose_reading",
            "test": "glucose_reading",
            "value": 52,
            "unit": "mg/dL",
            "date": "2024-05-15",
            "reference_range": "70-180 mg/dL"
        }
    ],
    "pt_sessions": [],
    "pharmacy_history": [
        {
            "medication": "Insulin Glargine 24 units",
            "frequency": "1 times daily",
            "route": "subcutaneous",
            "start_date": "2023-06-01",
            "duration_days": 420
        },
        {
            "medication": "Insulin Aspart 6 units",
            "frequency": "3 times daily",
            "route": "subcutaneous",
            "start_date": "2023-06-01",
            "duration_days": 420
        }
    ],
    "imaging_history": [],
    "requested_procedure": {
        "cpt_code": "E2101",
        "description": "Continuous Glucose Monitor (CGM)"
    },
    "attending_physician": "Dr. Michael Chang",
    "denial_letter": {
        "date": "2024-07-15",
        "insurer": "aetna",
        "reason": "Prior authorization denied: CGM request does not meet exception criteria. No documented evidence of hypoglycemic unawareness or glucose readings below policy threshold.",
        "denial_code": "PA-4042",
        "reviewer": "Dr. Sandra Liu"
    }
}

# --- PAT-043: cigna, CGM denied "stable HbA1c", HbA1c 9.1% → SUCCEED ---
patients["PAT-043"] = {
    "patient_id": "PAT-043",
    "demographics": {
        "name": "Kwame Asante",
        "dob": "1963-03-09",
        "gender": "male"
    },
    "insurance": {
        "member_id": "MBR-310043",
        "insurer": "cigna",
        "plan_id": "CIGNA-OPEN-ACCESS",
        "active": True
    },
    "vitals": {
        "height_cm": 179,
        "weight_kg": 96,
        "bmi": 30.0,
        "bp": "146/90"
    },
    "diagnosis_codes": [
        {
            "code": "E11.65",
            "description": "Type 2 diabetes with hyperglycemia",
            "primary": True
        }
    ],
    "progress_notes": [
        {
            "date": "2024-08-01",
            "note": "Glycemic variability with HbA1c 9.1% despite multi-dose insulin. CGM needed for pattern analysis."
        },
        {
            "date": "2024-09-10",
            "note": "Cigna denied CGM claiming stable HbA1c. HbA1c of 9.1% clearly exceeds 7.0% threshold for Cigna glycemic variability exception. Rebuttal in progress."
        }
    ],
    "physical_exam": [
        {
            "date": "2024-09-10",
            "findings": "Obese male. Background diabetic retinopathy. Bilateral peripheral neuropathy."
        }
    ],
    "lab_results": [
        {
            "test_name": "HbA1c",
            "test": "HbA1c",
            "value": 9.1,
            "unit": "%",
            "date": "2024-07-20",
            "reference_range": "< 7.0%"
        },
        {
            "test_name": "HbA1c",
            "test": "HbA1c",
            "value": 8.7,
            "unit": "%",
            "date": "2024-04-10",
            "reference_range": "< 7.0%"
        },
        {
            "test_name": "fasting_glucose",
            "test": "fasting_glucose",
            "value": 192,
            "unit": "mg/dL",
            "date": "2024-07-20",
            "reference_range": "70-100 mg/dL"
        }
    ],
    "pt_sessions": [],
    "pharmacy_history": [
        {
            "medication": "Insulin Glargine 45 units",
            "frequency": "1 times daily",
            "route": "subcutaneous",
            "start_date": "2024-01-01",
            "duration_days": 250
        },
        {
            "medication": "Insulin Lispro 14 units",
            "frequency": "3 times daily",
            "route": "subcutaneous",
            "start_date": "2024-01-01",
            "duration_days": 250
        },
        {
            "medication": "Metformin 1000mg",
            "frequency": "2 times daily",
            "route": "oral",
            "start_date": "2022-01-01",
            "duration_days": 980
        }
    ],
    "imaging_history": [],
    "requested_procedure": {
        "cpt_code": "E2101",
        "description": "Continuous Glucose Monitor (CGM)"
    },
    "attending_physician": "Dr. Rachel Green",
    "denial_letter": {
        "date": "2024-09-05",
        "insurer": "cigna",
        "reason": "Prior authorization denied: Patient's HbA1c appears stable. CGM is not indicated for patients with stable glycemic control on current insulin regimen.",
        "denial_code": "PA-4043",
        "reviewer": "Dr. Thomas Park"
    }
}

# --- PAT-044: cms, knee MRI denied "incomplete workup", X-ray + 8 wks PT → SUCCEED ---
patients["PAT-044"] = {
    "patient_id": "PAT-044",
    "demographics": {
        "name": "Helen Papadopoulos",
        "dob": "1956-07-20",
        "gender": "female"
    },
    "insurance": {
        "member_id": "MBR-310044",
        "insurer": "cms",
        "plan_id": "MEDICARE-PART-B",
        "active": True
    },
    "vitals": {
        "height_cm": 160,
        "weight_kg": 76,
        "bmi": 29.7,
        "bp": "140/86"
    },
    "diagnosis_codes": [
        {
            "code": "M17.11",
            "description": "Primary osteoarthritis, right knee",
            "primary": True
        }
    ],
    "progress_notes": [
        {
            "date": "2024-05-01",
            "note": "Right knee pain limiting mobility. X-ray shows moderate OA. Completed 8 weeks PT with no improvement."
        },
        {
            "date": "2024-07-10",
            "note": "CMS denied MRI citing incomplete workup. X-ray and 8-week PT course both documented. Denial appears to be processing error. Rebuttal in progress."
        }
    ],
    "physical_exam": [
        {
            "date": "2024-07-10",
            "findings": "Bilateral varus deformity. Crepitus. ROM 5-105 right. Mild effusion. Antalgic gait."
        }
    ],
    "lab_results": [],
    "pt_sessions": [
        {"session_date": "2024-03-04", "session_number": 1, "therapist_notes": "Initial eval.", "pain_score": 7, "improved": False},
        {"session_date": "2024-03-07", "session_number": 2, "therapist_notes": "Quad sets, SLR.", "pain_score": 7, "improved": False},
        {"session_date": "2024-03-11", "session_number": 3, "therapist_notes": "Step exercises.", "pain_score": 7, "improved": False},
        {"session_date": "2024-03-14", "session_number": 4, "therapist_notes": "Stationary bike.", "pain_score": 6, "improved": True},
        {"session_date": "2024-03-18", "session_number": 5, "therapist_notes": "Balance board.", "pain_score": 6, "improved": False},
        {"session_date": "2024-03-21", "session_number": 6, "therapist_notes": "Closed-chain exercises.", "pain_score": 6, "improved": False},
        {"session_date": "2024-03-25", "session_number": 7, "therapist_notes": "Lateral step-downs.", "pain_score": 6, "improved": False},
        {"session_date": "2024-03-28", "session_number": 8, "therapist_notes": "Aquatic therapy trial.", "pain_score": 6, "improved": False},
        {"session_date": "2024-04-01", "session_number": 9, "therapist_notes": "Plateau noted.", "pain_score": 6, "improved": False},
        {"session_date": "2024-04-04", "session_number": 10, "therapist_notes": "No further gains.", "pain_score": 7, "improved": False},
        {"session_date": "2024-04-08", "session_number": 11, "therapist_notes": "Functional decline.", "pain_score": 7, "improved": False},
        {"session_date": "2024-04-11", "session_number": 12, "therapist_notes": "Recommends imaging.", "pain_score": 7, "improved": False},
        {"session_date": "2024-04-15", "session_number": 13, "therapist_notes": "Maintenance exercises.", "pain_score": 7, "improved": False},
        {"session_date": "2024-04-18", "session_number": 14, "therapist_notes": "Unable to progress.", "pain_score": 7, "improved": False},
        {"session_date": "2024-04-22", "session_number": 15, "therapist_notes": "Final session. MRI recommended.", "pain_score": 7, "improved": False},
        {"session_date": "2024-04-25", "session_number": 16, "therapist_notes": "Discharged from PT.", "pain_score": 7, "improved": False}
    ],
    "pharmacy_history": [
        {
            "medication": "Acetaminophen 1000mg",
            "start_date": "2024-02-01",
            "duration_days": 90
        },
        {
            "medication": "Diclofenac gel 1%",
            "start_date": "2024-03-01",
            "duration_days": 60
        }
    ],
    "imaging_history": [
        {
            "type": "X-ray",
            "date": "2024-02-20",
            "findings": "Moderate medial joint space narrowing. Osteophyte formation. Subchondral sclerosis."
        }
    ],
    "requested_procedure": {
        "cpt_code": "73721",
        "description": "MRI right knee without contrast"
    },
    "attending_physician": "Dr. Alan Brooks",
    "denial_letter": {
        "date": "2024-07-05",
        "insurer": "cms",
        "reason": "Prior authorization denied: Incomplete diagnostic workup. Records do not demonstrate adequate conservative therapy trial or prior imaging studies per CMS LCD L33642.",
        "denial_code": "PA-4044",
        "reviewer": "Dr. Catherine Marsh"
    }
}

# --- PAT-045: united, shoulder MRI denied, CPT 73221 NOT covered → FAIL ---
patients["PAT-045"] = {
    "patient_id": "PAT-045",
    "demographics": {
        "name": "Jamal Henderson",
        "dob": "1981-09-15",
        "gender": "male"
    },
    "insurance": {
        "member_id": "MBR-310045",
        "insurer": "united",
        "plan_id": "UHC-CHOICE-PLUS",
        "active": True
    },
    "vitals": {
        "height_cm": 188,
        "weight_kg": 98,
        "bmi": 27.7,
        "bp": "130/82"
    },
    "diagnosis_codes": [
        {
            "code": "M75.10",
            "description": "Rotator cuff syndrome, unspecified shoulder",
            "primary": True
        }
    ],
    "progress_notes": [
        {
            "date": "2024-08-01",
            "note": "Right shoulder pain 5 months. Failed conservative therapy. Requesting shoulder MRI."
        },
        {
            "date": "2024-09-10",
            "note": "United denied shoulder MRI. CPT 73221 is explicitly not covered under UHC-CHOICE-PLUS plan. This is a coverage exclusion, not a medical necessity issue. Rebuttal unlikely to succeed."
        }
    ],
    "physical_exam": [
        {
            "date": "2024-09-10",
            "findings": "Positive Neer and Hawkins. Empty can test 3/5. ROM limited. Atrophy of supraspinatus fossa."
        }
    ],
    "lab_results": [],
    "pt_sessions": [
        {"session_date": "2024-05-06", "session_number": 1, "therapist_notes": "Initial eval.", "pain_score": 7, "improved": False},
        {"session_date": "2024-05-10", "session_number": 2, "therapist_notes": "Rotator cuff protocol.", "pain_score": 7, "improved": False},
        {"session_date": "2024-05-13", "session_number": 3, "therapist_notes": "Isometric strengthening.", "pain_score": 6, "improved": True},
        {"session_date": "2024-05-17", "session_number": 4, "therapist_notes": "Theraband exercises.", "pain_score": 6, "improved": False},
        {"session_date": "2024-05-20", "session_number": 5, "therapist_notes": "Scapular stabilization.", "pain_score": 6, "improved": False},
        {"session_date": "2024-05-24", "session_number": 6, "therapist_notes": "Progress limited.", "pain_score": 6, "improved": False},
        {"session_date": "2024-05-27", "session_number": 7, "therapist_notes": "Functional activities.", "pain_score": 6, "improved": False},
        {"session_date": "2024-05-31", "session_number": 8, "therapist_notes": "No gains. MRI recommended.", "pain_score": 7, "improved": False},
        {"session_date": "2024-06-03", "session_number": 9, "therapist_notes": "Discharged from PT.", "pain_score": 7, "improved": False}
    ],
    "pharmacy_history": [
        {
            "medication": "Meloxicam 15mg",
            "start_date": "2024-04-01",
            "duration_days": 120
        },
        {
            "medication": "Subacromial corticosteroid injection",
            "start_date": "2024-06-15",
            "duration_days": 1
        }
    ],
    "imaging_history": [
        {
            "type": "X-ray",
            "date": "2024-04-20",
            "findings": "Subacromial spurring. No fracture."
        }
    ],
    "requested_procedure": {
        "cpt_code": "73221",
        "description": "MRI right shoulder without contrast"
    },
    "attending_physician": "Dr. Emily Tanaka",
    "denial_letter": {
        "date": "2024-09-05",
        "insurer": "united",
        "reason": "Prior authorization denied: CPT 73221 (MRI shoulder) is not a covered benefit under the UHC-CHOICE-PLUS plan. This service is excluded from the member's current plan tier.",
        "denial_code": "PA-4045",
        "reviewer": "Dr. Daniel Foster"
    }
}

# --- PAT-046: aetna, CGM denied, insulin pump + dawn phenomenon glucose 230 → SUCCEED ---
patients["PAT-046"] = {
    "patient_id": "PAT-046",
    "demographics": {
        "name": "Ingrid Johansson",
        "dob": "1967-04-30",
        "gender": "female"
    },
    "insurance": {
        "member_id": "MBR-310046",
        "insurer": "aetna",
        "plan_id": "AETNA-GOLD-PPO",
        "active": True
    },
    "vitals": {
        "height_cm": 168,
        "weight_kg": 70,
        "bmi": 24.8,
        "bp": "128/78"
    },
    "diagnosis_codes": [
        {
            "code": "E11.65",
            "description": "Type 2 diabetes with hyperglycemia",
            "primary": True
        }
    ],
    "progress_notes": [
        {
            "date": "2024-07-01",
            "note": "Dawn Phenomenon with fasting glucose 230 mg/dL. On insulin pump (continuous subcutaneous infusion). Meets step therapy. CGM needed for overnight profiling."
        },
        {
            "date": "2024-08-15",
            "note": "Aetna denied CGM. Patient is on insulin pump which far exceeds minimum injection requirement. Fasting glucose 230 clearly meets thresholds. Preparing comprehensive rebuttal."
        }
    ],
    "physical_exam": [
        {
            "date": "2024-08-15",
            "findings": "Peripheral neuropathy bilateral. Insulin pump site left abdomen in good condition."
        }
    ],
    "lab_results": [
        {
            "test_name": "HbA1c",
            "test": "HbA1c",
            "value": 8.6,
            "unit": "%",
            "date": "2024-06-15",
            "reference_range": "< 7.0%"
        },
        {
            "test_name": "fasting_glucose",
            "test": "fasting_glucose",
            "value": 230,
            "unit": "mg/dL",
            "date": "2024-06-28",
            "reference_range": "70-100 mg/dL"
        },
        {
            "test_name": "fasting_glucose",
            "test": "fasting_glucose",
            "value": 225,
            "unit": "mg/dL",
            "date": "2024-06-29",
            "reference_range": "70-100 mg/dL"
        },
        {
            "test_name": "fasting_glucose",
            "test": "fasting_glucose",
            "value": 238,
            "unit": "mg/dL",
            "date": "2024-06-30",
            "reference_range": "70-100 mg/dL"
        }
    ],
    "pt_sessions": [],
    "pharmacy_history": [
        {
            "medication": "Insulin pump (Omnipod) — continuous subcutaneous insulin infusion",
            "frequency": "continuous",
            "route": "subcutaneous",
            "start_date": "2023-06-01",
            "duration_days": 420
        },
        {
            "medication": "Metformin 1000mg",
            "frequency": "2 times daily",
            "route": "oral",
            "start_date": "2022-01-01",
            "duration_days": 960
        }
    ],
    "imaging_history": [],
    "requested_procedure": {
        "cpt_code": "E2101",
        "description": "Continuous Glucose Monitor (CGM)"
    },
    "attending_physician": "Dr. Patricia Hernandez",
    "denial_letter": {
        "date": "2024-08-10",
        "insurer": "aetna",
        "reason": "Prior authorization denied: CGM request lacks sufficient clinical justification. Documentation does not clearly demonstrate that current insulin regimen is inadequate for glycemic management.",
        "denial_code": "PA-4046",
        "reviewer": "Dr. Elizabeth Grant"
    }
}

# --- PAT-047: cigna, lumbar MRI denied "no neurological findings", SLR positive + foot drop → SUCCEED ---
patients["PAT-047"] = {
    "patient_id": "PAT-047",
    "demographics": {
        "name": "Nikolai Petrov",
        "dob": "1972-01-18",
        "gender": "male"
    },
    "insurance": {
        "member_id": "MBR-310047",
        "insurer": "cigna",
        "plan_id": "CIGNA-HMO-STANDARD",
        "active": True
    },
    "vitals": {
        "height_cm": 180,
        "weight_kg": 86,
        "bmi": 26.5,
        "bp": "132/82"
    },
    "diagnosis_codes": [
        {
            "code": "M54.5",
            "description": "Low back pain",
            "primary": True
        },
        {
            "code": "G54.4",
            "description": "Lumbosacral root disorder",
            "primary": False
        }
    ],
    "progress_notes": [
        {
            "date": "2024-06-01",
            "note": "Progressive left leg weakness with foot drop. Positive SLR at 20 degrees. Motor deficit L5 distribution. Urgent MRI needed."
        },
        {
            "date": "2024-07-15",
            "note": "Cigna denied lumbar MRI stating no neurological findings. Patient has documented foot drop and positive SLR — clear neurological deficit. Preparing rebuttal with detailed exam findings."
        }
    ],
    "physical_exam": [
        {
            "date": "2024-06-01",
            "findings": "Left foot drop — dorsiflexion 3/5. Positive SLR left at 20 degrees. Absent left ankle jerk. Sensory deficit L5 dermatome. Antalgic gait.",
            "red_flags": [
                "Neurological Deficit"
            ]
        }
    ],
    "lab_results": [],
    "pt_sessions": [
        {"session_date": "2024-05-06", "session_number": 1, "therapist_notes": "Initial eval. Significant radiculopathy.", "pain_score": 8, "improved": False},
        {"session_date": "2024-05-10", "session_number": 2, "therapist_notes": "Gentle ROM only.", "pain_score": 8, "improved": False},
        {"session_date": "2024-05-13", "session_number": 3, "therapist_notes": "Worsening weakness.", "pain_score": 9, "improved": False},
        {"session_date": "2024-05-17", "session_number": 4, "therapist_notes": "Foot drop developing.", "pain_score": 9, "improved": False},
        {"session_date": "2024-05-20", "session_number": 5, "therapist_notes": "Cannot perform exercises safely.", "pain_score": 9, "improved": False},
        {"session_date": "2024-05-24", "session_number": 6, "therapist_notes": "Discharged. Urgent imaging needed.", "pain_score": 9, "improved": False}
    ],
    "pharmacy_history": [
        {
            "medication": "Gabapentin 600mg",
            "start_date": "2024-05-01",
            "duration_days": 60
        },
        {
            "medication": "Methylprednisolone dose pack",
            "start_date": "2024-05-15",
            "duration_days": 6
        }
    ],
    "imaging_history": [
        {
            "type": "X-ray",
            "date": "2024-05-03",
            "findings": "Disc space narrowing L4-L5 and L5-S1. Spondylotic changes."
        }
    ],
    "requested_procedure": {
        "cpt_code": "72148",
        "description": "MRI lumbar spine without contrast"
    },
    "attending_physician": "Dr. James Lee",
    "denial_letter": {
        "date": "2024-07-10",
        "insurer": "cigna",
        "reason": "Prior authorization denied: No significant neurological findings documented. Patient has not completed required conservative therapy course per Cigna lumbar MRI guidelines.",
        "denial_code": "PA-4047",
        "reviewer": "Dr. Robert Chang"
    }
}

# --- PAT-048: cms, CGM denied, 1 injection/day (needs ≥2) → FAIL ---
patients["PAT-048"] = {
    "patient_id": "PAT-048",
    "demographics": {
        "name": "Dorothy Abrams",
        "dob": "1959-06-14",
        "gender": "female"
    },
    "insurance": {
        "member_id": "MBR-310048",
        "insurer": "cms",
        "plan_id": "MEDICARE-PART-B",
        "active": True
    },
    "vitals": {
        "height_cm": 162,
        "weight_kg": 82,
        "bmi": 31.2,
        "bp": "138/84"
    },
    "diagnosis_codes": [
        {
            "code": "E11.65",
            "description": "Type 2 diabetes with hyperglycemia",
            "primary": True
        }
    ],
    "progress_notes": [
        {
            "date": "2024-09-01",
            "note": "Patient on once-daily basal insulin only. Requests CGM for glucose monitoring. No documented hypoglycemic episodes."
        },
        {
            "date": "2024-10-05",
            "note": "CMS denied CGM: requires minimum 2 daily insulin injections. Patient on only 1 injection/day. No exception criteria met. Denial appears appropriate."
        }
    ],
    "physical_exam": [
        {
            "date": "2024-10-05",
            "findings": "Mild peripheral neuropathy. Otherwise unremarkable diabetic exam."
        }
    ],
    "lab_results": [
        {
            "test_name": "HbA1c",
            "test": "HbA1c",
            "value": 7.8,
            "unit": "%",
            "date": "2024-08-15",
            "reference_range": "< 7.0%"
        },
        {
            "test_name": "fasting_glucose",
            "test": "fasting_glucose",
            "value": 162,
            "unit": "mg/dL",
            "date": "2024-08-15",
            "reference_range": "70-100 mg/dL"
        }
    ],
    "pt_sessions": [],
    "pharmacy_history": [
        {
            "medication": "Insulin Glargine 20 units",
            "frequency": "1 times daily",
            "route": "subcutaneous",
            "start_date": "2024-03-01",
            "duration_days": 210
        },
        {
            "medication": "Metformin 1000mg",
            "frequency": "2 times daily",
            "route": "oral",
            "start_date": "2022-06-01",
            "duration_days": 830
        }
    ],
    "imaging_history": [],
    "requested_procedure": {
        "cpt_code": "E2101",
        "description": "Continuous Glucose Monitor (CGM)"
    },
    "attending_physician": "Dr. Patricia Hernandez",
    "denial_letter": {
        "date": "2024-10-01",
        "insurer": "cms",
        "reason": "Prior authorization denied: Patient does not meet step therapy requirements for CGM. CMS requires minimum 2 insulin injections per day. Patient documentation shows 1 injection daily (basal insulin only). No exception criteria met.",
        "denial_code": "PA-4048",
        "reviewer": "Dr. Janet Moore"
    }
}

# --- PAT-049: aetna, knee MRI denied, 4 wks PT (≥3 req) + positive McMurray → SUCCEED ---
patients["PAT-049"] = {
    "patient_id": "PAT-049",
    "demographics": {
        "name": "Amara Okafor",
        "dob": "1986-10-27",
        "gender": "female"
    },
    "insurance": {
        "member_id": "MBR-310049",
        "insurer": "aetna",
        "plan_id": "AETNA-BASIC-EPO",
        "active": True
    },
    "vitals": {
        "height_cm": 166,
        "weight_kg": 70,
        "bmi": 25.4,
        "bp": "120/74"
    },
    "diagnosis_codes": [
        {
            "code": "M23.211",
            "description": "Derangement anterior horn medial meniscus, right knee",
            "primary": True
        },
        {
            "code": "M17.11",
            "description": "Primary osteoarthritis, right knee",
            "primary": False
        }
    ],
    "progress_notes": [
        {
            "date": "2024-06-15",
            "note": "Right knee pain with clicking and catching. 4 weeks PT completed. Positive McMurray test. Suspected meniscal tear."
        },
        {
            "date": "2024-07-20",
            "note": "Aetna denied knee MRI. Patient has completed 4 weeks PT (Aetna requires 3 weeks minimum). Positive McMurray with clinical suspicion of meniscal tear. Preparing rebuttal."
        }
    ],
    "physical_exam": [
        {
            "date": "2024-07-20",
            "findings": "Positive McMurray test with audible click. Joint line tenderness medial. ROM 0-125. Mild effusion. No locking."
        }
    ],
    "lab_results": [],
    "pt_sessions": [
        {"session_date": "2024-05-13", "session_number": 1, "therapist_notes": "Initial eval. Meniscal protocol.", "pain_score": 6, "improved": False},
        {"session_date": "2024-05-16", "session_number": 2, "therapist_notes": "Quad and hamstring strengthening.", "pain_score": 6, "improved": False},
        {"session_date": "2024-05-20", "session_number": 3, "therapist_notes": "Step exercises.", "pain_score": 6, "improved": False},
        {"session_date": "2024-05-23", "session_number": 4, "therapist_notes": "Catching sensation persists.", "pain_score": 6, "improved": False},
        {"session_date": "2024-05-27", "session_number": 5, "therapist_notes": "Balance training.", "pain_score": 5, "improved": True},
        {"session_date": "2024-05-30", "session_number": 6, "therapist_notes": "Functional testing.", "pain_score": 5, "improved": False},
        {"session_date": "2024-06-03", "session_number": 7, "therapist_notes": "No further gains.", "pain_score": 6, "improved": False},
        {"session_date": "2024-06-06", "session_number": 8, "therapist_notes": "Discharged. MRI recommended.", "pain_score": 6, "improved": False}
    ],
    "pharmacy_history": [
        {
            "medication": "Ibuprofen 600mg",
            "start_date": "2024-05-01",
            "duration_days": 45
        }
    ],
    "imaging_history": [
        {
            "type": "X-ray",
            "date": "2024-05-05",
            "findings": "Mild joint space narrowing. No fracture. No loose bodies."
        }
    ],
    "requested_procedure": {
        "cpt_code": "73721",
        "description": "MRI right knee without contrast"
    },
    "attending_physician": "Dr. Sarah Mitchell",
    "denial_letter": {
        "date": "2024-07-15",
        "insurer": "aetna",
        "reason": "Prior authorization denied: Insufficient documentation of conservative therapy failure. Clinical notes do not adequately demonstrate functional limitation requiring advanced imaging.",
        "denial_code": "PA-4049",
        "reviewer": "Dr. Howard Stein"
    }
}

# --- PAT-050: cigna, knee MRI denied "imaging not indicated", fracture on X-ray → SUCCEED ---
patients["PAT-050"] = {
    "patient_id": "PAT-050",
    "demographics": {
        "name": "Ravi Krishnamurthy",
        "dob": "1978-03-05",
        "gender": "male"
    },
    "insurance": {
        "member_id": "MBR-310050",
        "insurer": "cigna",
        "plan_id": "CIGNA-HMO-STANDARD",
        "active": True
    },
    "vitals": {
        "height_cm": 175,
        "weight_kg": 80,
        "bmi": 26.1,
        "bp": "126/78"
    },
    "diagnosis_codes": [
        {
            "code": "S82.001A",
            "description": "Unspecified fracture of right patella, initial encounter",
            "primary": True
        },
        {
            "code": "M17.11",
            "description": "Primary osteoarthritis, right knee",
            "primary": False
        }
    ],
    "progress_notes": [
        {
            "date": "2024-08-10",
            "note": "Right knee injury after fall. X-ray shows non-displaced patellar fracture. MRI needed to assess soft tissue injury and occult fracture extent."
        },
        {
            "date": "2024-09-15",
            "note": "Cigna denied MRI claiming imaging is not indicated. X-ray clearly demonstrates a fracture requiring MRI for complete evaluation. Preparing urgent rebuttal."
        }
    ],
    "physical_exam": [
        {
            "date": "2024-08-10",
            "findings": "Significant swelling right knee. Unable to perform SLR against gravity. Patellar tenderness. Effusion 3+. Limited ROM 20-60 due to pain."
        }
    ],
    "lab_results": [],
    "pt_sessions": [],
    "pharmacy_history": [
        {
            "medication": "Acetaminophen 1000mg",
            "start_date": "2024-08-10",
            "duration_days": 14
        },
        {
            "medication": "Tramadol 50mg",
            "start_date": "2024-08-10",
            "duration_days": 7
        }
    ],
    "imaging_history": [
        {
            "type": "X-ray",
            "date": "2024-08-10",
            "findings": "Non-displaced transverse fracture of the right patella. Moderate joint effusion. Cannot exclude additional ligamentous or meniscal injury on plain films."
        }
    ],
    "requested_procedure": {
        "cpt_code": "73721",
        "description": "MRI right knee without contrast"
    },
    "attending_physician": "Dr. Kevin Park",
    "denial_letter": {
        "date": "2024-09-10",
        "insurer": "cigna",
        "reason": "Prior authorization denied: Advanced imaging not indicated at this time. Conservative management with follow-up radiographs recommended per Cigna musculoskeletal imaging guidelines.",
        "denial_code": "PA-4050",
        "reviewer": "Dr. William Nguyen"
    }
}

# ──────────────────────────────────────────────────────────────────────
# Write all patient files
# ──────────────────────────────────────────────────────────────────────

os.makedirs(OUT, exist_ok=True)

print(f"Writing {len(patients)} patient files to {OUT}/")
for pid, data in patients.items():
    with open(os.path.join(OUT, f"{pid}.json"), "w") as f:
        json.dump(data, f, indent=2)
    print(f"  {pid}.json")

print(f"Done: {len(patients)} patients written.")

import json
import os
import uuid
from datetime import datetime

from models import (
    PTPAState,
    PatientRecord,
    EpisodeProgress,
    EpisodeStatus,
    TaskID,
)

from tasks import get_max_steps, get_task
from environment.task1_verification import handle_task1_action
from environment.task2_mri_necessity import handle_task2_action


DATA_PATH = "data/prs"
IPD_PATH = "data/ipd"


class EnvironmentEngine:

    def __init__(self):
        self.prs = self._load_json_folder(DATA_PATH, key="patient_id")
        self.ipd = self._load_json_folder(IPD_PATH, key="insurer")
        self.state = None

    # -------------------------------
    # SAFE JSON LOADER (FIXES EVERYTHING)
    # -------------------------------
    def _load_json_folder(self, path, key):
        data_store = {}

        if not os.path.exists(path):
            return data_store

        for file in os.listdir(path):
            if not file.endswith(".json"):
                continue

            file_path = os.path.join(path, file)

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()

                    # ✅ Skip truly empty or whitespace-only files
                    if not content:
                        print(f"⚠️ Skipping empty/whitespace file: {file}")
                        continue

                    data = json.loads(content)

                    if key not in data:
                        print(f"⚠️ Skipping invalid file (missing {key}): {file}")
                        continue

                    data_store[data[key]] = data

            except Exception as e:
                print(f"❌ Skipping broken file: {file} → {e}")

        return data_store
    
    # -------------------------------
    # RESET
    # -------------------------------

    def reset(self, task_id: TaskID, patient_id: str):
        patient_data = self.prs[patient_id]

        task_info = get_task(task_id)

        patient = PatientRecord(
            patient_id=patient_id,
            name=patient_data["demographics"]["name"],
            dob=patient_data["demographics"]["dob"],
            member_id=patient_data["insurance"]["member_id"],
            insurer=patient_data["insurance"]["insurer"],
            plan_id=patient_data["insurance"]["plan_id"],
            primary_icd10=patient_data["diagnosis_codes"][0]["code"],
            requested_cpt=patient_data["requested_procedure"]["cpt_code"],
            attending_physician="Dr. Default"
        )

        self.state = PTPAState(
            episode_id=str(uuid.uuid4()),
            task_id=task_id,
            difficulty=task_info.difficulty,
            status=EpisodeStatus.ACTIVE,
            step_count=0,
            max_steps=get_max_steps(task_id),
            patient=patient,
            progress=EpisodeProgress(),
            seed=42,
            created_at=datetime.utcnow().isoformat()
        )

        return self.state

    # -------------------------------
    # STEP
    # -------------------------------

    def step(self, action):
        self.state.step_count += 1

        if self.state.task_id == TaskID.VERIFICATION:
            obs = handle_task1_action(action, self.state, self.prs, self.ipd)

        elif self.state.task_id == TaskID.MRI_NECESSITY:
            obs = handle_task2_action(action, self.state, self.prs, self.ipd)

        else:
            raise NotImplementedError(f"Task {self.state.task_id} not implemented")

        return obs

    # -------------------------------
    # STATE
    # -------------------------------

    def get_state(self):
        return self.state
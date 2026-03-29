# Patient Triage & Prior Authorization (PTPA) OpenEnv

A high-fidelity healthcare environment for training and evaluating AI agents on real-world prior authorization (PA) workflows. Agents must navigate insurance eligibility verification, medical necessity assessment for advanced imaging, and complex exception appeal construction for diabetic management devices.

Built on the [OpenEnv specification](https://github.com/meta-pytorch/OpenEnv).

---

## Quick Start

### Docker (recommended)

```bash
docker build -t ptpa-env .
docker run -p 8000:8000 -e OPENAI_API_KEY=$OPENAI_API_KEY ptpa-env
```

### Local Development

```bash
pip install -e .
uvicorn server.app:app --host 0.0.0.0 --port 8000
```

The server will be available at `http://localhost:8000`.

### Verify

```bash
curl http://localhost:8000/health
curl http://localhost:8000/tasks
curl http://localhost:8000/validate
```

---

## Tasks

| Task | Difficulty | Max Steps | Baseline Score | Description |
|------|-----------|-----------|---------------|-------------|
| `task1_verification` | Easy | 10 | 0.98 | Insurance eligibility check + CPT coverage lookup |
| `task2_mri_necessity` | Medium | 20 | 0.42 | MRI medical necessity review with PT duration logic and red flag bypass |
| `task3_cgm_appeal` | Hard | 25 | 0.15 | CGM exception appeal with lab threshold identification and LMN generation |

### Task 1: Insurance Verification & Eligibility (Easy)

The agent verifies whether a patient's insurance is active and whether the requested procedure (CPT code) is covered under their plan. Graded on:

- **Eligibility Status (40%)** — Correctly identify active/inactive policy
- **Procedure Coverage (40%)** — Correctly identify CPT coverage
- **Policy Rationale (20%)** — Cite the correct policy section

### Task 2: Medical Necessity for Advanced Imaging (Medium)

The agent determines if a patient meets conservative therapy requirements for MRI approval. Must extract PT session records, calculate duration, check for red flags that bypass PT requirements, and compare against insurer-specific thresholds (Aetna: 3 weeks, Cigna/CMS: 6 weeks). Graded on:

- **Evidence Extraction (35%)** — Find PT session dates and records
- **Policy Duration Logic (30%)** — Correctly apply duration threshold
- **Red Flag Recognition (20%)** — Identify or rule out clinical urgency bypasses
- **Final Decision Accuracy (15%)** — Correct approve/deny/appeal

### Task 3: Medical Exception Appeal — CGM (Hard)

The agent handles an appeal after CGM denial. Must check step therapy compliance, extract glucose/HbA1c values, identify qualifying exception criteria (Dawn Phenomenon > 200 mg/dL, Hypoglycemic Unawareness < 54 mg/dL, Glycemic Variability HbA1c > 7.0%), generate a Letter of Medical Necessity, and submit an appeal. Graded on:

- **Metric Identification (40%)** — Find the specific threshold value in lab data
- **Rationale Mapping (30%)** — Link metric to the correct policy exception clause
- **Appeal Letter Quality (30%)** — LMN with ICD-10 codes, lab values, professional format

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/reset` | Start a new episode for a task |
| `POST` | `/step` | Execute one agent action |
| `GET` | `/state?episode_id=...` | Get current episode state |
| `GET` | `/tasks` | List all tasks with action schemas |
| `POST` | `/grader` | Grade a completed episode |
| `POST` | `/baseline` | Run baseline gpt-4o-mini agent on all tasks |
| `GET` | `/health` | Liveness check |
| `GET` | `/validate` | Validate environment integrity |
| `GET` | `/info` | Environment metadata |
| `WS` | `/ws` | WebSocket for real-time interaction |

### Example: Run an Episode

```bash
# 1. Reset
curl -X POST http://localhost:8000/reset \
  -H "Content-Type: application/json" \
  -d '{"task_id": "task1_verification", "seed": 42}'

# 2. Step (use episode_id from reset response)
curl -X POST http://localhost:8000/step \
  -H "Content-Type: application/json" \
  -d '{
    "episode_id": "YOUR_EPISODE_ID",
    "action": {
      "action_type": "check_eligibility",
      "patient_id": "PAT-001",
      "task_id": "task1_verification",
      "parameters": {"member_id": "MBR-881234", "insurer": "aetna"}
    }
  }'

# 3. Grade
curl -X POST http://localhost:8000/grader \
  -H "Content-Type: application/json" \
  -d '{"episode_id": "YOUR_EPISODE_ID"}'
```

---

## Action Space

11 action types across all tasks:

| Action Type | Tasks | Description |
|-------------|-------|-------------|
| `query_patient_record` | All | Retrieve a section of the patient's EHR |
| `query_policy_database` | All | Retrieve insurance policy rules |
| `submit_decision` | All | Submit final approve/deny/appeal decision |
| `check_eligibility` | Task 1 | Verify member ID and plan status |
| `check_cpt_coverage` | Task 1 | Look up CPT code coverage |
| `extract_pt_sessions` | Task 2 | Pull physical therapy session records |
| `check_red_flags` | Task 2 | Scan for clinical urgency indicators |
| `compare_policy_duration` | Task 2 | Compare PT weeks vs policy requirement |
| `extract_lab_values` | Task 3 | Retrieve HbA1c, glucose readings |
| `check_step_therapy` | Task 3 | Verify insulin injection requirements |
| `generate_appeal_letter` | Task 3 | Draft Letter of Medical Necessity |

---

## Observation Space

Every `step()` returns a `PTPAObservation`:

| Field | Type | Description |
|-------|------|-------------|
| `result` | str | Human-readable summary of action result |
| `success` | bool | Whether the action completed |
| `found_evidence` | list | Extracted clinical evidence items |
| `red_flags` | list | Clinical urgency indicators |
| `pt_sessions` | list | Physical therapy session records |
| `policy_rule` | object | Retrieved insurance policy rule |
| `reward` | float | Partial progress reward (-0.5 to +0.4) |
| `reward_reason` | str | Explanation of reward signal |
| `step_count` | int | Steps taken so far |
| `done` | bool | Episode termination flag |

---

## Reward Function

Dense reward signals that shape agent behavior:

| Signal | Value | Trigger |
|--------|-------|---------|
| Discovery | +0.10 | Retrieved a relevant policy section |
| Evidence | +0.20 | Extracted a critical lab value or PT note |
| Logic | +0.30 | Identified a red flag or exception criteria |
| Success | +0.40 | Submitted the correct determination |
| Loop Penalty | -0.10 | Repeated same query without new results |
| Destructive Penalty | -0.50 | Unauthorized access or false information |

---

## Baseline Scores

Using gpt-4o-mini (temperature=0, seed=42):

| Task | Score | Analysis |
|------|-------|----------|
| Verification (Easy) | 0.98 | Rare errors in member ID parsing |
| MRI Necessity (Medium) | 0.42 | Difficulty correlating PT dates with duration rules |
| CGM Appeal (Hard) | 0.15 | Frequent failure to find the 200 mg/dL exception |
| **Overall Mean** | **0.52** | |

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | For baseline agent and Task 3 LLM-as-judge grader |
| `PTPA_LOG_LEVEL` | No | Logging level (default: INFO) |
| `PTPA_MAX_SESSIONS` | No | Max concurrent sessions (default: 50) |
| `PTPA_SEED_OVERRIDE` | No | Override seed for all episodes |

---

## Project Structure

```
healthcare_prior_auth/
├── openenv.yaml                <- Environment manifest
├── Dockerfile                  <- Container build
├── pyproject.toml              <- Python dependencies
├── README.md                   <- This file
├── models.py                   <- Shared Pydantic models (interface contract)
├── tasks.py                    <- Task registry, grader specs, answer keys
├── server/
│   ├── app.py                  <- FastAPI app + all endpoints
│   ├── session.py              <- In-memory session management
│   └── websocket.py            <- WebSocket handler
├── environment/
│   ├── engine.py               <- step()/reset()/state()/grade() logic
│   └── rewards.py              <- Reward computation
├── data/
│   └── prs/                    <- Patient Record System fixtures
├── baseline/
│   └── baseline.py             <- gpt-4o-mini baseline inference
```

---

## License

MIT

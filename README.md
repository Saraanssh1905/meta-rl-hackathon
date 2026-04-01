# Incident Triage & Escalation Environment (OpenEnv)

## Overview

Modern production systems fail in complex, cascading ways.

When incidents occur, on-call engineers must: - Assess severity
quickly - Identify root causes - Route issues to correct teams - Take
recovery actions

This environment simulates that workflow as a reinforcement learning
problem.

------------------------------------------------------------------------

## Repository Structure

    meta-rl-hackathon/
    ├── server/
    │   ├── app.py
    │   ├── environment.py
    │   ├── scenarios.py
    │   └── requirements.txt
    ├── models.py
    ├── client.py
    ├── inference.py
    ├── Dockerfile
    ├── openenv.yaml
    └── README.md

------------------------------------------------------------------------

## Environment Design

### Episode Flow

reset() → observation\
step(action) → reward + feedback\
done = True( 1 step per episode)

------------------------------------------------------------------------

## Action Space

<img width="886" height="472" alt="image" src="https://github.com/user-attachments/assets/f4de333b-94f7-4e37-a7fa-25ac2758557e" />


  Field              Type              Required      Description
  ------------------ ----------------- ------------- --------------------------
  severity           str               Yes           P1 / P2 / P3 / P4
  root_cause         str               Medium/Hard   Snake_case issue
  assigned_team      str               Medium/Hard   backend / database / etc
  root_cause_alert   str               Hard          A / B / C
  priority_order     List\[str\]       Hard          Order of resolution
  actions            Dict\[str,str\]   Hard          Fix per alert

------------------------------------------------------------------------

## Observation Space

<img width="830" height="764" alt="image" src="https://github.com/user-attachments/assets/8a2a3e80-9497-4514-b338-028adc319930" />


  Field             Type          Description
  ----------------- ------------- -------------------------
  alerts            List          Alert objects
  logs              List\[str\]   System logs
  metrics           Dict          System metrics
  task_difficulty   str           easy / medium / hard
  message           str           Instructions / feedback
  available_teams   List\[str\]   Valid teams

------------------------------------------------------------------------

## Tasks

### Task 1 --- Severity Classification (Easy)

Single alert → classify severity. No logs or metrics provided — the agent must reason purely from alert text.
6 scenarios covering all severity levels:

<img width="873" height="411" alt="image" src="https://github.com/user-attachments/assets/043884b0-91f3-42fa-a17c-a6c9ef559d1f" />

Results:

<img width="636" height="214" alt="image" src="https://github.com/user-attachments/assets/270e119e-25cc-46b0-867a-efda5b5f9237" />

Grading:

<img width="860" height="301" alt="image" src="https://github.com/user-attachments/assets/a897b747-1435-47bd-8377-7718d7a61199" />



------------------------------------------------------------------------

### Task 2 --- Diagnose & Assign (Medium)

Alert + logs + metrics → severity + root cause + team

3 scenarios:
<img width="883" height="240" alt="image" src="https://github.com/user-attachments/assets/1562984a-69ff-4960-ade3-81e6b5a865be" />

Results:


<img width="676" height="399" alt="image" src="https://github.com/user-attachments/assets/aba25dfe-9787-4b63-a13b-61dc7d810fbc" />

Grading:

<img width="884" height="256" alt="image" src="https://github.com/user-attachments/assets/2a695923-bdcc-426a-aa12-1537664477fb" />


------------------------------------------------------------------------

### Task 3 --- Cascading Failure (Hard)

Multiple alerts +logs+metrics → full triage decision.

2 scenarios:

<img width="868" height="253" alt="image" src="https://github.com/user-attachments/assets/48afbb64-3dd6-4bdf-85ac-5a5470bfde99" />

Root cause: B (Redis failed first). Correct: root cause B, P1, priority [B, A, C], increase Redis memory — downstream services recover automatically.

<img width="873" height="255" alt="image" src="https://github.com/user-attachments/assets/db2d8dc4-4bd9-40d3-acb5-970a2d78046a" />

Root cause: C (deployment introduced a segfaulting module at 14:55). Correct: root cause C, P1, priority [C, B, A], rollback v2.4.1 — LB and CDN recover automatically.

Results:

<img width="920" height="856" alt="image" src="https://github.com/user-attachments/assets/e1d94aa3-c6ad-4331-9d13-23b8f0b387d3" />

Grading: 

<img width="881" height="358" alt="image" src="https://github.com/user-attachments/assets/db516ce4-a1fe-402d-b748-131f162f1bbf" />





------------------------------------------------------------------------

## Reward Function

The environment uses a **dense, structured reward function (0.0 → 1.0)** that provides
both **positive reinforcement for correct reasoning** and **implicit negative marking for mistakes**.

Rather than binary success/failure, the agent is evaluated across multiple dimensions,
ensuring meaningful feedback throughout the trajectory.

---

### 🎯 Reward Structure by Task

#### 🟢 Easy Task (Severity Classification)

Reward is based on distance from correct severity:

| Condition | Reward |
|----------|--------|
| Exact match | 1.0 |
| Off by 1 level | 0.7 |
| Off by 2 levels | 0.4 |
| Completely wrong | 0.0 |

---

#### 🟡 Medium Task (Diagnosis & Assignment)

Total reward = weighted sum:

R = 0.4·Severity + 0.35·RootCause + 0.25·Team

- Severity → exact or partial match
- Root Cause → exact / partial string match
- Team → exact match only

---

#### 🔴 Hard Task (Cascading Failure Triage)

Total reward:

R = 0.30·RootCauseAlert  
  + 0.20·Severity  
  + 0.25·PriorityOrder  
  + 0.10·Team  
  + 0.15·Actions  

- Priority → full or partial (first correct)
- Actions → keyword overlap scoring

---

## ⚠️ Negative Marking (Penalty Design)

The environment incorporates **implicit negative marking** by reducing reward
for incorrect, incomplete, or suboptimal decisions.

### Key Penalty Mechanisms

#### ❌ Incorrect Decisions
- Wrong severity → sharp drop (up to 0.0)
- Wrong root cause / team → zero contribution for that component

#### ❌ Missing Information
- Not providing required fields (root cause, actions, etc.)
  → treated as **0 contribution**
- Encourages **complete outputs**, not partial guessing

#### ❌ Poor Reasoning / Ordering
- Incorrect priority order in hard tasks:
  - Full mismatch → 0
  - Only first correct → partial (0.10)
- Prevents random ordering strategies

#### ❌ Low-Quality Actions
- Actions are evaluated via **semantic keyword overlap**
- Irrelevant or vague actions → low score contribution

---

## 🔬 Code-Level Mapping

The reward logic is directly implemented in:

- `environment.py::_grade_easy()`
- `environment.py::_grade_medium()`
- `environment.py::_grade_hard()`

Each function:
- Computes **component-wise scores**
- Aggregates them into a final reward ∈ [0.0, 1.0]
- Returns **detailed feedback** explaining correctness

---

## 🚀 Why This Reward Design is Strong

- ✅ **Dense reward signal** → guides learning at every step  
- ✅ **Partial credit system** → rewards progress, not just success  
- ✅ **Implicit penalties** → discourages wrong or incomplete outputs  
- ✅ **Multi-dimensional evaluation** → tests reasoning, not guessing  
- ✅ **Deterministic grading** → reproducible and fair  

This ensures that agents must demonstrate:
- Accurate classification  
- Correct root cause reasoning  
- Proper prioritization  
- Actionable decision-making  

rather than relying on shortcuts or random guesses.

------------------------------------------------------------------------

## Setup

### Install

pip install openenv-core fastapi uvicorn pydantic openai

### Run locally

uvicorn server.app:app --reload

Open: http://127.0.0.1:8000/docs

<img width="1167" height="916" alt="image" src="https://github.com/user-attachments/assets/3a68cd67-334c-44d9-928b-02fdf4fe5b3c" />


------------------------------------------------------------------------

### Docker

docker build -t incident-triage\
docker run -p 7860:7860 incident-triage

------------------------------------------------------------------------

### Deploy

openenv push --repo-id `<your-username>`{=html}/incident-triage

------------------------------------------------------------------------

## Baseline Scores

  Difficulty   Score
  ------------ -------
  Easy         0.92
  Medium       1.00
  Hard         0.61

------------------------------------------------------------------------

=======
## Inference

export HF_TOKEN=your_token\
python inference.py --base-url http://localhost:8000

------------------------------------------------------------------------

## Live Demo

https://huggingface.co/spaces/Saraanssh1905/incident-triage

<img width="676" height="399" alt="image" src="https://github.com/user-attachments/assets/b71011a1-82ad-4f49-99fc-2cae7360a1d5" />

<img width="676" height="399" alt="image" src="https://github.com/user-attachments/assets/a63307ed-62b1-43eb-a81c-6823ca88489f" />



------------------------------------------------------------------------

## Team Neural Nexus

-   Omkar Iyer - Evaluation, Deployment\
-   Saraanssh Mehra - Environment Design, Backend


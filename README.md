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

### Repository Structure Screenshot

<img width="417" height="809" alt="image" src="https://github.com/user-attachments/assets/b01ee7bb-5eef-48df-9aa6-ecc983c2cb87" />



------------------------------------------------------------------------

## Environment Design

### Episode Flow

reset() → observation\
step(action) → reward + feedback\
done = True

------------------------------------------------------------------------

## Action Space

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

Single alert → classify severity

<img width="636" height="214" alt="image" src="https://github.com/user-attachments/assets/270e119e-25cc-46b0-867a-efda5b5f9237" />


------------------------------------------------------------------------

### Task 2 --- Diagnose & Assign (Medium)

Alert + logs + metrics → severity + root cause + team

<img width="676" height="399" alt="image" src="https://github.com/user-attachments/assets/aba25dfe-9787-4b63-a13b-61dc7d810fbc" />


------------------------------------------------------------------------

### Task 3 --- Cascading Failure (Hard)

Multiple alerts → full triage

<img width="920" height="856" alt="image" src="https://github.com/user-attachments/assets/e1d94aa3-c6ad-4331-9d13-23b8f0b387d3" />




------------------------------------------------------------------------

## Reward Function

Range: 0.0 to 1.0\
Partial credit across all components.

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


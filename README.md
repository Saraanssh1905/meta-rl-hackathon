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

\[ADD REPO STRUCTURE SCREENSHOT HERE\]

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

\[ADD EASY TASK SCREENSHOT\]

------------------------------------------------------------------------

### Task 2 --- Diagnose & Assign (Medium)

Alert + logs + metrics → severity + root cause + team

\[ADD MEDIUM TASK SCREENSHOT\]

------------------------------------------------------------------------

### Task 3 --- Cascading Failure (Hard)

Multiple alerts → full triage

\[ADD HARD TASK SCREENSHOT\]

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

\[ADD FASTAPI SCREENSHOT\]

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

------------------------------------------------------------------------

## Team Neural Nexus

-   Omkar Iyer - Evaluation, Deployment\
-   Saraanssh Mehra - Environment Design, Backend


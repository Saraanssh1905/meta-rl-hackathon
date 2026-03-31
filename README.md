---
title: incident-triage
emoji: 🚨
colorFrom: red
colorTo: blue
sdk: docker
pinned: false
---

# Incident Triage & Escalation Environment

## Description & Motivation

Incident triage is the process of rapidly assessing, classifying, and routing system alerts during a production outage or degradation event. When something goes wrong in a live system — a payment service going down, a database hitting connection limits, or a cascading failure across multiple services — an on-call engineer must quickly determine how severe the situation is, what caused it, and which team should fix it. Speed and accuracy both matter: a misclassified P1 incident can mean minutes of additional downtime and significant revenue loss.

This environment is valuable for AI agent training because incident triage requires genuine multi-step reasoning under pressure. The agent must read noisy, real-world-style alert data, correlate log lines with metrics, identify root causes that are not explicitly stated, and produce structured decisions with partial information. Unlike toy tasks, there is no single obvious signal — the agent must weigh evidence across multiple sources and apply domain knowledge about how distributed systems fail.

What makes this a genuine real-world task is that the scenarios are grounded in actual failure patterns seen in production engineering: database connection pool exhaustion, WAF misconfigurations, memory leaks from unevicted caches, Redis failures causing cascading downstream outages, and bad deployments causing server crashes. The three difficulty levels mirror how real incidents present themselves — from a single unambiguous alert to a multi-service cascading failure where the root cause is buried two layers deep.

---

## Action Space

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| severity | str | ✅ Always | P1/P2/P3/P4 classification |
| root_cause | str | Medium/Hard | Snake_case root cause identifier |
| assigned_team | str | Medium/Hard | One of: backend, frontend, database, network, security, devops |
| root_cause_alert | str | Hard only | Alert ID (A/B/C) of the root cause |
| priority_order | List[str] | Hard only | Alert IDs in priority order |
| actions | Dict[str,str] | Hard only | Per-alert recommended actions |

---

## Observation Space

| Field | Type | Description |
|-------|------|-------------|
| task_difficulty | str | "easy", "medium", or "hard" |
| alerts | List[Dict] | Alert objects with id, title, message, service, timestamp |
| logs | List[str] | Relevant log lines (medium/hard only) |
| metrics | Dict[str,str] | System metrics (medium/hard only) |
| message | str | Instructions or grading feedback |
| available_teams | List[str] | Teams the agent can assign to |
| available_severities | List[str] | Always ["P1", "P2", "P3", "P4"] |

---

## Tasks

### Task 1: Severity Classification (Easy)

The agent receives a single alert describing a production incident and must classify its severity as P1, P2, P3, or P4. No logs or metrics are provided — the agent must reason purely from the alert text.

**Example:** An alert stating "Payment service completely down, transaction success rate 0%, duration 25 minutes" should be classified as P1 — a critical outage with direct customer and revenue impact.

**Grading:**
- Exact match → 1.0
- Off by 1 level (e.g. P1 vs P2) → 0.5
- Off by 2 levels → 0.2
- Off by 3 levels → 0.0

---

### Task 2: Diagnose & Assign (Medium)

The agent receives a single alert along with relevant log lines and system metrics. It must identify the severity, determine the root cause in snake_case format, and assign the incident to the correct team.

**Example:** An alert about checkout service response time spiking, combined with logs showing DB connection pool exhaustion and metrics showing 100/100 connections used, should be classified as P2, root cause `database_connection_pool_exhaustion`, assigned to the `database` team.

**Grading:**
- Severity: 40% (uses same partial credit scale as Easy)
- Root cause: 35% (exact snake_case match required)
- Assigned team: 25% (exact match required)

---

### Task 3: Cascading Failure Triage (Hard)

The agent receives multiple alerts simultaneously, along with logs and metrics. It must identify which alert is the root cause, classify overall severity, determine the correct priority order to address alerts, assign the responsible team, and recommend a specific action per alert.

**Example:** Three simultaneous alerts — Redis memory critical, payment service 500 errors, auth service timeouts — with logs showing Redis eviction causing payment DB fallback and auth cache miss. The root cause is the Redis alert (B), severity is P1, priority order is [B, A, C], and the fix is to increase Redis memory while the downstream services recover automatically.

**Grading:**
- Root cause alert identification: 30%
- Severity classification: 20%
- Priority order: 25%
- Assigned team: 10%
- Per-alert actions: 15%

---

## Reward Function

All rewards are in the range 0.0 to 1.0. The environment uses a partial credit system — the agent is never penalized below 0.0, but receives proportional credit for each correct component of its answer.

**Easy:** Severity is graded on a sliding scale based on distance from the correct level. An exact match gives full credit, being off by one level gives 0.5, off by two gives 0.2, and off by three gives 0.0.

**Medium:** The reward is a weighted sum of three components. Severity contributes 40% using the same sliding scale, root cause contributes 35% (binary — exact match or zero), and assigned team contributes 25% (binary).

**Hard:** The reward is a weighted sum of five components — root cause alert (30%), severity (20%), priority order (25%), assigned team (10%), and per-alert actions (15%). Priority order uses partial credit based on how many alerts are in the correct position.

This design rewards agents that make reasonable approximations, not just perfect answers, making it suitable for training with reinforcement learning methods like GRPO.

---

## Setup & Usage

### Install
```bash
pip install openenv-core pydantic fastapi uvicorn huggingface-hub
```

### Run locally
```bash
cd my_env
uvicorn server.app:app --reload
# Visit http://127.0.0.1:8000/docs
```

### Run with Docker
```bash
cd my_env
docker build -t incident-triage -f server/Dockerfile .
docker run -p 7860:7860 incident-triage
# Visit http://localhost:7860/docs
```

### Connect with client
```python
import asyncio
from my_env.client import IncidentTriageEnv
from my_env.models import TriageAction

async def main():
    env = IncidentTriageEnv(base_url="http://localhost:8000")
    result = await env.reset(difficulty="easy")
    obs = result.observation
    print(obs.alerts, obs.message)

    action = TriageAction(severity="P1")
    step_result = await env.step(action)
    print("Reward:", step_result.observation.reward)

asyncio.run(main())
```

### Live deployment
```
https://huggingface.co/spaces/Saraanssh1905/incident-triage
```

---

## Baseline Scores

Evaluated using `meta-llama/Llama-3.1-8B-Instruct` via HuggingFace Inference API. 3 episodes per difficulty level.

| Difficulty | Model | Average Score |
|------------|-------|---------------|
| Easy | Llama-3.1-8B-Instruct | 0.57 |
| Medium | Llama-3.1-8B-Instruct | 0.65 |
| Hard | Llama-3.1-8B-Instruct | 0.17 |

The easy score reflects that severity classification is straightforward for most scenarios but the model occasionally misclassifies by one level. The medium score shows the model reliably identifies severity and team but struggles with exact root cause naming. The hard score reflects the genuine difficulty of cascading failure analysis — identifying the true root cause among multiple simultaneous alerts requires multi-step causal reasoning that smaller models find challenging.
<img width="396" height="794" alt="image" src="https://github.com/user-attachments/assets/3ef1fcfb-c950-422d-a4af-620b030cc7f3" />

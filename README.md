---
title: incident-triage
emoji: 🚨
colorFrom: red
colorTo: blue
sdk: docker
pinned: false
app_port: 8000
---

# Incident Triage & Escalation Environment (OpenEnv)

- Simulating Multi-Step Reasoning in a Single-Step Environment

Although each episode in this environment is strictly single-step, we introduce a novel cross-episode memory mechanism that enables the agent to iteratively improve its decisions.
By feeding previous actions, rewards, and feedback back into the model, we effectively simulate multi-step reasoning without modifying the environment dynamics.

## Overview

Modern production systems fail in complex, cascading ways.

When incidents occur, on-call engineers must rapidly assess severity, identify root causes, route issues to the correct teams, and take recovery actions. This environment simulates that workflow as a reinforcement learning problem  grounded in real production failure patterns like database connection pool exhaustion, WAF/GeoIP misconfigurations, memory leaks from unevicted model caches, Redis cascades, and bad deployments triggering segfaults across backend servers.
The three difficulty levels mirror how real incidents present themselves  from a single unambiguous alert to a multi-service cascading failure where the root cause is buried two layers deep.

------------------------------------------------------------------------

## ! Why We Built This

We wanted to move beyond toy RL environments and simulate something that actually happens in real systems.

During our research, we noticed that most OpenEnv submissions focus on games or abstract tasks. However, incident triage in production systems is a real, high-stakes decision-making problem where partial correctness matters.

This environment is designed to reflect how on-call engineers think:
- Not all signals are clear
- Multiple components can fail simultaneously
- The correct answer often has degrees of correctness

Our goal was to build something that:
- Feels realistic
- Provides dense reward signals
- Challenges even strong LLMs on reasoning, not just pattern matching


------------------------------------------------------------------------

## - Repository Structure


<img width="1024" height="665" alt="image" src="https://github.com/user-attachments/assets/61fb4cf8-c7d8-44bb-84d4-b186ade81734" />



###  Architecture Overview

- `server/`  Backend simulation (what the agent interacts with)
- `models.py`  Data contracts between agent and environment
- `client.py`  Interface used by agents to communicate with the env
- `inference.py`  Baseline agent using an LLM
- `Dockerfile`  Deployment layer (HF Spaces)

------------------------------------------------------------------------

## Environment Design

### Episode Flow

reset()  observation\
step(action)  reward + feedback\
done = True(1 step per episode)

------------------------------------------------------------------------

##   Design Decisions

### Single-Step Episodes
We intentionally designed each episode to be a single step.

Reason:
- Focus on decision quality rather than exploration
- Makes evaluation deterministic and reproducible
- Aligns with real-world triage (you usually act once, not in loops)

### Weighted Reward Components
We assigned different weights to each component:

- Severity  high importance
- Root cause  slightly less
- Team  least

This reflects real-world impact:
Getting severity wrong is more costly than assigning to the wrong team.

### Scenario Design
Scenarios were inspired by real production issues:
- Database connection exhaustion
- WAF misconfigurations
- Cache cascades
- Bad deployments

**Dynamic Generative Layer:** To prevent agent memorization and test true reinforcement learning generalization, the environment applies a generative layer during `reset()`. Base scenario archetypes are dynamically perturbed, randomizing system IDs, scaling latency multipliers (e.g. `200ms` to `245ms`), and shifting resource metric percentages. This effectively creates an infinite, un-memorizable state space while maintaining underlying logical consistency.

We intentionally added **noise and misleading signals** in hard tasks to simulate real debugging complexity.

------------------------------------------------------------------------

## Action Space

The agent outputs a structured triage decision depending on difficulty:

- **Easy** → only severity
- **Medium** → severity + root cause + team
- **Hard** → full triage (ordering + actions)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `severity` | `str` | Always | P1 / P2 / P3 / P4 classification |
| `root_cause` | `str` | Medium / Hard | Snake_case root cause identifier (e.g. `db_connection_pool_exhaustion`) |
| `assigned_team` | `str` | Medium / Hard | One of: `backend`, `frontend`, `database`, `network`, `security`, `infra` |
| `root_cause_alert` | `str` | Hard only | Alert ID (A / B / C) that is the root cause of the cascade |
| `priority_order` | `List[str]` | Hard only | Alert IDs in the order they should be addressed |
| `actions` | `Dict[str, str]` | Hard only | Per-alert recommended action keyed by alert ID |

------------------------------------------------------------------------

## Observation Space

<img width="830" height="764" alt="image" src="https://github.com/user-attachments/assets/8a2a3e80-9497-4514-b338-028adc319930" />


| Field | Type | Description |
|-------|------|-------------|
| `task_id` | `str` | Unique scenario identifier (e.g. `easy_01`, `hard_02_gen_a3f1c2`) |
| `task_difficulty` | `str` | `"easy"`, `"medium"`, or `"hard"` |
| `alerts` | `List[Dict]` | Alert objects — each has `id`, `title`, `message`, `service`, `timestamp` |
| `logs` | `List[str]` | Relevant log lines (medium / hard only; empty on easy) |
| `metrics` | `Dict[str, str]` | System metrics snapshot (medium / hard only; empty on easy) |
| `message` | `str` | Task instructions on reset; scoring feedback after step |
| `available_teams` | `List[str]` | `["backend", "frontend", "database", "network", "security", "infra"]` |

------------------------------------------------------------------------

## Tasks

### Task 1 — Severity Classification (Easy)

Single alert → classify severity. No logs or metrics provided — the agent must reason purely from alert text.

6 scenarios covering all severity levels:

| ID | Service | Correct Severity | Signal |
|----|---------|-----------------|--------|
| `easy_01` | payment-service | P1 | Complete payment outage, 0% success rate, 25 min duration |
| `easy_02` | content-service | P4 | Minor 404 spike on blog pages, no user impact |
| `easy_03` | auth-service | P1 | Login failure rate 40%, users locked out |
| `easy_04` | logging-infra | P4 | Disk at 72%, fills in 14 days, informational only |
| `easy_05` | search-service | P2 | Latency 200ms → 1000ms, affects ~30% of users |
| `easy_06` | api-service | P3 | Latency 200ms → 350ms, affects <5% of users |

**Grading** (partial credit by severity distance):

| Distance | Score |
|----------|-------|
| Exact match | 1.0 |
| Off by 1 level | 0.7 |
| Off by 2 levels | 0.4 |
| Off by 3 levels | 0.1 |

------------------------------------------------------------------------

### Task 2 — Diagnose & Assign (Medium)

Alert + logs + metrics → severity + root cause + team

4 scenarios (including misleading DB CPU vs query load edge cases):

| ID | Service | Severity | Root Cause | Team |
|----|---------|----------|------------|------|
| `medium_01` | checkout-service | P2 | `db_connection_pool_exhaustion` | database |
| `medium_02` | api-gateway | P2 | `geoip_waf_misconfiguration` | security |
| `medium_03` | recommendation-service | P3 | `model_cache_memory_leak` | backend |
| `medium_04` | postgres-primary | P2 | `database_query_overload` | database |

**Grading** (weighted component scoring):

| Component | Weight | Scoring |
|-----------|--------|---------|
| Severity | 0.40 | Exact = full; off-by-1 = 0.20; else = 0.0 |
| Root Cause | 0.35 | Exact/synonym match = full; ≥50% keyword match = 0.20; else = 0.0 |
| Team | 0.25 | Exact match only |

------------------------------------------------------------------------

### Task 3 — Cascading Failure Triage (Hard)

Multiple alerts + logs + metrics → full triage decision with root cause identification, priority ordering, and per-alert remediation actions.

3 scenarios (including deep cascading timeout failures with red herrings):

| ID | Alerts | Root Cause Alert | Cascade Pattern | Team |
|----|--------|-----------------|-----------------|------|
| `hard_01` | Payment 500s, Redis memory critical, Auth timeouts | B (Redis) | Redis → Payment DB fallback → Auth token cache miss | database |
| `hard_02` | CDN origin errors, LB health fails, Deployment completed | C (Deploy) | Bad deploy → Server segfaults → LB removes hosts → CDN fails | backend |
| `hard_03` | API gateway 504s, Inventory pod crash loop, MQ backlog | B (Inventory) | OOMKill → Consumers disconnect → Gateway upstream timeout | backend |

**Grading** (weighted component scoring with anti-hack defenses):

| Component | Weight | Scoring |
|-----------|--------|---------|
| Root Cause Alert | 0.30 | Exact match = full; partial = 0.15; else = 0.0 |
| Severity | 0.20 | Exact = full; off-by-1 = 0.10; off-by-2 = 0.05 |
| Priority Order | 0.30 | Set overlap ratio (all correct = full) |
| Team | 0.10 | Exact/synonym match = full; partial = 0.05 |
| Actions | 0.20 | Per-action keyword match requiring ≥60% overlap (anti-hack threshold) |

------------------------------------------------------------------------
------------------------------------------------------------------------

## Reward Function

The environment uses a **dense, structured reward function (0.0  1.0)** that provides
both **positive reinforcement for correct reasoning** and **implicit negative marking for mistakes**.

Rather than binary success/failure, the agent is evaluated across multiple dimensions,
so the agent gets useful feedback instead of just pass/fail.

---

###  Reward Structure by Task

####  Easy Task (Severity Classification)

Reward is based on distance from correct severity:

| Condition | Reward |
|----------|--------|
| Exact match | 1.0 |
| Off by 1 level | 0.7 |
| Off by 2 levels | 0.4 |
| Completely wrong | 0.0 |

---

#### ! Medium Task (Diagnosis & Assignment)

Total reward = weighted sum:

R = 0.4Severity + 0.35RootCause + 0.25Team

- Severity  exact or partial match
- Root Cause  exact / partial string match
- Team  exact match only

---

####  Hard Task (Cascading Failure Triage)

Total reward:

R = 0.30RootCauseAlert + 0.20Severity + 0.25PriorityOrder + 0.10Team + 0.15Actions  

- Priority  full or partial (first correct)
- Actions  keyword overlap scoring

> ! Note: Even GPT-level models struggle with the hard tasks due to misleading signals.

---

##  Negative Marking (Penalty Design)

The environment incorporates **implicit negative marking** by reducing reward
for incorrect, incomplete, or suboptimal decisions.

### Key Penalty Mechanisms

####  Incorrect Decisions
- Wrong severity  sharp drop (up to 0.0)
- Wrong root cause / team  zero contribution for that component

####  Missing Information
- Not providing required fields (root cause, actions, etc.)
   treated as **0 contribution**
- Encourages **complete outputs**, not partial guessing

####  Poor Reasoning / Ordering
- Incorrect priority order in hard tasks:
  - Full mismatch  0
  - Only first correct  partial (0.10)
- Prevents random ordering strategies

####  Low-Quality Actions
- Actions are evaluated via **semantic keyword overlap**
- Irrelevant or vague actions  low score contribution

---

##  Code-Level Mapping

The reward logic is directly implemented in:

- `environment.py::_grade_easy()`
- `environment.py::_grade_medium()`
- `environment.py::_grade_hard()`

Each function:
- Computes **component-wise scores**
- Aggregates them into a final reward  [0.0, 1.0]
- Returns **detailed feedback** explaining correctness

---

## � Learning Paradigm

This environment does **not perform learning internally**.

- Each episode is **independent**
- The environment is **stateless across episodes**
- The agent receives a **single-step reward per episode**

Learning occurs **externally**, where:

- A training algorithm (e.g., RL, GRPO, fine-tuning)
- Uses the reward signal returned by the environment
- To iteratively improve the agents policy across episodes

The role of this environment is to provide:
- A **high-quality reward signal**
- A **deterministic evaluation framework**
- A **realistic decision-making task**

This design aligns with standard reinforcement learning pipelines,
where environments act as evaluators rather than learners.

------------------------------------------------------------------------

##  Live Agent Performance (Our Latest Run)
Following full LLM reasoning via Qwen 72B Instruct on **Dynamic Generative Scenarios**:
  Difficulty   Validation Score
  ------------ ----------------
  Easy         **1.00** *(Perfect routing & diagnosis)*
  Medium       **~0.77** *(Demands mathematically precise root causes)*
  Hard         **~0.80** *(Heavily penalizes loose or verbose action descriptions)*

------------------------------------------------------------------------

� Cross-Episode Memory (Simulated Multi-Step Reasoning)

Although the environment itself is strictly single-step per episode, we extend agent capability by introducing a cross-episode memory mechanism in the inference pipeline.

! Key Idea

Instead of modifying the environment (which remains stateless), we simulate multi-step reasoning by:

Storing the previous episodes trajectory
Feeding it back into the agents prompt for the next episode

This allows the agent to learn from past mistakes and iteratively improve decisions across episodes.

 How It Works

After each episode, we store:

Agent action
Reward received
Feedback from the environment
{
  "action": {...},
  "reward": 0.52,
  "feedback": "Incorrect root cause..."
}

This is saved in a persistent memory file:

memory/trajectory.json


 Memory  Prompt Injection

Before generating the next action, the agent is given:

PREVIOUS ATTEMPTS:
Step 1:
Action: ...
Reward: ...
Observation: ...

Step 2:
...

This enables the model to:

Identify incorrect reasoning patterns
Avoid repeating mistakes
Improve root cause identification and prioritization

  Why This Matters

Even though the environment is single-step:

The agent becomes trajectory-aware
Decision-making becomes iterative instead of one-shot
This simulates reinforcement learning-style improvement without modifying the environment
 Observed Impact

This mechanism had minimal effect on easy tasks (already near optimal), but showed clear improvement on hard cascading failure scenarios, where reasoning depth matters.

------------------------------------------------------------------------

##  Limitations & Anti-Hacking Defenses

- **Strict String Matching:** We consciously rejected semantic/LLM-as-a-judge evaluation to prevent rate limiting and ensure 100% determinism. Furthermore, our `fuzzy_match` strictly requires 60% term overlap and multi-keyword intersections to prevent "reward hacking" (where LLMs output massive buzzword lists to accidentally trigger scores).
- **Single-step episodes:** While this limits long-horizon learning, it perfectly mirrors the standard OpenEnv interface while our inference pipeline handles the cross-episode memory simulation.

These were conscious trade-offs to ensure:
- Deterministic and hack-proof grading
- Fast and reliable Judge inference
- Simplicity for hackathon constraints

------------------------------------------------------------------------

## - Future Improvements

- Multi-step episodes with evolving system state
- More diverse and noisy real-world scenarios
- Better semantic evaluation for actions
- Integration with real observability data formats

This would make the environment closer to real production systems.

------------------------------------------------------------------------

## Setup (Run commands on git bash terminal)

### Install

pip install openenv-core fastapi uvicorn pydantic openai

### Run locally

uvicorn server.app:app --reload

Open: http://127.0.0.1:8000/docs

<img width="1167" height="916" alt="image" src="https://github.com/user-attachments/assets/3a68cd67-334c-44d9-928b-02fdf4fe5b3c" />


------------------------------------------------------------------------

### Docker

docker build -t incident-triage\
docker run -p 8000:8000 incident-triage

------------------------------------------------------------------------

### Deploy

openenv push --repo-id `<your-username>`{=html}/incident-triage

------------------------------------------------------------------------

## Automated Agent Scores (w/ Dynamic Gen)

  Difficulty   Score
  ------------ -------
  Easy         1.00
  Medium       0.77
  Hard         0.80

------------------------------------------------------------------------

 Memory Snapshot

Example of stored trajectory:

cat memory/trajectory.json

<img width="1897" height="342" alt="image" src="https://github.com/user-attachments/assets/0f24743c-d415-4e1b-9fce-54618a249376" />


The agent stores full episode trajectories including alerts, logs, actions, and rewards.
This enables cross-episode reasoning, where the model can identify failure patterns and improve decisions in subsequent attempts.
------------------------------------------------------------------------

## Inference

export HF_TOKEN=your_token\
python inference.py --base-url http://localhost:8000

------------------------------------------------------------------------

## Live Demo

https://huggingface.co/spaces/Saraanssh1905/incident-triage

<img width="1919" height="974" alt="image" src="https://github.com/user-attachments/assets/9eba444c-0b20-48a3-9219-ac3c75633bcc" />





------------------------------------------------------------------------

##  Team Contributions

- **Omkar Iyer**
  - Designed evaluation logic and reward shaping
  - Worked on deployment and validation

- **Saraanssh Mehra**
  - Built environment simulation and scenarios
  - Implemented backend and API integration


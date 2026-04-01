# Incident Triage & Escalation Environment (OpenEnv)

## Overview

Modern production systems fail in complex, cascading ways.

When incidents occur, on-call engineers must rapidly assess severity, identify root causes, route issues to the correct teams, and take recovery actions. This environment simulates that workflow as a reinforcement learning problem — grounded in real production failure patterns like database connection pool exhaustion, WAF/GeoIP misconfigurations, memory leaks from unevicted model caches, Redis cascades, and bad deployments triggering segfaults across backend servers.
The three difficulty levels mirror how real incidents present themselves — from a single unambiguous alert to a multi-service cascading failure where the root cause is buried two layers deep.

------------------------------------------------------------------------

## 💡 Why We Built This

We wanted to move beyond toy RL environments and simulate something that actually happens in real systems.

During our research, we noticed that most OpenEnv submissions focus on games or abstract tasks. However, incident triage in production systems is a real, high-stakes decision-making problem where partial correctness matters.

This environment is designed to reflect how on-call engineers think:
- Not all signals are clear
- Multiple components can fail simultaneously
- The “correct” answer often has degrees of correctness

Our goal was to build something that:
- Feels realistic
- Provides dense reward signals
- Challenges even strong LLMs on reasoning, not just pattern matching

------------------------------------------------------------------------

## 🧠 Design Decisions

### Single-Step Episodes
We intentionally designed each episode to be a single step.

Reason:
- Focus on decision quality rather than exploration
- Makes evaluation deterministic and reproducible
- Aligns with real-world triage (you usually act once, not in loops)

### Weighted Reward Components
We assigned different weights to each component:

- Severity → high importance
- Root cause → slightly less
- Team → least

This reflects real-world impact:
Getting severity wrong is more costly than assigning to the wrong team.

### Scenario Design
Scenarios were inspired by real production issues:
- Database connection exhaustion
- WAF misconfigurations
- Cache cascades
- Bad deployments

We intentionally added **noise and misleading signals** in hard tasks to simulate real debugging complexity.


------------------------------------------------------------------------

## 📂 Repository Structure


<img width="1536" height="1024" alt="image" src="https://github.com/user-attachments/assets/e3bf75e7-c037-4eb6-861d-79fb16e6b05b" />


### 🧩 Architecture Overview

- `server/` → Backend simulation (what the agent interacts with)
- `models.py` → Data contracts between agent and environment
- `client.py` → Interface used by agents to communicate with the env
- `inference.py` → Baseline agent using an LLM
- `Dockerfile` → Deployment layer (HF Spaces)

------------------------------------------------------------------------

## Environment Design

### Episode Flow

reset() → observation\
step(action) → reward + feedback\
done = True(1 step per episode)

------------------------------------------------------------------------

## Action Space

The agent outputs a structured triage decision depending on difficulty:

- Easy → only severity
- Medium → severity + root cause + team
- Hard → full triage (ordering + actions)


<img width="886" height="472" alt="image" src="https://github.com/user-attachments/assets/f4de333b-94f7-4e37-a7fa-25ac2758557e" />




------------------------------------------------------------------------

## Observation Space

<img width="830" height="764" alt="image" src="https://github.com/user-attachments/assets/8a2a3e80-9497-4514-b338-028adc319930" />




------------------------------------------------------------------------

## Tasks

### Task 1 - Severity Classification (Easy)

Single alert → classify severity. No logs or metrics provided — the agent must reason purely from alert text.

6 scenarios covering all severity levels:

<img width="873" height="411" alt="image" src="https://github.com/user-attachments/assets/043884b0-91f3-42fa-a17c-a6c9ef559d1f" />

Results:

<img width="636" height="214" alt="image" src="https://github.com/user-attachments/assets/270e119e-25cc-46b0-867a-efda5b5f9237" />

Grading:

<img width="860" height="301" alt="image" src="https://github.com/user-attachments/assets/a897b747-1435-47bd-8377-7718d7a61199" />



------------------------------------------------------------------------

### Task 2 - Diagnose & Assign (Medium)

Alert + logs + metrics → severity + root cause + team

3 scenarios:

<img width="883" height="240" alt="image" src="https://github.com/user-attachments/assets/1562984a-69ff-4960-ade3-81e6b5a865be" />

Results:


<img width="676" height="399" alt="image" src="https://github.com/user-attachments/assets/aba25dfe-9787-4b63-a13b-61dc7d810fbc" />

Grading:

<img width="884" height="256" alt="image" src="https://github.com/user-attachments/assets/2a695923-bdcc-426a-aa12-1537664477fb" />


------------------------------------------------------------------------

### Task 3 - Cascading Failure (Hard)

Multiple alerts +logs+metrics → full triage decision.

2 scenarios:

<img width="868" height="253" alt="image" src="https://github.com/user-attachments/assets/48afbb64-3dd6-4bdf-85ac-5a5470bfde99" />



<img width="873" height="255" alt="image" src="https://github.com/user-attachments/assets/db2d8dc4-4bd9-40d3-acb5-970a2d78046a" />



Results:

<img width="920" height="856" alt="image" src="https://github.com/user-attachments/assets/e1d94aa3-c6ad-4331-9d13-23b8f0b387d3" />

Grading: 

<img width="881" height="358" alt="image" src="https://github.com/user-attachments/assets/db516ce4-a1fe-402d-b748-131f162f1bbf" />





------------------------------------------------------------------------

## Reward Function

The environment uses a **dense, structured reward function (0.0 → 1.0)** that provides
both **positive reinforcement for correct reasoning** and **implicit negative marking for mistakes**.

Rather than binary success/failure, the agent is evaluated across multiple dimensions,
so the agent gets useful feedback instead of just pass/fail.

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

R = 0.30·RootCauseAlert + 0.20·Severity + 0.25·PriorityOrder + 0.10·Team + 0.15·Actions  

- Priority → full or partial (first correct)
- Actions → keyword overlap scoring

> 💡 Note: Even GPT-level models struggle with the hard tasks due to misleading signals.

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

## 🔁 Learning Paradigm

This environment does **not perform learning internally**.

- Each episode is **independent**
- The environment is **stateless across episodes**
- The agent receives a **single-step reward per episode**

Learning occurs **externally**, where:

- A training algorithm (e.g., RL, GRPO, fine-tuning)
- Uses the reward signal returned by the environment
- To iteratively improve the agent’s policy across episodes

The role of this environment is to provide:
- A **high-quality reward signal**
- A **deterministic evaluation framework**
- A **realistic decision-making task**

This design aligns with standard reinforcement learning pipelines,
where environments act as evaluators rather than learners.

------------------------------------------------------------------------

## ⚠️ Limitations

- The environment uses predefined scenarios (not dynamic generation)
- Root cause matching is string-based (not semantic understanding)
- Single-step episodes limit long-horizon learning

These were conscious trade-offs to ensure:
- Deterministic evaluation
- Fast inference
- Simplicity for hackathon constraints

------------------------------------------------------------------------

## 🚀 Future Improvements

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

## Inference

export HF_TOKEN=your_token\
python inference.py --base-url http://localhost:8000

------------------------------------------------------------------------

## Live Demo

https://huggingface.co/spaces/Saraanssh1905/incident-triage

<img width="1919" height="974" alt="image" src="https://github.com/user-attachments/assets/9eba444c-0b20-48a3-9219-ac3c75633bcc" />





------------------------------------------------------------------------

## 👥 Team Contributions

- **Omkar Iyer**
  - Designed evaluation logic and reward shaping
  - Worked on deployment and validation

- **Saraanssh Mehra**
  - Built environment simulation and scenarios
  - Implemented backend and API integration


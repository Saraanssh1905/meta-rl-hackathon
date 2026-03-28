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

[2-3 paragraphs: what incident triage is, why it matters for AI agent training, 
what makes this a genuine real-world task]

## Action Space

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| severity | str | ✅ Always | P1/P2/P3/P4 classification |
| root_cause | str | Medium/Hard | Snake_case root cause identifier |
| assigned_team | str | Medium/Hard | One of: backend, frontend, database, network, security, devops |
| root_cause_alert | str | Hard only | Alert ID (A/B/C) of the root cause |
| priority_order | List[str] | Hard only | Alert IDs in priority order |
| actions | Dict[str,str] | Hard only | Per-alert recommended actions |

## Observation Space

| Field | Type | Description |
|-------|------|-------------|
| task_difficulty | str | "easy", "medium", or "hard" |
| alerts | List[Dict] | Alert objects with id, title, message, service, timestamp |
| logs | List[str] | Relevant log lines (medium/hard only) |
| metrics | Dict[str,str] | System metrics (medium/hard only) |
| message | str | Instructions or grading feedback |
| available_teams | List[str] | Teams the agent can assign to |

## Tasks

### Task 1: Severity Classification (Easy)
[describe what agent does, example, grading: exact=1.0, off-by-1=0.5, off-by-2=0.2]

### Task 2: Diagnose & Assign (Medium)  
[describe, grading weights: severity 40% + root cause 35% + team 25%]

### Task 3: Cascading Failure Triage (Hard)
[describe, grading: root cause alert 30% + severity 20% + priority 25% + team 10% + actions 15%]

## Reward Function

[explain partial credit system, how each component is scored, that rewards are 0.0-1.0]

## Setup & Usage

[pip install, local run, Docker run, connect with client code example]

## Baseline Scores

| Difficulty | Model | Average Score |
|-----------|-------|--------------|
| Easy | gpt-4o-mini | X.XX |
| Medium | gpt-4o-mini | X.XX |
| Hard | gpt-4o-mini | X.XX |

import os
import json
import argparse
import asyncio
from openai import OpenAI

from client import IncidentTriageEnv
from models import TriageAction

# ================= MEMORY =================
os.makedirs("memory", exist_ok=True)

MEMORY_PATH = "memory/trajectory.json"


def load_memory():
    if not os.path.exists(MEMORY_PATH):
        return {"steps": []}
    with open(MEMORY_PATH, "r") as f:
        return json.load(f)


def save_memory(memory):
    with open(MEMORY_PATH, "w") as f:
        json.dump(memory, f, indent=2)


def reset_memory():
    save_memory({"steps": []})


def append_memory(obs, action_dict, reward):
    memory = load_memory()

    memory["steps"].append({
        "alerts": obs.alerts,
        "logs": obs.logs,
        "metrics": obs.metrics,
        "action": action_dict,
        "reward": reward 
    })

    save_memory(memory)

# ENV CONFIG (MANDATORY)

API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
API_KEY = os.getenv("HF_TOKEN")
MODEL_NAME = os.getenv("MODEL_NAME", "meta-llama/Llama-3.1-8B-Instruct")

if not API_KEY:
    print(" No API key found. Running in mock mode.")


client = None

if API_KEY:
    client = OpenAI(
        base_url=API_BASE_URL,
        api_key=API_KEY,
    )
else:
    print(" No API key found. Running in fallback mode.")

def build_prompt(obs):
    memory = load_memory()

    history_text = ""
    for i, step in enumerate(memory["steps"][-3:]):
        history_text += f"""
    Previous Step {i+1}:
    Action: {step['action']}
    Reward: {step['reward']}
    Observation: {step['alerts']}
    """
        
    """Build an LLM prompt from the observation."""
    
    alerts_text = ""
    for a in obs.alerts:
        alerts_text += f"\n  Alert {a['id']}: [{a['title']}] {a['message']}"

    logs_text = "\n  ".join(obs.logs) if obs.logs else "None"
    metrics_text = json.dumps(obs.metrics, indent=2) if obs.metrics else "None"
    difficulty = obs.task_difficulty
    hint_text = getattr(obs, "hint", None)

    prompt = f"""You are an expert on-call SRE engineer.
    You are improving over previous attempts. Learn from past mistakes.

PREVIOUS ATTEMPTS:
{history_text}
Think step-by-step internally, but DO NOT output your reasoning.

IMPORTANT:
- Return ONLY valid JSON
- Do NOT include explanations in output
- Do NOT include markdown

Difficulty: {difficulty}

ALERTS:
{alerts_text}

LOGS:
{logs_text}

METRICS:
{metrics_text}
"""

    prompt += """

GUIDELINES:
- Try to improve over previous reward and avoid repeating mistakes
- Determine severity based on user impact:
  - P1: Complete outage or critical failure affecting most users
  - P2: Major degradation affecting many users
  - P3: Minor issue affecting few users
  - P4: Informational, no user impact

- Identify root cause from logs and metrics (not just alerts)
- In multi-alert scenarios:
  - The root cause is usually the earliest failing component
  - Other alerts are downstream effects

- Think step-by-step internally, but output ONLY JSON
"""
    prompt += """

For multi-alert incidents:
- Identify which alert happened FIRST
- Trace dependency chain (what caused what)
- Fix the root cause, others will resolve
"""
    prompt += """

IMPORTANT:
- Do NOT overestimate severity
- Not all issues are P1
- Use impact, not panic signals
"""
    prompt += """

COMMON ROOT CAUSE PATTERNS:

- "connection pool exhausted", "max_connections reached" → database_connection_pool_exhaustion → team: database
- "WAF blocking", "403 spike", "geoip rules" → waf_geoip_misconfiguration → team: security
- "memory leak", "heap growing", "OOM" → memory_leak → team: backend
- "high latency + DB logs slow" → database_issue → team: database

Always map logs → root cause → correct team.
"""
    prompt += """

FOR MULTI-ALERT CASES:

- The FIRST alert in time is usually the root cause
- Fixing root cause resolves downstream alerts
- Priority order = [root cause → affected systems]

Example:
If Redis fails → DB overload → service errors  
Then:
Root cause = Redis  
Priority = Redis → DB → Services
"""
    # hint BEFORE instructions
    if hint_text:
        prompt += f"\nHINT: {hint_text}\n"
        prompt += "Use this hint to identify the root cause.\n"

    # difficulty-specific instructions

    if difficulty == "easy":
        prompt += """
    "Output ONLY valid JSON. Do not include explanation outside JSON."

    Format:
    {"severity": "P1" | "P2" | "P3" | "P4"}
    """

    elif difficulty == "medium":
        prompt += """
    "Output ONLY valid JSON. Do not include explanation outside JSON."

    Format:
    {
        "severity": "P1|P2|P3|P4",
    "root_cause": "short_snake_case",
    "assigned_team": "one of the available teams"
    }
    """

    else:
        prompt += """
    "Output ONLY valid JSON. Do not include explanation outside JSON."

    Format:
    {
        "severity": "P1|P2|P3|P4",
        "root_cause_alert": "A|B|C",
        "priority_order": ["A","B","C"],
        "assigned_team": "one of the available teams",
        "actions": {"A": "...", "B": "...", "C": "..."}
    }
    """
    return prompt


def safe_parse_action(raw_text):
    import json

    
    # STEP 1: Extract JSON safely
    
    try:
        start = raw_text.find("{")
        end = raw_text.rfind("}") + 1

        if start != -1 and end != -1:
            json_str = raw_text[start:end]
            data = json.loads(json_str)
        else:
            raise ValueError("No JSON found")

    except Exception:
        data = {}

    
    # STEP 2: Fix severity
    
    severity = data.get("severity", "P3")
    if severity not in ["P1", "P2", "P3", "P4"]:
        severity = "P3"

    
    # STEP 3: Fix priority_order
    
    priority_order = data.get("priority_order")
    if not isinstance(priority_order, list):
        priority_order = []

    
    # STEP 4: Fix actions
    
    actions = data.get("actions")
    if not isinstance(actions, dict):
        actions = {}

    
    # STEP 5: Normalize team
    
    team = data.get("assigned_team", "")
    if team:
        team = team.lower()

    TEAM_MAP = {
        "infrastructure team": "infra",
        "devops": "infra",
        "security team": "security",
        "backend team": "backend",
        "database team": "database"
    }

    team = TEAM_MAP.get(team, team)

    
    # STEP 6: Safe return
    
    return TriageAction(
        severity=severity,
        root_cause=data.get("root_cause", "unknown issue"),
        assigned_team=team,
        root_cause_alert=data.get("root_cause_alert", ""),
        priority_order=priority_order,
        actions=actions,
    )

def log_start(task, env, model):
    print(f"[START] task={task} env={env} model={model}", flush=True)

def log_step(step, action, reward, done, error):
    error_val = error if error else "null"
    done_val = str(done).lower()
    print(
        f"[STEP] step={step} action={action} reward={reward:.2f} done={done_val} error={error_val}",
        flush=True,
    )

def log_end(success, steps, score, rewards):
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} score={score:.2f} rewards={rewards_str}",
        flush=True,
    )

async def run_episode(base_url, difficulty):
    TASK_NAME = "incident_triage"
    BENCHMARK = "openenv"

    log_start(f"{difficulty}_task", BENCHMARK, MODEL_NAME)

    rewards = []
    steps_taken = 0
    success = False

    env = None

    try:
        # -------- SAFE ENV INIT --------
        try:
            env = IncidentTriageEnv(base_url=base_url)
            result = await env.reset()
            obs = result.observation
        except Exception as e:
            print("[DEBUG] ENV RESET FAILED:", e)
            env = None
            obs = type("MockObs", (), {
                "alerts": [],
                "logs": [],
                "metrics": {},
                "task_difficulty": "easy",
                "hint": None
            })()

        # -------- STEP LOOP --------
        for step in range(1, 6):
            try:
                prompt = build_prompt(obs)

                try:
                    if client:
                        completion = await asyncio.wait_for(
                            asyncio.to_thread(
                                client.chat.completions.create,
                                model=MODEL_NAME,
                                messages=[{"role": "user", "content": prompt}],
                                temperature=0,
                                max_tokens=300,
                            ),
                            timeout=15,
                        )
                        raw = completion.choices[0].message.content or ""
                    else:
                        raw = '{"severity": "P3"}'

                    if not raw or "{" not in raw:
                        raise ValueError("Bad output")

                except Exception as e:
                    raw = json.dumps({
                        "severity": "P3",
                        "root_cause": "unknown_issue",
                        "assigned_team": "backend",
                        "root_cause_alert": "",
                        "priority_order": [],
                        "actions": {}
                    })

                try:
                    action = safe_parse_action(raw)
                except:
                    action = TriageAction(severity="P3")

                reward = 0.0
                done = False
                error = None

                # -------- SAFE STEP --------
                if env:
                    try:
                        result = await env.step(action)
                        obs = result.observation
                        reward = result.observation.reward or 0.0
                        done = result.done
                    except Exception as e:
                        error = str(e)

                rewards.append(reward)
                steps_taken = step

                log_step(step, str(action), reward, done, error)

                if done:
                    break

            except Exception as e:
                log_step(step, "fallback", 0.0, False, str(e))
                continue

        score = sum(rewards) / len(rewards) if rewards else 0.0
        success = score > 0

    except Exception as e:
        print("[DEBUG] EPISODE FAILED:", e)

    finally:
        try:
            if env:
                await env.close()
        except:
            pass

        log_end(success, steps_taken, score, rewards)
        return score   


# MAIN RUN

async def run_inference(base_url):
    difficulties = ["easy", "medium", "hard"]
    difficulty_scores = {}

    for difficulty in difficulties:
        scores = []

        for ep in range(3):
            score = await run_episode(base_url, difficulty)
            scores.append(score)

        avg = sum(scores) / len(scores) if scores else 0.0
        difficulty_scores[difficulty] = avg

    
    print("\n[DEBUG] FINAL SCORES")
    for d, s in difficulty_scores.items():
        print(f"[DEBUG] {d} avg: {s:.2f}")


# ENTRYPOINT

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inference Script")
    parser.add_argument(
        "--base-url",
        default=os.getenv("BASE_URL") or os.getenv("API_BASE_URL") or "http://localhost:8000"
    )

    args = parser.parse_args()

    asyncio.run(run_inference(args.base_url))


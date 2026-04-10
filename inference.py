import os
import json
import argparse
import asyncio
from typing import List, Optional

from openai import OpenAI
from client import IncidentTriageEnv
from models import TriageAction

#  CONFIG
# Environment variables will be fetched inside main() to correctly capture injected values

MAX_STEPS = 1

#  MEMORY 
os.makedirs("memory", exist_ok=True)
MEMORY_PATH = "memory/trajectory.json"

def load_memory():
    if not os.path.exists(MEMORY_PATH):
        return {"steps": []}
    with open(MEMORY_PATH, "r") as f:
        return json.load(f)

def save_memory(memory):
    with open(MEMORY_PATH, "w") as f:
        json.dump(memory, f)

def reset_memory():
    save_memory({"steps": []})

def append_memory(obs, action_dict, reward):
    memory = load_memory()
    memory["steps"].append({
        "alerts": obs.alerts,
        "action": action_dict,
        "reward": reward
    })
    save_memory(memory)

#  LOGGING 

def log_start(task, env, model):
    print(f"[START] task={task} env={env} model={model}", flush=True)

def log_step(step, action, reward, done, error):
    error_val = error if error else "null"
    print(
        f"[STEP] step={step} action={action} reward={reward:.2f} done={str(done).lower()} error={error_val}",
        flush=True
    )

def log_end(success, steps, score, rewards):
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} score={score:.2f} rewards={rewards_str}",
        flush=True
    )

# PROMPT 

def build_prompt(obs):
    memory = load_memory()

    history_text = ""
    for i, step in enumerate(memory["steps"][-3:]):
        action = step["action"]

        history_text += f"""
        Previous attempt {i+1}:
        - reward: {step['reward']:.2f}
        - predicted root cause: {action.get('root_cause')}
        - predicted team: {action.get('assigned_team')}

        Insight:
        - {'Good prediction, similar reasoning may help' if step['reward'] > 0.7 else 'Incorrect prediction, avoid this pattern'}
        """

    alerts_text = ""
    for a in obs.alerts:
        alerts_text += f"\nAlert {a['id']}: [{a['title']}] {a['message']}"

    logs_text = "\n".join(obs.logs) if obs.logs else "None"
    metrics_text = json.dumps(obs.metrics, indent=2) if obs.metrics else "None"

    difficulty = obs.task_difficulty

    prompt = f"""
    You are an expert SRE engineer.

    Previous attempts:
    {history_text}

    Alerts:
    {alerts_text}

    Logs:
    {logs_text}

    Metrics:
    {metrics_text}

    IMPORTANT:
    - Return ONLY valid JSON
    - No explanations
    - No markdown

    Return JSON with:
    - severity must be one of: P1, P2, P3, P4

    MEMORY USAGE RULES:
    - Use previous attempts as guidance, NOT exact answers
    - Do NOT copy previous root causes directly
    - Adapt based on logs and metrics

    SEVERITY GUIDELINES:
    - P1: service down, 500 errors, revenue impact
    - P2: degraded performance, high latency
    - P3: partial issues, limited impact
    - P4: minor or informational alerts

    GUIDELINES:
    - Use logs + metrics to find root cause
    - Do NOT rely only on alert text
    - Map root cause  correct team

    COMMON PATTERNS:
    - connection pool exhausted  database
    - WAF blocking  security
    - memory leak  backend

    MULTI-ALERT RULES:
    - Earliest failing component = root cause
    - Other alerts are downstream
    """

    prompt += """
    CRITICAL:
    - root_cause must NEVER be null
    - Always infer a specific root cause from logs
    - Use snake_case (e.g., redis_failure, db_connection_exhaustion)
    """

    if difficulty == "easy":
        prompt += """
        If unsure, prefer P2 (not P1, not P4)
        """
        prompt += '\n{"severity": "P1"}'

    elif difficulty == "medium":
        prompt += """
            IMPORTANT:
            - Use EXACT root cause from logs
            - Use specific snake_case terms
            - Examples:
            - postgres_connection_pool_exhaustion
            - waf_geoip_misconfiguration
            - model_cache_memory_leak
            - Map to correct team precisely
            """
        prompt += '\n{"severity":"P1","root_cause":"database_issue","assigned_team":"database"}'

    else:
        prompt += """
            IMPORTANT:
            - Identify the TRUE root cause (not symptoms)
            - root_cause_alert = earliest failing alert
            - priority_order must start with root cause

            - ALWAYS include:
            - root_cause_alert
            - priority_order
            - actions

            - Each action must directly address the issue in logs
            """
        prompt += '\n{"severity":"P1","root_cause_alert":"A","priority_order":["A","B","C"],"assigned_team":"backend","actions":{"A":"...","B":"...","C":"..."}}'

    return prompt

# SAFE PARSE 

def safe_parse(raw):
    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        data = json.loads(raw[start:end])
    except:
        data = {}

    # FORCE CORRECT TYPES

    severity = data.get("severity", "P3")
    if severity not in ["P1", "P2", "P3", "P4"]:
        severity = "P3"

    root_cause = data.get("root_cause")
    if not root_cause:
        root_cause = "unknown_issue"

    assigned_team = data.get("assigned_team")
    if not assigned_team:
        assigned_team = "backend"

    root_cause_alert = data.get("root_cause_alert")

    priority_order = data.get("priority_order")
    if not isinstance(priority_order, list):
        priority_order = None

    actions = data.get("actions")
    if not isinstance(actions, dict):
        actions = None

    return TriageAction(
        severity=severity,
        root_cause=root_cause,
        assigned_team=assigned_team,
        root_cause_alert=root_cause_alert,
        priority_order=priority_order,
        actions=actions,
    )

# MAIN 

async def main(base_url):

    if "API_BASE_URL" not in os.environ:
        os.environ["API_BASE_URL"] = "https://router.huggingface.co/v1"
    if "API_KEY" not in os.environ:
        os.environ["API_KEY"] = os.environ.get("HF_TOKEN", "dummy_key")

    client = OpenAI(
        base_url=os.environ["API_BASE_URL"],
        api_key=os.environ["API_KEY"]
    )
    
    model_name = os.environ.get("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")

    difficulties = ["easy", "medium", "hard"]

    for difficulty in difficulties:

        reset_memory()  #  MEMORY PERSISTS ACROSS EPISODES

        for ep in range(3):

            rewards_all = []
            steps_taken = 0

            log_start(
                task=f"incident-triage-{difficulty}-ep{ep}",
                env="openenv",
                model=model_name
            )

            env = None
            try:
                image_name = os.environ.get("IMAGE_NAME")
                if image_name:
                    env = await IncidentTriageEnv.from_docker_image(image_name)
                else:
                    env = IncidentTriageEnv(base_url=base_url)
                    await env.__aenter__()

                result = await env.reset(difficulty=difficulty)  #  removed seed
                obs = result.observation

                prompt = build_prompt(obs)

                completion = client.chat.completions.create(
                        model=model_name,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0,
                        max_tokens=200,
                        
                    )
                raw = completion.choices[0].message.content or ""


                action = safe_parse(raw)

                step_result = await env.step(action)
                reward = step_result.reward or 0.0

                append_memory(obs, action.__dict__, reward)

                rewards_all.append(reward)
                steps_taken = 1

                log_step(
                    step=1,
                    action=json.dumps(action.__dict__),
                    reward=reward,
                    done=True,
                    error=None
                )

            except Exception as e:
                import traceback
                print(f"[DEBUG] failure: {e}", flush=True)
                traceback.print_exc()
                raise e
            finally:
                if env:
                    if image_name:
                        await env.close()
                    else:
                        await env.__aexit__(None, None, None)

            # Task validation requires score to be strictly in (0, 1)
            score = max(min(sum(rewards_all), 0.99), 0.01)
            success = score > 0.3

            log_end(success, steps_taken, score, rewards_all)

# ENTRY 

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:7860")
    args = parser.parse_args()

    asyncio.run(main(args.base_url))


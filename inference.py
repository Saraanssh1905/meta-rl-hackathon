import os
import json
import argparse
import asyncio
from openai import OpenAI

from client import IncidentTriageEnv
from models import TriageAction


# -----------------------------
# ENV CONFIG (MANDATORY)
# -----------------------------
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY")
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
    print("⚠️ No API key found. Running in fallback mode.")

def build_prompt(obs):
    """Build an LLM prompt from the observation."""
    
    alerts_text = ""
    for a in obs.alerts:
        alerts_text += f"\n  Alert {a['id']}: [{a['title']}] {a['message']}"

    logs_text = "\n  ".join(obs.logs) if obs.logs else "None"
    metrics_text = json.dumps(obs.metrics, indent=2) if obs.metrics else "None"
    difficulty = obs.task_difficulty
    hint_text = getattr(obs, "hint", None)

    prompt = f"""You are an expert on-call SRE engineer.

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
    # 🔥 Add hint BEFORE instructions
    if hint_text:
        prompt += f"\nHINT: {hint_text}\n"
        prompt += "Use this hint to identify the root cause.\n"

    # 🔥 NOW add difficulty-specific instructions
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

# -----------------------------
# SAFE PARSER (UPGRADE)
# -----------------------------
def safe_parse_action(raw_text):
    try:
        start = raw_text.find("{")
        end = raw_text.rfind("}") + 1
        data = json.loads(raw_text[start:end])

        return TriageAction(
            severity=data.get("severity", "P3"),
            root_cause=data.get("root_cause"),
            assigned_team=data.get("assigned_team"),
            root_cause_alert=data.get("root_cause_alert"),
            priority_order=data.get("priority_order"),
            actions=data.get("actions"),
        )
    except Exception:
        return TriageAction(severity="P3")  # fallback


# -----------------------------
# MAIN RUN
# -----------------------------
async def run_inference(base_url):
    all_results = {}

    for difficulty in ["easy", "medium", "hard"]:
        scores = []
        failures=0
        print(f"\n{'='*50}")
        print(f"  {difficulty.upper()} TASKS")
        print(f"{'='*50}")

        for ep in range(3):
            async with IncidentTriageEnv(base_url=base_url) as env:
                reset_result = await env.reset(seed=ep, difficulty=difficulty)
                obs = reset_result.observation

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
                            timeout=10,
                        )

                        raw = completion.choices[0].message.content or ""

                        print(f"RAW MODEL OUTPUT: {raw}")

                    else:
                        raw = '{"severity": "P3"}'

                    # 🔥 fallback if empty or bad
                    if not raw or not raw.strip() or "{" not in raw:
                        raw = '{"severity": "P3"}'

                except Exception as e:
                    print(f"  ep{ep}: model failed → fallback | {e}")
                    raw = '{"severity": "P3"}'
                    failures += 1
                action = safe_parse_action(raw)

                step_result = await env.step(action)
                reward = step_result.observation.reward or 0.0
                scores.append(reward)

                print(
                    f"  ep{ep}: score={reward:.2f} "
                    f"| {step_result.observation.message[:80]}"
                )

        avg = round(sum(scores) / len(scores), 2)
        all_results[difficulty] = {"scores": scores, "average": avg}
        print(f"\n  [{difficulty.upper()}] Average: {avg:.2f}")
        print(f"  Failures: {failures}/{len(scores)}")

    print(f"\n{'='*50}")
    print("FINAL RESULTS SUMMARY")
    print(f"{'='*50}")
    for diff, data in all_results.items():
        print(f"  {diff:8s}: {data['average']:.2f}  (scores: {data['scores']})")


# -----------------------------
# ENTRYPOINT
# -----------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inference Script")
    parser.add_argument("--base-url", default="http://localhost:8000")
    args = parser.parse_args()

    asyncio.run(run_inference(args.base_url))

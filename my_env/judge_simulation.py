from openai import OpenAI
from .client import IncidentTriageEnv
from .models import TriageAction
import json, os
from openai import OpenAI
from .client import IncidentTriageEnv
from .models import TriageAction
import json, os

# 👇 ADD HERE
def safe_parse_action(raw):
    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        data = json.loads(raw[start:end])

        return TriageAction(
            severity=data.get("severity", "P3"),
            root_cause=data.get("root_cause"),
            assigned_team=data.get("assigned_team"),
            root_cause_alert=data.get("root_cause_alert"),
            priority_order=data.get("priority_order"),
            actions=data.get("actions"),
        )
    except Exception:
        return TriageAction(severity="P3")
    
MODEL_NAME = os.getenv("MODEL_NAME", "meta-llama/Llama-3.1-8B-Instruct")
client = OpenAI(
    base_url=os.getenv("API_BASE_URL", "https://router.huggingface.co/v1"),
    api_key=os.getenv("HF_TOKEN")
)

import asyncio

async def run_judge(base_url):
    print("🚀 Judge simulation started")
    results = {}

    for difficulty in ["easy", "medium", "hard"]:
        print(f"\n===== {difficulty.upper()} =====")
        scores = []

        for ep in range(5):
            print(f"Connecting → {difficulty} ep{ep}")

            async with IncidentTriageEnv(base_url=base_url) as env:
                print("✅ Connected")

                r = await env.reset(seed=ep, difficulty=difficulty)
                obs = r.observation

                prompt = f"""
You are an expert incident triage system.

Analyze the alerts, logs, and metrics carefully.

Return STRICT JSON with the following fields:

{{
  "severity": "P1 | P2 | P3 | P4",
  "root_cause": "short description",
  "assigned_team": "team name",
  "priority_order": ["alert_id1", "alert_id2"],
  "root_cause_alert": "alert_id",
  "actions": {{"alert_id": "action"}}
}}

IMPORTANT:
- Always include ALL fields
- Do not leave anything empty
- Be concise and accurate

ALERTS: {obs.alerts}
LOGS: {obs.logs}
METRICS: {obs.metrics}
"""

                try:
                    response = client.chat.completions.create(
                        model=MODEL_NAME,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.3,
                    )

                    raw = response.choices[0].message.content or ""

                    action = safe_parse_action(raw)

                except Exception as e:
                    print(f"ep{ep} failed → fallback ({e})")
                    action = TriageAction(severity="P3")

                result = await env.step(action)
                reward = result.reward or 0.0

                print(f"ep{ep}: {reward:.2f}")
                scores.append(reward)

        avg = sum(scores) / len(scores)
        results[difficulty] = avg
        print(f"AVG {difficulty}: {avg:.2f}")

    print("\nFINAL RESULTS:", results)


# ✅ ENTRYPOINT FIX
if __name__ == "__main__":
    asyncio.run(run_judge("http://localhost:8000"))
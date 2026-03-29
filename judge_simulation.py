
import json, os, random, asyncio
from openai import OpenAI

from client import IncidentTriageEnv
from models import TriageAction

# =========================
# SAFE PARSER (your original, slightly hardened)
# =========================
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


# =========================
# NOISE INJECTION (simulate bad LLMs)
# =========================
def inject_noise(raw):
    noise_type = random.choice([
        "none", "truncate", "extra_text", "invalid_json"
    ])

    if noise_type == "truncate":
        return raw[: len(raw)//2]

    if noise_type == "extra_text":
        return raw + "\nExplanation: possible infra degradation"

    if noise_type == "invalid_json":
        return raw.replace("{", "").replace("}", "")

    return raw


# =========================
# CLIENT SETUP
# =========================
MODEL_NAME = os.getenv("MODEL_NAME", "meta-llama/Llama-3.1-8B-Instruct")

client = OpenAI(
    base_url=os.getenv("API_BASE_URL", "https://router.huggingface.co/v1"),
    api_key=os.getenv("HF_TOKEN")
)


# =========================
# MAIN JUDGE RUNNER
# =========================
async def run_judge(base_url):
    print("🚀 Judge simulation started")
    results = {}

    for difficulty in ["easy", "medium", "hard"]:
        print(f"\n===== {difficulty.upper()} =====")
        scores = []

        for ep in range(5):
            print(f"\nConnecting → {difficulty} ep{ep}")

            async with IncidentTriageEnv(base_url=base_url) as env:
                print("✅ Connected")

                r = await env.reset(seed=ep, difficulty=difficulty)
                obs = r.observation

                prompt = f"""
You are an expert incident triage system.

Return STRICT JSON:

{{
  "severity": "P1 | P2 | P3 | P4",
  "root_cause": "short description",
  "assigned_team": "team name",
  "priority_order": ["alert_id1", "alert_id2"],
  "root_cause_alert": "alert_id",
  "actions": {{"alert_id": "action"}}
}}

IMPORTANT:
- Include ALL fields
- No empty values

ALERTS: {obs.alerts}
LOGS: {obs.logs}
METRICS: {obs.metrics}
"""

                try:
                    response = client.chat.completions.create(
                        model=MODEL_NAME,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=random.choice([0.0, 0.3, 0.7]),
                    )

                    raw = response.choices[0].message.content or ""

                    # 🔥 Inject noise (simulate bad model behavior)
                    raw = inject_noise(raw)

                    print(f"[RAW OUTPUT]: {raw[:200]}")

                    action = safe_parse_action(raw)

                    # =========================
                    # SIMULATE BAD AGENT OUTPUTS
                    # =========================

                    # Missing fields
                    if random.random() < 0.3:
                        action.root_cause = None

                    if random.random() < 0.3:
                        action.actions = None

                    # Wrong types
                    if random.random() < 0.2:
                        action.priority_order = "ABC"

                except Exception as e:
                    print(f"ep{ep} failed → fallback ({e})")
                    action = TriageAction(severity="P3")

                # =========================
                # ENV STEP
                # =========================
                try:
                    result = await env.step(action)
                    reward = result.reward or 0.0
                except Exception as e:
                    print(f"⚠️ ENV CRASH: {e}")
                    reward = 0.0

                print(f"ep{ep}: score={reward:.2f}")
                scores.append(reward)

        avg = sum(scores) / len(scores)
        results[difficulty] = round(avg, 2)

        print(f"\nAVG {difficulty}: {avg:.2f}")

    print("\n🔥 FINAL RESULTS:", results)


# =========================
# ENTRYPOINT
# =========================
if __name__ == "__main__":
    asyncio.run(run_judge("http://localhost:8000"))


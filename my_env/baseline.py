import os
import json
import argparse
import asyncio
from huggingface_hub import InferenceClient

import sys
sys.path.insert(0, os.path.dirname(__file__))
from client import IncidentTriageEnv
from models import TriageAction


def build_prompt(obs):
    """Build an LLM prompt from the observation."""
    alerts_text = ""
    for a in obs.alerts:
        alerts_text += f"\n  Alert {a['id']}: [{a['title']}] {a['message']}"

    logs_text = "\n  ".join(obs.logs) if obs.logs else "None"
    metrics_text = json.dumps(obs.metrics, indent=2) if obs.metrics else "None"
    difficulty = obs.task_difficulty

    prompt = f"""You are an expert on-call SRE engineer. Triage the following incident.

ALERTS:{alerts_text}

LOGS:
  {logs_text}

METRICS:
  {metrics_text}

AVAILABLE TEAMS: {', '.join(obs.available_teams)}
SEVERITY LEVELS: P1 (critical outage) > P2 (major degradation) > P3 (minor issue) > P4 (informational)

"""
    if difficulty == "easy":
        prompt += 'Respond with ONLY valid JSON, no explanation, no markdown:\n{"severity": "P1 or P2 or P3 or P4"}'
    elif difficulty == "medium":
        prompt += (
            'Respond with ONLY valid JSON, no explanation, no markdown:\n'
            '{"severity": "P1|P2|P3|P4", '
            '"root_cause": "short_snake_case_description", '
            '"assigned_team": "one of the available teams"}'
        )
    else:
        prompt += (
            'Respond with ONLY valid JSON, no explanation, no markdown:\n'
            '{"severity": "P1|P2|P3|P4", '
            '"root_cause_alert": "the alert ID (A/B/C) that is the root cause", '
            '"priority_order": ["alert_id", ...], '
            '"assigned_team": "one of the available teams", '
            '"actions": {"alert_id": "recommended_action", ...}}'
        )
    return prompt


def parse_json_response(text):
    """Extract JSON from model response robustly."""
    text = text.strip()
    # strip markdown fences if present
    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    # find first { and last }
    start = text.find("{")
    end = text.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError(f"No JSON found in response: {text}")
    return json.loads(text[start:end])


async def run_baseline(base_url, model="meta-llama/Llama-3.1-8B-Instruct"):
    """Run baseline across all 3 difficulties using HuggingFace Inference API."""
    hf_token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if not hf_token:
        # try huggingface_hub stored token
        try:
            from huggingface_hub import get_token
            hf_token = get_token()
        except Exception:
            pass

    if not hf_token:
        raise ValueError("No HuggingFace token found. Run: huggingface-cli login")

    api_client = InferenceClient(token=hf_token)
    all_results = {}

    for difficulty in ["easy", "medium", "hard"]:
        scores = []
        print(f"\n{'='*50}")
        print(f"  {difficulty.upper()} TASKS")
        print(f"{'='*50}")

        for ep in range(3):
            async with IncidentTriageEnv(base_url=base_url) as env:
                reset_result = await env.reset(seed=ep, difficulty=difficulty)
                obs = reset_result.observation

                prompt = build_prompt(obs)

                response = api_client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0,
                    max_tokens=300,
                )

                raw = response.choices[0].message.content
                try:
                    answer = parse_json_response(raw)
                except Exception as e:
                    print(f"  ep{ep}: JSON parse failed: {e} | raw: {raw[:100]}")
                    scores.append(0.0)
                    continue

                try:
                    action = TriageAction(**answer)
                except Exception as e:
                    print(f"  ep{ep}: TriageAction build failed: {e}")
                    scores.append(0.0)
                    continue

                step_result = await env.step(action)
                reward = step_result.observation.reward or 0.0
                scores.append(reward)
                print(
                    f"  ep{ep}: score={reward:.2f} "
                    f"| {step_result.observation.message[:80]}"
    )

        avg = sum(scores) / len(scores)
        all_results[difficulty] = {"scores": scores, "average": avg}
        print(f"\n  [{difficulty.upper()}] Average: {avg:.2f}")

    print(f"\n{'='*50}")
    print("BASELINE RESULTS SUMMARY")
    print(f"{'='*50}")
    for diff, data in all_results.items():
        print(f"  {diff:8s}: {data['average']:.2f}  (individual: {data['scores']})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Incident Triage Baseline")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--model", default="meta-llama/Llama-3.1-8B-Instruct")
    args = parser.parse_args()
    asyncio.run(run_baseline(args.base_url, args.model))

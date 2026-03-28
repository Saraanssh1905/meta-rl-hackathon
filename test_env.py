from my_env.client import IncidentTriageEnv
from my_env.models import TriageAction

BASE_URL = "http://127.0.0.1:8000"

with IncidentTriageEnv(base_url=BASE_URL).sync() as env:
    for difficulty in ["easy", "medium", "hard"]:
        print(f"\\n=== TESTING {difficulty.upper()} ===")

        r = env.reset(difficulty=difficulty)
        print("Task:", r.observation.task_id)
        print("Alerts:", r.observation.alerts)

        result = env.step(TriageAction(severity="P1"))  # temp action
        print("Reward:", result.reward)
        print("Feedback:", result.observation.message)
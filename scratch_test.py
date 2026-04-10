from server.environment import IncidentTriageEnvironment
from models import TriageAction

env = IncidentTriageEnvironment()

# Test hard difficulty
obs = env.reset(difficulty="hard", seed=42)
print("Scenario generated:", obs.alerts[0]["title"])
print("Is ID unique?", obs.task_id)

action = TriageAction(
    severity="P1",
    assigned_team=None,   # Tests the NameError
)

try:
    obs2 = env.step(action)
    print("Step 1 succeeded! Reward:", obs2.reward)
except Exception as e:
    print("Failed step 1!", e)

try:
    env.step(action)
    print("Step 2 succeeded! (Should not happen)")
except Exception as e:
    print("Step 2 failed cleanly as expected!", type(e), e)

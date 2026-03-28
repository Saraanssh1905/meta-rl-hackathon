import random
import uuid
from openenv.core.env_server import Environment

from server.scenarios import SCENARIOS, AVAILABLE_TEAMS

# import sys, os
# sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from models import TriageAction, TriageObservation, TriageState


# Class-level storage so state persists across requests
_sessions = {}


class IncidentTriageEnvironment(Environment):
    """IT incident triage environment for AI agent evaluation."""

    SUPPORTS_CONCURRENT_SESSIONS = True

    def __init__(self):
        self._session_id = None

    def _get_session(self):
        if self._session_id and self._session_id in _sessions:
            return _sessions[self._session_id]
        return {}

    def _set_session(self, data):
        if self._session_id:
            _sessions[self._session_id] = data

    def reset(self, seed=None, episode_id=None, **kwargs) -> TriageObservation:
        self._session_id = episode_id or str(uuid.uuid4())
        difficulty = kwargs.get("difficulty", "easy")
        scenarios = SCENARIOS.get(difficulty, SCENARIOS["easy"])

        if seed is not None:
            random.seed(seed)
        scenario = random.choice(scenarios)

        session_data = {
            "scenario": scenario,
            "difficulty": difficulty,
            "task_id": scenario["id"],
            "step_count": 0,
            "max_steps": 1,
        }
        self._set_session(session_data)

        return TriageObservation(
            done=False,
            reward=None,
            task_id=scenario["id"],
            task_difficulty=difficulty,
            alerts=scenario["alerts"],
            logs=scenario.get("logs", []),
            metrics=scenario.get("metrics", {}),
            message=(
                "You are the on-call engineer. Analyze the alert(s) "
                "and provide your triage decision. "
                f"Difficulty: {difficulty}"
            ),
            available_teams=AVAILABLE_TEAMS,
        )

    def step(self, action: TriageAction, **kwargs) -> TriageObservation:
        session = self._get_session()
        if not session:
            raise ValueError("No active session. Call reset() first.")

        session["step_count"] += 1
        scenario = session["scenario"]
        difficulty = session["difficulty"]
        correct = scenario["correct_answer"]

        reward, feedback = self._grade(action, correct, difficulty)
        self._set_session(session)

        return TriageObservation(
            done=True,
            reward=reward,
            task_id=session["task_id"],
            task_difficulty=difficulty,
            alerts=scenario["alerts"],
            logs=scenario.get("logs", []),
            metrics=scenario.get("metrics", {}),
            message=feedback,
            available_teams=AVAILABLE_TEAMS,
        )

    @property
    def state(self) -> TriageState:
        session = self._get_session()
        return TriageState(
            episode_id=self._session_id,
            step_count=session.get("step_count", 0),
            current_task=session.get("task_id", ""),
            current_difficulty=session.get("difficulty", ""),
            max_steps=session.get("max_steps", 1),
        )

    def _grade(self, action, correct, difficulty):
        if difficulty == "easy":
            return self._grade_easy(action, correct)
        elif difficulty == "medium":
            return self._grade_medium(action, correct)
        else:
            return self._grade_hard(action, correct)

    def _grade_easy(self, action, correct):
        agent = action.severity.upper().strip()
        answer = correct["severity"].upper()
        if agent == answer:
            return 1.0, f"Correct! Severity is {answer}."
        order = ["P1", "P2", "P3", "P4"]
        if agent in order and answer in order:
            diff = abs(order.index(agent) - order.index(answer))
            if diff == 1:
                return 0.5, f"Close — you said {agent}, correct was {answer}."
            if diff == 2:
                return 0.2, f"Off by 2 — you said {agent}, correct was {answer}."
        return 0.0, f"Wrong — you said {agent}, correct was {answer}."

    def _grade_medium(self, action, correct):
        score = 0.0
        fb = []
        agent_sev = action.severity.upper().strip()
        correct_sev = correct["severity"].upper()
        if agent_sev == correct_sev:
            score += 0.4
            fb.append(f"Severity: ✓ ({correct_sev})")
        else:
            order = ["P1", "P2", "P3", "P4"]
            if agent_sev in order and correct_sev in order:
                if abs(order.index(agent_sev) - order.index(correct_sev)) == 1:
                    score += 0.2
            fb.append(f"Severity: ✗ ({agent_sev} vs {correct_sev})")
        if action.root_cause:
            a = action.root_cause.lower().strip().replace(" ", "_")
            c = correct["root_cause"].lower().strip().replace(" ", "_")
            if a == c:
                score += 0.35
                fb.append("Root cause: ✓")
            elif c in a or a in c:
                score += 0.15
                fb.append(f"Root cause: partial ({c})")
            else:
                fb.append(f"Root cause: ✗ (expected {c})")
        else:
            fb.append("Root cause: not provided")
        if action.assigned_team:
            if action.assigned_team.lower().strip() == correct["assigned_team"].lower():
                score += 0.25
                fb.append("Team: ✓")
            else:
                fb.append(f"Team: ✗ ({action.assigned_team} vs {correct['assigned_team']})")
        else:
            fb.append("Team: not provided")
        return round(score, 2), " | ".join(fb)

    def _grade_hard(self, action, correct):
        score = 0.0
        fb = []
        if action.root_cause_alert:
            if action.root_cause_alert.upper() == correct["root_cause_alert"].upper():
                score += 0.30
                fb.append("Root cause alert: ✓")
            else:
                fb.append(f"Root cause alert: ✗ ({action.root_cause_alert} vs {correct['root_cause_alert']})")
        else:
            fb.append("Root cause alert: not provided")
        agent_sev = action.severity.upper().strip()
        correct_sev = correct["severity"].upper()
        if agent_sev == correct_sev:
            score += 0.20
            fb.append(f"Severity: ✓ ({correct_sev})")
        else:
            fb.append(f"Severity: ✗ ({agent_sev} vs {correct_sev})")
        if action.priority_order:
            co = [x.upper() for x in correct["priority_order"]]
            ao = [x.upper() for x in action.priority_order]
            if ao == co:
                score += 0.25
                fb.append("Priority: ✓")
            elif len(ao) > 0 and ao[0] == co[0]:
                score += 0.10
                fb.append("Priority: first correct only")
            else:
                fb.append("Priority: ✗")
        else:
            fb.append("Priority: not provided")
        if action.assigned_team:
            if action.assigned_team.lower().strip() == correct.get("assigned_team", "").lower():
                score += 0.10
                fb.append("Team: ✓")
            else:
                fb.append(f"Team: ✗ ({action.assigned_team} vs {correct.get('assigned_team')})")
        else:
            fb.append("Team: not provided")
        if action.actions and correct.get("actions"):
            ca = correct["actions"]
            matches = 0
            for alert_id, correct_act in ca.items():
                agent_act = action.actions.get(alert_id, "")
                cwords = set(correct_act.lower().replace("_", " ").split())
                awords = set(agent_act.lower().replace("_", " ").split())
                if len(cwords & awords) >= len(cwords) * 0.5:
                    matches += 1
            score += (matches / len(ca)) * 0.15
            fb.append(f"Actions: {matches}/{len(ca)}")
        else:
            fb.append("Actions: not provided")
        return round(score, 2), " | ".join(fb)
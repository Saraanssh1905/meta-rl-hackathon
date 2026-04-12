import random
import time
import uuid
from openenv.core.env_server import Environment

from server.scenarios import SCENARIOS, AVAILABLE_TEAMS


from models import TriageAction, TriageObservation, TriageState

def fuzzy_match(pred, expected):
    if not pred or not expected:
        return False

    pred = pred.lower().replace("_", " ")
    expected = expected.lower().replace("_", " ")

    # direct match
    
    if expected in pred or pred in expected:
        return True

    # synonyms

    SYNONYMS = {
    "database": ["db", "connection pool", "query overload", "db exhaustion"],
    "waf": ["firewall", "geoip", "blocked traffic"],
    "cpu": ["high cpu", "cpu spike", "resource exhaustion"],
    "latency": ["slow", "delay", "timeout"],
    "memory": ["ram", "memory leak", "oom"],
}

    for key, vals in SYNONYMS.items():
        if key in expected:
            if any(v in pred for v in vals):
                return True

    # Explicit string matching required - removed aggressive keyword overlap
    return False

# Class-level storage so state persists across requests
_sessions = {}
SESSION_TTL = 300  # 5 minutes

def _cleanup_sessions():
    """Remove expired sessions to prevent memory leaks under load."""
    now = time.time()
    expired = [k for k, v in _sessions.items() if now - v.get("created_at", now) > SESSION_TTL]
    for k in expired:
        del _sessions[k]


class IncidentTriageEnvironment(Environment):
    """IT incident triage environment for AI agent evaluation."""

    SUPPORTS_CONCURRENT_SESSIONS = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._session_id = None

    def _get_session(self):
        if self._session_id and self._session_id in _sessions:
            return _sessions[self._session_id]
        return {}

    def _set_session(self, data):
        _cleanup_sessions()
        if self._session_id:
            if "created_at" not in data:
                data["created_at"] = time.time()
            _sessions[self._session_id] = data

    def reset(self, seed=None, episode_id=None, **kwargs) -> TriageObservation:
        self._session_id = episode_id or str(uuid.uuid4())
        difficulty = kwargs.get("difficulty", "easy")
        scenarios = SCENARIOS.get(difficulty, SCENARIOS["easy"])

        from server.scenarios import apply_dynamic_layer

        rng = random.Random(seed) if seed is not None else random
        scenario_template = rng.choice(scenarios)
        scenario = apply_dynamic_layer(scenario_template, rng)

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
        if session.get("done"):
            raise ValueError("Episode already finished")

        session["step_count"] += 1
        scenario = session["scenario"]
        difficulty = session["difficulty"]
        correct = scenario["correct_answer"]

        # SAFE ATTRIBUTE ACCESS (VERY IMPORTANT)

        if not getattr(action, "severity", None):
            action.severity = "P3"

        if not getattr(action, "assigned_team", None):
            action.assigned_team = "unknown"

        if not getattr(action, "root_cause", None):
            action.root_cause = "unknown issue"

        if not getattr(action, "priority_order", None):
            action.priority_order = []

        if not getattr(action, "actions", None):
            action.actions = {}

        if not getattr(action, "root_cause_alert", None):
            action.root_cause_alert = ""

        # INPUT SANITIZATION

        # Fix severity

        if action.severity not in ["P1", "P2", "P3", "P4"]:
            action.severity = "P3"

        # Fix priority_order

        if not isinstance(action.priority_order, list):
            action.priority_order = []

        # Fix actions

        if not isinstance(action.actions, dict):
            action.actions = {}

        # Normalize team names

        team = action.assigned_team.lower() if action.assigned_team else ""

        TEAM_MAP = {
        "infrastructure team": "infra",
        "devops": "infra",
        "security team": "security",
        "backend team": "backend",
        "database team": "database"
    }

        action.assigned_team = TEAM_MAP.get(team, team)
    
        reward, feedback = self._grade(action, correct, difficulty)

        # Penalty for missing root cause

        if action.root_cause.lower() in ["unknown issue","unknown",""]:
            reward -= 0.05
        if action.assigned_team.lower() in ["unknown", ""]:
            reward -= 0.03
        if action.severity.upper() not in ["P1", "P2", "P3", "P4"]:
            reward -= 0.05
        if difficulty == "hard" and not action.actions:
            reward -= 0.05
        if reward is None:
            reward = 0.0

        #   Preventing negative or >1 scores

        reward = max(0.0, min(1.0, reward))

        
        feedback = f"Score: {reward} | {feedback}"

        session["done"] = True
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
                return 0.7, f"Close  you said {agent}, correct was {answer}."

            if diff == 2:
                return 0.4, f"Off by 2  you said {agent}, correct was {answer}."

        return 0.1, f"Wrong  you said {agent}, correct was {answer}."

    def _grade_medium(self, action, correct):
        
        score = 0.0
        fb = []
        agent_sev = action.severity.upper().strip()
        correct_sev = correct["severity"].upper()
        if agent_sev == correct_sev:
            score += 0.4
            fb.append(f"Severity:  ({correct_sev})")
        else:
            order = ["P1", "P2", "P3", "P4"]
            if agent_sev in order and correct_sev in order:
                if abs(order.index(agent_sev) - order.index(correct_sev)) == 1:
                    score += 0.2
            fb.append(f"Severity:  ({agent_sev} vs {correct_sev})")
        if action.root_cause:
            if fuzzy_match(action.root_cause, correct["root_cause"]):
                score += 0.35
                fb.append("Root cause: ")
            else:
            # PARTIAL MATCH
                target_words = correct["root_cause"].split("_")
                match_count = sum(1 for word in target_words if len(word) > 3 and word in action.root_cause.lower())
                if match_count >= max(2, len(target_words) // 2):
                    score += 0.20
                    fb.append("Root cause: partial (matched keywords)")
                else:
                    fb.append(f"Root cause:  (expected {correct['root_cause']})")
        else:
            fb.append("Root cause: not provided")
        if action.assigned_team:
            if fuzzy_match(action.assigned_team, correct["assigned_team"]):
                score += 0.25
                fb.append("Team: ")
            else:
                fb.append(f"Team:  ({action.assigned_team} vs {correct['assigned_team']})")
        else:
            fb.append("Team: not provided")
        return round(score, 2), " | ".join(fb)

    def _grade_hard(self, action, correct):
        score = 0.0
        fb = []
        if action.root_cause_alert:
            agent_root = action.root_cause_alert.upper()
            correct_root = correct["root_cause_alert"].upper()

            if fuzzy_match(agent_root, correct_root):
                score += 0.30
            elif any(word in agent_root.lower() for word in correct_root.lower().split("_")):
                score += 0.15
            else:
                fb.append("")
        else:
            fb.append("Root cause alert: not provided")

        agent_sev = action.severity.upper().strip()
        correct_sev = correct["severity"].upper()

        order = ["P1", "P2", "P3", "P4"]

        if agent_sev == correct_sev:
            score += 0.20
            fb.append(f"Severity:  ({correct_sev})")
        elif agent_sev in order and correct_sev in order:
            diff = abs(order.index(agent_sev) - order.index(correct_sev))
            if diff == 1:
                score += 0.10
                fb.append(f"Severity: close ({agent_sev} vs {correct_sev})")
            elif diff == 2:
                score += 0.05
                fb.append(f"Severity: slightly off ({agent_sev} vs {correct_sev})")
            else:
                fb.append(f"Severity:  ({agent_sev} vs {correct_sev})")
        else:
            fb.append(f"Severity: invalid ({agent_sev})")
        if action.priority_order:
            co = [x.upper() for x in correct["priority_order"]]
            ao = [x.upper() for x in action.priority_order]
            # Position-aware scoring: reward correct items in correct positions
            positional_matches = sum(1 for a, c in zip(ao, co) if a == c)
            first_correct = 1 if (ao and co and ao[0] == co[0]) else 0

            # 60% weight on positional accuracy, 40% on getting root cause first
            pos_score = (positional_matches / len(co)) * 0.60
            first_score = first_correct * 0.40
            priority_reward = (pos_score + first_score) * 0.25
            score += priority_reward

            if positional_matches == len(co):
                fb.append("Priority: correct (exact order)")
            elif first_correct:
                fb.append(f"Priority: partial (root cause correct, {positional_matches}/{len(co)} positions)")
            elif positional_matches > 0:
                fb.append(f"Priority: partial ({positional_matches}/{len(co)} positions, wrong root cause first)")
            else:
                fb.append("Priority: ")
        else:
            fb.append("Priority: not provided")
        if action.assigned_team:
            agent_team = action.assigned_team.lower().strip()
            correct_team = correct.get("assigned_team", "").lower()

            if fuzzy_match(agent_team, correct_team):
                score += 0.10
                fb.append("Team: ")
            elif agent_team in correct_team or correct_team in agent_team:
                score += 0.05
                fb.append("Team: partial")
            else:
                fb.append(f"Team:  ({agent_team} vs {correct_team})")
        else:
            fb.append("Team: not provided")
        if action.actions and correct.get("actions"):
            ca = correct["actions"]
            matches = 0
            for alert_id, correct_act in ca.items():
                agent_act = action.actions.get(alert_id, "")
                cwords = set(correct_act.lower().replace("_", " ").split())
                awords = set(agent_act.lower().replace("_", " ").split())
                if len(cwords & awords) >= max(2, int(len(cwords) * 0.6)):
                    matches += 1
            score += (matches / len(ca)) * 0.15
            fb.append(f"Actions: {matches}/{len(ca)}")
        else:
            fb.append("Actions: not provided")
        return round(score, 2), " | ".join(fb)
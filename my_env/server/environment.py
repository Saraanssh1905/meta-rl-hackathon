import random
import uuid
from openenv.core.env_server import Environment

from .scenarios import SCENARIOS, AVAILABLE_TEAMS

# models.py is in parent directory; adjust import based on how server runs
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from models import TriageAction, TriageObservation, TriageState


class IncidentTriageEnvironment(Environment):
    """IT incident triage environment for AI agent evaluation."""

    SUPPORTS_CONCURRENT_SESSIONS = True

    def __init__(self):
        self._state = TriageState()
        self._scenario = None
        self._difficulty = "easy"
        self._task_id = None

    # ── OpenEnv interface ──────────────────────────────────

    def reset(self, seed=None, episode_id=None, **kwargs) -> TriageObservation:
        self._difficulty = kwargs.get("difficulty", "easy")
        scenarios = SCENARIOS.get(self._difficulty, SCENARIOS["easy"])

        if seed is not None:
            random.seed(seed)
        self._scenario = random.choice(scenarios)
        self._task_id = self._scenario["id"]

        self._state = TriageState(
            episode_id=episode_id or str(uuid.uuid4()),
            step_count=0,
            current_task=self._task_id,
            current_difficulty=self._difficulty,
            max_steps=1,
        )

        return TriageObservation(
            done=False,
            reward=None,
            task_id=self._task_id,
            task_difficulty=self._difficulty,
            alerts=self._scenario["alerts"],
            logs=self._scenario.get("logs", []),
            metrics=self._scenario.get("metrics", {}),
            message=(
                "You are the on-call engineer. Analyze the alert(s) "
                "and provide your triage decision. "
                f"Difficulty: {self._difficulty}"
            ),
            available_teams=AVAILABLE_TEAMS,
        )

    def step(self, action: TriageAction, **kwargs) -> TriageObservation:
        self._state.step_count += 1
        correct = self._scenario["correct_answer"]
        reward, feedback = self._grade(action, correct)

        return TriageObservation(
            done=True,
            reward=reward,
            task_id=self._task_id,
            task_difficulty=self._difficulty,
            alerts=self._scenario["alerts"],
            logs=self._scenario.get("logs", []),
            metrics=self._scenario.get("metrics", {}),
            message=feedback,
            available_teams=AVAILABLE_TEAMS,
        )

    @property
    def state(self) -> TriageState:
        return self._state

    # ── Grading ────────────────────────────────────────────

    def _grade(self, action, correct):
        if self._difficulty == "easy":
            return self._grade_easy(action, correct)
        elif self._difficulty == "medium":
            return self._grade_medium(action, correct)
        else:
            return self._grade_hard(action, correct)

    def _grade_easy(self, action, correct):
        """Severity only → 1.0 / 0.5 / 0.2 / 0.0"""
        agent = (action.severity or "").upper().strip()
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
        """Severity 40% + root cause 35% + team 25%"""
        score = 0.0
        fb = []

        # — Severity (40%) —
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

        # — Root cause (35%) —
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

        # — Team (25%) —
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
        """Root cause alert 30% + severity 20% + priority 25% + team 10% + actions 15%"""
        score = 0.0
        fb = []

        # — Root cause alert (30%) —
        if action.root_cause_alert:
            if action.root_cause_alert.upper() == correct["root_cause_alert"].upper():
                score += 0.30
                fb.append("Root cause alert: ✓")
            else:
                fb.append(
                    f"Root cause alert: ✗ "
                    f"({action.root_cause_alert} vs {correct['root_cause_alert']})"
                )
        else:
            fb.append("Root cause alert: not provided")

        # — Severity (20%) —
        agent_sev = action.severity.upper().strip()
        correct_sev = correct["severity"].upper()
        if agent_sev == correct_sev:
            score += 0.20
            fb.append(f"Severity: ✓ ({correct_sev})")
        else:
            fb.append(f"Severity: ✗ ({agent_sev} vs {correct_sev})")

        # — Priority order (25%) —
        if action.priority_order:
            co = [x.upper() for x in correct["priority_order"]]
            ao = [x.upper() for x in action.priority_order]
            if ao == co:
                score += 0.25
                fb.append("Priority: ✓")
            elif len(ao) > 0 and len(co) > 0 and ao[0] == co[0]:
                score += 0.10
                fb.append("Priority: first correct only")
            else:
                fb.append("Priority: ✗")
        else:
            fb.append("Priority: not provided")

        # — Team (10%) —
        if action.assigned_team:
            if action.assigned_team.lower().strip() == correct.get("assigned_team", "").lower():
                score += 0.10
                fb.append("Team: ✓")
            else:
                fb.append(f"Team: ✗ ({action.assigned_team} vs {correct.get('assigned_team')})")
        else:
            fb.append("Team: not provided")

        # — Actions (15%) —
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

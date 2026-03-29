from openenv.core.env_client import EnvClient
from openenv.core.client_types import StepResult
from models import TriageAction, TriageObservation, TriageState


class IncidentTriageEnv(EnvClient[TriageAction, TriageObservation, TriageState]):
    """Client for the Incident Triage environment."""

    def _step_payload(self, action: TriageAction) -> dict:
        payload = {"severity": action.severity}
        if action.root_cause is not None:
            payload["root_cause"] = action.root_cause
        if action.assigned_team is not None:
            payload["assigned_team"] = action.assigned_team
        if action.root_cause_alert is not None:
            payload["root_cause_alert"] = action.root_cause_alert
        if action.priority_order is not None:
            payload["priority_order"] = action.priority_order
        if action.actions is not None:
            payload["actions"] = action.actions
        return payload

    def _parse_result(self, payload: dict) -> StepResult:
        obs = payload.get("observation", {})
        return StepResult(
            observation=TriageObservation(
                done=payload.get("done", False),
                reward=payload.get("reward"),
                task_id=obs.get("task_id", ""),
                task_difficulty=obs.get("task_difficulty", ""),
                alerts=obs.get("alerts", []),
                logs=obs.get("logs", []),
                metrics=obs.get("metrics", {}),
                message=obs.get("message", ""),
                available_teams=obs.get("available_teams", []),
            ),
            reward=payload.get("reward"),
            done=payload.get("done", False),
        )

    def _parse_state(self, payload: dict) -> TriageState:
        return TriageState(
            episode_id=payload.get("episode_id"),
            step_count=payload.get("step_count", 0),
            current_task=payload.get("current_task", ""),
            current_difficulty=payload.get("current_difficulty", ""),
            max_steps=payload.get("max_steps", 1),
        )

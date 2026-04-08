from typing import List, Optional, Dict
from openenv.core.env_server import Action, Observation, State
class TriageAction(Action):
    """The agent's triage decision."""
    severity: str                                    # "P1", "P2", "P3", or "P4"
    root_cause: Optional[str] = None                 # e.g. "database_connection_pool_exhaustion"
    assigned_team: Optional[str] = None              # e.g. "database", "backend", "security"
    root_cause_alert: Optional[str] = None           # which alert ID is the root cause (hard)
    priority_order: Optional[List[str]] = None       # order to address alerts (hard)
    actions: Optional[Dict[str, str]] = None         # alert_id  recommended action (hard)

    class Config:
        extra="allow"
class TriageObservation(Observation):
    """What the agent sees  alert data + feedback."""
    # done: bool and reward: Optional[float] inherited from Observation
    task_id: str = ""
    task_difficulty: str = ""                        # "easy", "medium", "hard"
    alerts: List[Dict[str, str]] = []                # list of alert objects
    logs: List[str] = []                             # relevant log lines
    metrics: Dict[str, str] = {}                     # system metrics
    message: str = ""                                # feedback / instructions
    available_teams: List[str] = []
    available_severities: List[str] = ["P1", "P2", "P3", "P4"]
class TriageState(State):
    """Internal episode metadata."""
    # episode_id: Optional[str] and step_count: int inherited from State
    current_task: str = ""
    current_difficulty: str = ""
    max_steps: int = 1
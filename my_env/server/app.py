from openenv.core.env_server import create_fastapi_app
from server.environment import IncidentTriageEnvironment
from models import TriageAction, TriageObservation
app = create_fastapi_app(IncidentTriageEnvironment, TriageAction, TriageObservation)
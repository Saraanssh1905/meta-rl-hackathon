from openenv.core.env_server import create_fastapi_app
from server.environment import IncidentTriageEnvironment
from models import TriageAction, TriageObservation
from fastapi.responses import RedirectResponse

app = create_fastapi_app(
    IncidentTriageEnvironment,
    TriageAction,
    TriageObservation
)

@app.get("/")
async def root():
    return {
        "environment": "Incident Triage & Escalation",
        "status": "running",
        "docs": "/docs",
        "tasks": ["easy (6 scenarios)", "medium (4 scenarios)", "hard (3 scenarios)"],
        "version": "1.0.0"
    }

#  Used by OpenEnv
def main():
    return app

#  Used for CLI / python execution
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server.app:app", host="0.0.0.0", port=8000)
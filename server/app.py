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
    return RedirectResponse(url="/docs")

#  Used by OpenEnv
def main():
    return app

#  Used for CLI / python execution
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server.app:app", host="0.0.0.0", port=8000)
from openenv.core.env_server import create_fastapi_app
from server.environment import IncidentTriageEnvironment
from models import TriageAction, TriageObservation

app = create_fastapi_app(
    IncidentTriageEnvironment,
    TriageAction,
    TriageObservation
)
from fastapi.responses import RedirectResponse

@app.get("/")
def root():
    return RedirectResponse(url="/docs")
def main():
    import uvicorn
    uvicorn.run("server.app:app", host="0.0.0.0", port=7860)

if __name__ == "__main__":
    main()
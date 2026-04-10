from openenv.core.env_server import create_fastapi_app
from server.environment import IncidentTriageEnvironment
from models import TriageAction, TriageObservation
from fastapi.responses import RedirectResponse

app = create_fastapi_app(
    IncidentTriageEnvironment,
    TriageAction,
    TriageObservation
)

from fastapi.openapi.docs import get_swagger_ui_html

@app.get("/")
def root():
    return get_swagger_ui_html(openapi_url="/openapi.json", title="API Docs")

#  Used by OpenEnv
def main():
    return app

#  Used for CLI / python execution
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server.app:app", host="0.0.0.0", port=7860)
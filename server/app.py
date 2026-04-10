from openenv.core.env_server import create_fastapi_app
from server.environment import IncidentTriageEnvironment
from models import TriageAction, TriageObservation
from fastapi.responses import RedirectResponse

app = create_fastapi_app(
    IncidentTriageEnvironment,
    TriageAction,
    TriageObservation
)

from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import HTMLResponse

class IframeDocsRedirectMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # Intercept the root path before any default HF or OpenEnv routers get it
        if request.url.path == "/":
            html_content = '<!DOCTYPE html><html><head><meta http-equiv="refresh" content="0; url=docs" /></head><body></body></html>'
            return HTMLResponse(content=html_content)
        return await call_next(request)

app.add_middleware(IframeDocsRedirectMiddleware)

#  Used by OpenEnv
def main():
    return app

#  Used for CLI / python execution
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server.app:app", host="0.0.0.0", port=8000)
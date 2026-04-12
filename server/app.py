from openenv.core.env_server import create_fastapi_app
from server.environment import IncidentTriageEnvironment
from models import TriageAction, TriageObservation
from fastapi.responses import HTMLResponse

app = create_fastapi_app(
    IncidentTriageEnvironment,
    TriageAction,
    TriageObservation
)

@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Incident Triage Environment</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                   background: #0d1117; color: #c9d1d9; padding: 40px; line-height: 1.6; }
            h1 { color: #f0f6fc; font-size: 2em; margin-bottom: 4px; }
            h2 { color: #f0f6fc; font-size: 1.3em; margin: 28px 0 12px; }
            .badge { display: inline-block; padding: 2px 8px; border-radius: 4px;
                     font-size: 0.75em; font-weight: 600; margin-left: 8px; }
            .version { background: #238636; color: white; }
            .spec { background: #1f6feb; color: white; }
            .subtitle { color: #8b949e; font-size: 0.9em; margin-bottom: 24px; }
            .subtitle a { color: #58a6ff; }
            p { color: #8b949e; margin-bottom: 16px; }
            ul { list-style: disc; padding-left: 24px; margin-bottom: 16px; }
            ol { padding-left: 24px; margin-bottom: 16px; }
            li { margin-bottom: 6px; color: #c9d1d9; }
            strong { color: #f0f6fc; }
            code { background: #161b22; padding: 2px 6px; border-radius: 4px;
                   font-family: 'SFMono-Regular', Consolas, monospace; color: #f85149; font-size: 0.9em; }
            a { color: #58a6ff; text-decoration: none; }
            a:hover { text-decoration: underline; }
            hr { border: none; border-top: 1px solid #21262d; margin: 24px 0; }
            .container { max-width: 800px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>OpenEnv Environment HTTP API
                <span class="badge version">1.0.0</span>
                <span class="badge spec">OAS 3.1</span>
            </h1>
            <p class="subtitle"><a href="/openapi.json">/openapi.json</a></p>

            <h2>OpenEnv Environment HTTP API</h2>
            <p>HTTP API for interacting with OpenEnv environments through a standardized interface.</p>

            <h2>Features</h2>
            <ul>
                <li><strong>Environment Reset</strong>: Initialize or restart episodes</li>
                <li><strong>Action Execution</strong>: Send actions and receive observations</li>
                <li><strong>State Inspection</strong>: Query current environment state</li>
                <li><strong>Schema Access</strong>: Retrieve JSON schemas for actions and observations</li>
            </ul>

            <h2>Workflow</h2>
            <ol>
                <li>Call <code>/reset</code> to start a new episode and get initial observation</li>
                <li>Call <code>/step</code> repeatedly with actions to interact with environment</li>
                <li>Episode ends when observation returns <code>done: true</code></li>
                <li>Call <code>/state</code> anytime to inspect current environment state</li>
            </ol>

            <h2>Documentation</h2>
            <ul>
                <li><strong>Swagger UI</strong>: Available at <a href="/docs"><code>/docs</code></a></li>
                <li><strong>ReDoc</strong>: Available at <a href="/redoc"><code>/redoc</code></a></li>
                <li><strong>OpenAPI Schema</strong>: Available at <a href="/openapi.json"><code>/openapi.json</code></a></li>
            </ul>

            <hr>
            <a href="https://github.com/openenv" style="color: #8b949e;">OpenEnv Team - Website</a>
        </div>
    </body>
    </html>
    """

#  Used by OpenEnv
def main():
    return app

#  Used for CLI / python execution
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server.app:app", host="0.0.0.0", port=8000)
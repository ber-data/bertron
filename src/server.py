from fastapi import FastAPI
import uvicorn
from fastapi.responses import RedirectResponse

app = FastAPI()


@app.get("/", include_in_schema=False)
def get_root():
    r"""Redirect to the API documentation page."""
    return RedirectResponse(url="/docs")


@app.get("/health")
def get_health():
    r"""Get API health information."""
    return {"web_server": "ok", "database": None}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

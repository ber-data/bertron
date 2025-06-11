from fastapi import FastAPI
import uvicorn
from fastapi.responses import RedirectResponse
from pymongo import MongoClient

# Connect to MongoDB.
# TODO: Get these values from environment variables instead of hard-coding them.
mongo_client = MongoClient("mongo:27017", username="admin", password="root")

app = FastAPI()


@app.get("/", include_in_schema=False)
def get_root():
    r"""Redirect to the API documentation page."""
    return RedirectResponse(url="/docs")


@app.get("/health")
def get_health():
    r"""Get API health information."""
    is_database_healthy = len(mongo_client.list_database_names()) > 0
    return {"web_server": "ok", "database": is_database_healthy}


# TODO: Delete this endpoint once we're confident in our database connection.
@app.get("/experimental/database_names")
def get_database_names():
    r"""Get the names of all databases in the MongoDB server."""
    db_names = mongo_client.list_database_names()
    return {"database_names": db_names}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

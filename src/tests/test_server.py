r"""
This file contains tests targeting `src/server.py`.

You can learn about testing FastAPI apps here:
https://fastapi.tiangolo.com/tutorial/testing/
"""

from fastapi.testclient import TestClient
from starlette import status
from server import app


def test_root_endpoint_redirects_to_api_docs():
    client = TestClient(app)
    response = client.get("/", follow_redirects=False)
    assert response.status_code == status.HTTP_307_TEMPORARY_REDIRECT
    assert response.headers["location"] == "/docs"

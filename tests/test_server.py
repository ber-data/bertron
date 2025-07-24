r"""
This file contains tests targeting `src/server.py`.

You can learn about testing FastAPI apps here:
https://fastapi.tiangolo.com/tutorial/testing/
"""

import pytest
from fastapi.testclient import TestClient
from starlette import status

from src.models import HealthResponse, VersionResponse
from src.server import app


@pytest.fixture
def test_client():
    test_client = TestClient(app)
    yield test_client


def test_root_endpoint_redirects_to_api_docs(test_client: TestClient):
    response = test_client.get("/", follow_redirects=False)
    assert response.status_code == status.HTTP_307_TEMPORARY_REDIRECT
    assert response.headers["location"] == "/docs"


def test_version_endpoint_returns_version_response(test_client: TestClient):
    response = test_client.get("/version")
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    # Note: This will raise a `ValidationError` if the response is not
    #       a valid `VersionResponse` (e.g. if it has extra fields or
    #       its fields' values are of an incompatible data type).
    _ = VersionResponse(**body)


def test_health_endpoint_returns_health_response(test_client: TestClient):
    response = test_client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["web_server"] is True
    assert body["database"] is True
    _ = HealthResponse(**body)

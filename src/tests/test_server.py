r"""
This file contains tests targeting `src/server.py`.

You can learn about testing FastAPI apps here:
https://fastapi.tiangolo.com/tutorial/testing/
"""

import pytest
from fastapi.testclient import TestClient
from starlette import status

from models import VersionResponse
from server import app


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
    json_response = response.json()
    expected_fields = set(VersionResponse.model_fields.keys())
    actual_fields = set(json_response.keys())
    assert actual_fields == expected_fields

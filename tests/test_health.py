import pytest
import requests


def test_health_endpoint():
    """Test the health endpoint returns correct status and structure."""
    # Assuming the API server is running on localhost:8000
    # Adjust the URL if your server runs on a different host/port
    base_url = "http://app:8000"
    
    response = requests.get(f"{base_url}/health")
    
    # Check that the request was successful
    assert response.status_code == 200
    
    # Parse the JSON response
    health_data = response.json()
    
    # Verify the response structure matches HealthResponse model
    assert "web_server" in health_data
    assert "database" in health_data
    
    # Verify data types
    assert isinstance(health_data["web_server"], bool)
    assert isinstance(health_data["database"], bool)
    
    # Since the API server is running, web_server should always be True
    assert health_data["web_server"] is True
    
    # Since MongoDB is running, database should be True
    # This tests the actual database connectivity
    assert health_data["database"] is True
    
    # Verify response headers
    assert response.headers["content-type"] == "application/json"
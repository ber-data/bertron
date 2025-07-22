from typing import Dict, Any

from fastapi.testclient import TestClient
import pytest
from starlette import status

from src.server import app


@pytest.fixture
def test_client():
    test_client = TestClient(app)
    yield test_client


class TestBertronAPI:
    r"""
    Test suite for BERtron API endpoints assuming data is loaded.

    TODO: Remove prerequisite of data having been loaded by the `ingest` script.
          Instead, implement a sufficient fixture within the test suite.
    """

    def test_get_all_entities(self, test_client: TestClient):
        """Test getting all entities from the collection."""
        response = test_client.get("/bertron")
        
        assert response.status_code == status.HTTP_200_OK
        entities_data = response.json()
        
        # Verify response structure matches EntitiesResponse
        assert "documents" in entities_data
        assert "count" in entities_data
        
        # Verify data types
        assert isinstance(entities_data["documents"], list)
        assert isinstance(entities_data["count"], int)
        
        # Count should match the length of documents
        assert entities_data["count"] == len(entities_data["documents"])
        
        # If we have entities, verify structure of first entity
        if entities_data["count"] > 0:
            entity = entities_data["documents"][0]
            self._verify_entity_structure(entity)

    def test_get_entity_by_id_emsl(self, test_client: TestClient):
        """Test getting a specific EMSL entity by ID."""
        entity_id = "EMSL:c9405190-e962-4ba5-93f0-e3ff499f4488"
        response = test_client.get(f"/bertron/{entity_id}")
        
        assert response.status_code == status.HTTP_200_OK
        entity = response.json()
        
        # Verify this is the correct entity
        assert entity["id"] == entity_id
        assert entity["ber_data_source"] == "EMSL"
        assert entity["name"] == "EMSL Sample c9405190-e962-4ba5-93f0-e3ff499f4488"
        assert entity["description"] == "Clostridium thermocellum protein extracts"
        
        # Verify coordinates
        assert entity["coordinates"]["latitude"] == 34
        assert entity["coordinates"]["longitude"] == 118.0
        
        self._verify_entity_structure(entity)

    # TODO: Consider using URL encoding (a.k.a. "percent-encoding") for the slashes.
    def test_get_entity_by_id_ess_dive(self, test_client: TestClient):
        """Test getting a specific ESS-DIVE entity by ID."""
        entity_id = "doi:10.15485/2441497"
        response = test_client.get(f"/bertron/{entity_id}")
        
        assert response.status_code == status.HTTP_200_OK
        entity = response.json()
        
        # Verify this is the correct entity
        assert entity["id"] == entity_id
        assert entity["ber_data_source"] == "ESS-DIVE"
        assert "NGEE Arctic" in entity["name"]
        
        self._verify_entity_structure(entity)

    def test_get_entity_by_id_nmdc(self, test_client: TestClient):
        """Test getting a specific NMDC entity by ID."""
        entity_id = "nmdc:bsm-11-bsf8yq62"
        response = test_client.get(f"/bertron/{entity_id}")
        
        assert response.status_code == status.HTTP_200_OK
        entity = response.json()
        
        # Verify this is the correct entity
        assert entity["id"] == entity_id
        assert entity["ber_data_source"] == "NMDC"
        assert entity["name"] == "DSNY_CoreB_TOP"
        assert entity["description"] == "MONet sample represented in NMDC"
        
        # Verify coordinates with depth and elevation
        assert entity["coordinates"]["latitude"] == 28.125842
        assert entity["coordinates"]["longitude"] == -81.434174
        assert entity["coordinates"]["depth"] is not None
        assert entity["coordinates"]["elevation"] is not None
        
        self._verify_entity_structure(entity)

    def test_get_entity_by_id_not_found(self, test_client: TestClient):
        """Test getting a non-existent entity returns 404."""
        entity_id = "nonexistent:12345"
        response = test_client.get(f"/bertron/{entity_id}")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        error_data = response.json()
        assert "not found" in error_data["detail"].lower()

    def test_find_entities_with_filter(self, test_client: TestClient):
        """Test finding entities with MongoDB filter."""
        query = {
            "filter": {"ber_data_source": "EMSL"},
            "limit": 10
        }
        
        response = test_client.post(
            "/bertron/find",
            json=query,
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 200
        entities_data = response.json()
        
        assert "documents" in entities_data
        assert "count" in entities_data
        assert isinstance(entities_data["documents"], list)
        assert isinstance(entities_data["count"], int)
        
        # All returned entities should be from EMSL
        for entity in entities_data["documents"]:
            assert entity["ber_data_source"] == "EMSL"
            self._verify_entity_structure(entity)

    def test_find_entities_with_projection(self, test_client: TestClient):
        """Test finding entities with field projection."""
        query = {
            "filter": {},
            "projection": {"id": 1, "name": 1, "ber_data_source": 1},
            "limit": 5
        }
        
        response = test_client.post(
            "/bertron/find",
            json=query,
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        entities_data = response.json()
        
        assert entities_data["count"] <= 5
        
        # Verify projected fields are present
        for entity in entities_data["documents"]:
            assert "id" in entity
            assert "name" in entity
            assert "ber_data_source" in entity

    def test_find_entities_with_sort_and_limit(self, test_client: TestClient):
        """Test finding entities with sorting and limiting."""
        query = {
            "filter": {},
            "sort": {"ber_data_source": 1, "id": 1},
            "limit": 3
        }
        
        response = test_client.post(
            "/bertron/find",
            json=query,
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        entities_data = response.json()
        
        assert entities_data["count"] <= 3
        assert len(entities_data["documents"]) <= 3
        
        # Verify sorting (should be sorted by ber_data_source, then id)
        if len(entities_data["documents"]) > 1:
            for i in range(len(entities_data["documents"]) - 1):
                current = entities_data["documents"][i]
                next_entity = entities_data["documents"][i + 1]
                assert current["ber_data_source"] <= next_entity["ber_data_source"]

    def test_find_entities_invalid_query(self, test_client: TestClient):
        """Test finding entities with invalid MongoDB query."""
        query = {
            "filter": {"$invalid": "operator"}
        }
        
        response = test_client.post(
            "/bertron/find",
            json=query,
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        error_data = response.json()
        assert "Query error" in error_data["detail"]

    def test_geo_nearby_search(self, test_client: TestClient):
        """Test geographic nearby search."""
        # Search near the EMSL coordinates (34, 118.0)
        params = {
            "latitude": 34.0,
            "longitude": 118.0,
            "radius_meters": 100000  # 100km radius
        }
        
        response = test_client.get("/bertron/geo/nearby", params=params)
        
        assert response.status_code == status.HTTP_200_OK
        entities_data = response.json()
        
        assert "documents" in entities_data
        assert "count" in entities_data
        
        # Should find at least the EMSL entity
        found_emsl = False
        for entity in entities_data["documents"]:
            if entity["id"] == "EMSL:c9405190-e962-4ba5-93f0-e3ff499f4488":
                found_emsl = True
            self._verify_entity_structure(entity)
        
        assert found_emsl, "Should find the EMSL entity in nearby search"

    def test_geo_nearby_search_invalid_params(self, test_client: TestClient):
        """Test geographic nearby search with invalid parameters."""
        params = {
            "latitude": 91.0,  # Invalid latitude
            "longitude": 118.0,
            "radius_meters": 1000
        }
        
        response = test_client.get("/bertron/geo/nearby", params=params)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_geo_bounding_box_search(self, test_client: TestClient):
        """Test geographic bounding box search."""
        # Bounding box around Alaska (ESS-DIVE data)
        params = {
            "southwest_lat": 64.0,
            "southwest_lng": -166.0,
            "northeast_lat": 66.0,
            "northeast_lng": -163.0
        }
        
        response = test_client.get("/bertron/geo/bbox", params=params)
        
        assert response.status_code == status.HTTP_200_OK
        entities_data = response.json()
        
        assert "documents" in entities_data
        assert "count" in entities_data
        
        # Should find ESS-DIVE entities in Alaska
        found_ess_dive = False
        for entity in entities_data["documents"]:
            if entity["ber_data_source"] == "ESS-DIVE":
                found_ess_dive = True
                # Verify coordinates are within bounding box
                lat = entity["coordinates"]["latitude"]
                lng = entity["coordinates"]["longitude"]
                assert 64.0 <= lat <= 66.0
                assert -166.0 <= lng <= -163.0
            self._verify_entity_structure(entity)
        
        assert found_ess_dive, "Should find ESS-DIVE entities in Alaska bounding box"

    def test_geo_bounding_box_invalid_coordinates(self, test_client: TestClient):
        """Test bounding box search with invalid coordinates."""
        params = {
            "southwest_lat": 66.0,  # Southwest lat > northeast lat
            "southwest_lng": -163.0,
            "northeast_lat": 64.0,
            "northeast_lng": -166.0
        }
        
        response = test_client.get("/bertron/geo/bbox", params=params)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        error_data = response.json()
        assert "latitude" in error_data["detail"].lower()


    def _verify_entity_structure(self, entity: Dict[str, Any]):
        """Helper method to verify entity structure matches schema."""
        required_fields = [
            "id", "name", "description", "ber_data_source", 
            "entity_type", "coordinates"
        ]
        
        for field in required_fields:
            assert field in entity, f"Missing required field: {field}"
        
        # Verify coordinates structure
        coords = entity["coordinates"]
        assert "latitude" in coords
        assert "longitude" in coords
        assert isinstance(coords["latitude"], (int, float))
        assert isinstance(coords["longitude"], (int, float))
        
        # Verify entity_type is a list
        assert isinstance(entity["entity_type"], list)
        assert len(entity["entity_type"]) > 0
        
        # Verify ber_data_source is valid
        valid_sources = ["EMSL", "ESS-DIVE", "NMDC", "JGI"]
        assert entity["ber_data_source"] in valid_sources


# Integration test that combines multiple operations
class TestBertronAPIIntegration:
    """Integration tests that combine multiple API operations."""
    
    # No need for live server since we're using TestClient
    # Uncomment the line below if you want to run against a test server
    # base_url = "http://app:8000"
    
    def test_data_consistency_across_endpoints(self, test_client: TestClient):
        """Test that the same entity returns consistent data across different endpoints."""
        entity_id = "EMSL:c9405190-e962-4ba5-93f0-e3ff499f4488"
        
        # Get entity by ID
        response1 = test_client.get(f"/bertron/{entity_id}")
        assert response1.status_code == status.HTTP_200_OK
        entity_by_id = response1.json()
        
        # Find entity using filter
        query = {"filter": {"id": entity_id}}
        response2 = test_client.post(
            "/bertron/find",
            json=query,
            headers={"Content-Type": "application/json"}
        )
        assert response2.status_code == status.HTTP_200_OK
        entities_data = response2.json()
        assert entities_data["count"] == 1
        entity_by_filter = entities_data["documents"][0]
        
        # Both should return the same entity data
        assert entity_by_id["id"] == entity_by_filter["id"]
        assert entity_by_id["name"] == entity_by_filter["name"]
        assert entity_by_id["ber_data_source"] == entity_by_filter["ber_data_source"]
        assert entity_by_id["coordinates"] == entity_by_filter["coordinates"]

    def test_geographic_search_consistency(self, test_client: TestClient):
        """Test that geographic searches return consistent results."""
        # Get all entities first
        response = test_client.get("/bertron")
        assert response.status_code == status.HTTP_200_OK
        all_entities = response.json()["documents"]
        
        if len(all_entities) == 0:
            pytest.skip("No entities in database for geographic consistency test")
        
        # Pick an entity with coordinates
        test_entity = None
        for entity in all_entities:
            if (entity["coordinates"]["latitude"] is not None and 
                entity["coordinates"]["longitude"] is not None):
                test_entity = entity
                break
        
        if test_entity is None:
            pytest.skip("No entities with valid coordinates for geographic test")
        
        lat = test_entity["coordinates"]["latitude"]
        lng = test_entity["coordinates"]["longitude"]
        
        # Search with nearby (should include the entity)
        nearby_params = {
            "latitude": lat,
            "longitude": lng,
            "radius_meters": 1000  # 1km radius
        }
        nearby_response = test_client.get("/bertron/geo/nearby", params=nearby_params)
        assert nearby_response.status_code == status.HTTP_200_OK
        nearby_entities = nearby_response.json()["documents"]
        
        # The test entity should be found in nearby search
        found_in_nearby = any(e["id"] == test_entity["id"] for e in nearby_entities)
        assert found_in_nearby, f"Entity {test_entity['id']} should be found in nearby search"
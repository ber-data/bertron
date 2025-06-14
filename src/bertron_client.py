#!/usr/bin/env python3
"""
BERtron API Client

A Python client for interacting with the BERtron API server.
Provides methods to query and retrieve entity data from the BER data sources.
"""

import requests
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import logging
from urllib.parse import urljoin

# Import pydantic Entity from bertron_schema_pydantic
from schema.datamodel.bertron_schema_pydantic import Entity

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class QueryResponse:
    """Represents a response from the BERtron API."""

    entities: List[Entity]
    count: int
    query_type: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class BertronAPIError(Exception):
    """Custom exception for BERtron API errors."""

    pass


class BertronClient:
    """Client for interacting with the BERtron API."""

    def __init__(self, base_url: str = "http://localhost:8000", timeout: int = 30):
        """
        Initialize the BERtron client.

        Args:
            base_url: Base URL of the BERtron API server
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {"Content-Type": "application/json", "Accept": "application/json"}
        )

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Make a request to the BERtron API.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            **kwargs: Additional arguments for requests

        Returns:
            JSON response as dictionary

        Raises:
            BertronAPIError: If the API request fails
        """
        url = urljoin(self.base_url, endpoint)

        try:
            response = self.session.request(
                method=method, url=url, timeout=self.timeout, **kwargs
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"API request failed: {e}")
            raise BertronAPIError(f"API request failed: {e}")

    def health_check(self) -> Dict[str, Any]:
        """
        Check the health of the BERtron API server.

        Returns:
            Health status information
        """
        return self._make_request("GET", "/health")

    def get_all_entities(self) -> QueryResponse:
        """
        Get all entities from the BERtron database.

        Returns:
            QueryResponse containing all entities
        """
        response = self._make_request("GET", "/bertron")
        entities = [Entity(**doc) for doc in response["documents"]]
        return QueryResponse(entities=entities, count=len(entities))

    def get_entity_by_id(self, entity_id: str) -> Entity:
        """
        Get a specific entity by its ID.

        Args:
            entity_id: The unique identifier of the entity

        Returns:
            Entity object

        Raises:
            BertronAPIError: If entity not found or API error
        """
        response = self._make_request("GET", f"/bertron/{entity_id}")
        return Entity(**response)

    def find_entities(
        self,
        filter_dict: Optional[Dict[str, Any]] = None,
        projection: Optional[Dict[str, Any]] = None,
        skip: int = 0,
        limit: int = 100,
        sort: Optional[Dict[str, int]] = None,
    ) -> QueryResponse:
        """
        Search for entities using MongoDB query syntax.

        Args:
            filter_dict: MongoDB filter criteria
            projection: Fields to include/exclude
            skip: Number of documents to skip
            limit: Maximum number of documents to return
            sort: Sort criteria

        Returns:
            QueryResponse containing matching entities
        """
        query_data = {"filter": filter_dict or {}, "skip": skip, "limit": limit}
        if projection:
            query_data["projection"] = projection
        if sort:
            query_data["sort"] = sort

        response = self._make_request("POST", "/bertron/find", json=query_data)
        entities = [Entity(**doc) for doc in response["documents"]]
        return QueryResponse(entities=entities, count=response["count"])

    def find_nearby_entities(
        self, latitude: float, longitude: float, radius_meters: float
    ) -> QueryResponse:
        """
        Find entities within a specified radius of a geographic point.

        Args:
            latitude: Center latitude in degrees (-90 to 90)
            longitude: Center longitude in degrees (-180 to 180)
            radius_meters: Search radius in meters

        Returns:
            QueryResponse containing nearby entities (sorted by distance)
        """
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "radius_meters": radius_meters,
        }

        response = self._make_request("GET", "/bertron/geo/nearby", params=params)
        entities = [Entity(**doc) for doc in response["documents"]]

        # Create metadata based on the request parameters since server doesn't return it
        metadata = {
            "center": {"latitude": latitude, "longitude": longitude},
            "radius_meters": radius_meters,
        }

        return QueryResponse(
            entities=entities,
            count=response["count"],
            query_type="geospatial_nearby",
            metadata=metadata,
        )

    def find_entities_in_bounding_box(
        self,
        southwest_lat: float,
        southwest_lng: float,
        northeast_lat: float,
        northeast_lng: float,
    ) -> QueryResponse:
        """
        Find entities within a rectangular bounding box.

        Args:
            southwest_lat: Southwest corner latitude
            southwest_lng: Southwest corner longitude
            northeast_lat: Northeast corner latitude
            northeast_lng: Northeast corner longitude

        Returns:
            QueryResponse containing entities within the bounding box
        """
        params = {
            "southwest_lat": southwest_lat,
            "southwest_lng": southwest_lng,
            "northeast_lat": northeast_lat,
            "northeast_lng": northeast_lng,
        }

        response = self._make_request("GET", "/bertron/geo/bbox", params=params)
        entities = [Entity(**doc) for doc in response["documents"]]

        # Create metadata based on the request parameters since server doesn't return it
        metadata = {
            "bounding_box": {
                "southwest": {"latitude": southwest_lat, "longitude": southwest_lng},
                "northeast": {"latitude": northeast_lat, "longitude": northeast_lng},
            }
        }

        return QueryResponse(
            entities=entities,
            count=response["count"],
            query_type="geospatial_bounding_box",
            metadata=metadata,
        )

    def find_entities_by_source(self, source: str) -> QueryResponse:
        """
        Find entities from a specific BER data source.

        Args:
            source: BER data source (EMSL, ESS-DIVE, JGI, NMDC, MONET)

        Returns:
            QueryResponse containing entities from the specified source
        """
        return self.find_entities(filter_dict={"ber_data_source": source})

    def find_entities_by_entity_type(self, entity_type: str) -> QueryResponse:
        """
        Find entities of a specific entity type.

        Args:
            entity_type: Entity type (biodata, sample, sequence, taxon, jgi_biosample)

        Returns:
            QueryResponse containing entities of the specified type
        """
        return self.find_entities(filter_dict={"entity_type": entity_type})

    def search_entities_by_name(
        self, name_pattern: str, case_sensitive: bool = False
    ) -> QueryResponse:
        """
        Search for entities by name using regex pattern matching.

        Args:
            name_pattern: Name pattern to search for
            case_sensitive: Whether the search should be case sensitive

        Returns:
            QueryResponse containing entities matching the name pattern
        """
        regex_filter = {"name": {"$regex": name_pattern}}
        if not case_sensitive:
            regex_filter["name"]["$options"] = "i"

        return self.find_entities(filter_dict=regex_filter)

    def get_entities_in_region(
        self, center_lat: float, center_lng: float, radius_km: float
    ) -> QueryResponse:
        """
        Convenience method to find entities in a region (radius in kilometers).

        Args:
            center_lat: Center latitude
            center_lng: Center longitude
            radius_km: Radius in kilometers

        Returns:
            QueryResponse containing entities in the specified region
        """
        radius_meters = radius_km * 1000
        return self.find_nearby_entities(center_lat, center_lng, radius_meters)

    def close(self):
        """Close the HTTP session."""
        self.session.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# Example usage
if __name__ == "__main__":
    # Example usage of the BERtron client

    # Initialize client
    client = BertronClient(base_url="http://localhost:8000")

    try:
        # Check server health
        health = client.health_check()
        print(f"Server health: {health}")

        # Get all entities
        print("\nGetting all entities...")
        all_entities = client.get_all_entities()
        print(f"Found {all_entities.count} entities")

        if all_entities.entities:
            # Show first entity as example
            first_entity = all_entities.entities[0]
            print(f"First entity: {first_entity.name} ({first_entity.id})")

            # Get specific entity by ID (if ID is available)
            if first_entity.id:
                entity = client.get_entity_by_id(first_entity.id)
                print(f"Retrieved entity: {entity.name}")

        # Search for entities from EMSL
        print("\nSearching for EMSL entities...")
        emsl_entities = client.find_entities_by_source("EMSL")
        print(f"Found {emsl_entities.count} EMSL entities")

        # Search for sample entities
        print("\nSearching for sample entities...")
        sample_entities = client.find_entities_by_entity_type("sample")
        print(f"Found {sample_entities.count} sample entities")

        # Geographic search near Seattle
        print("\nSearching near Florida (10km radius)...")
        florida_entities = client.get_entities_in_region(28.1, -81.4, 100)
        print(f"Found {florida_entities.count} entities near Florida")

        # Bounding box search for Yellowstone region
        print("\nSearching Yellowstone region region...")
        pnw_entities = client.find_entities_in_bounding_box(
            southwest_lat=44.0,
            southwest_lng=-125.0,
            northeast_lat=49.0,
            northeast_lng=-110.0,
        )
        print(f"Found {pnw_entities.count} entities in Yellowstone region")

    except BertronAPIError as e:
        print(f"API Error: {e}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.close()

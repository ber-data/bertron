import json
import os
from unittest.mock import Mock

import pytest

from src.ingest_data import BertronMongoDBIngestor


@pytest.fixture
def sample_data_dir():
    """Path to the sample data directory."""
    return "tests/data"


@pytest.fixture
def mock_ingestor(mocker):
    """Create an ingestor with mocked external dependencies but real processing logic."""
    # Mock external dependencies only
    mocker.patch('src.ingest_data.MongoClient')
    mock_httpx = mocker.patch('src.ingest_data.httpx.get')

    # Mock schema response
    mock_response = Mock()
    mock_response.json.return_value = {
        "type": "object",
        "version": "1.0.0",
        "properties": {}
    }
    mock_httpx.return_value = mock_response

    ingestor = BertronMongoDBIngestor(
        "mongodb://test:test@localhost:27017",
        "test_db",
        "https://example.com/schema.json"
    )

    # Set up minimal state needed for processing
    ingestor.db = Mock()
    ingestor.schema = {"version": "1.0.0"}

    return ingestor


@pytest.fixture
def setup_mock_collection(mock_ingestor):
    """Set up a mock collection for database operations and return the ingestor and collection."""
    mock_collection = Mock()
    mock_ingestor.db.entities = mock_collection
    mock_result = Mock()
    mock_result.upserted_id = "test_id"
    mock_collection.update_one.return_value = mock_result

    return mock_ingestor, mock_collection


def test_end_to_end_geojson_transformation(setup_mock_collection, sample_data_dir):
    """Test that real sample data gets transformed correctly to GeoJSON format."""
    mock_ingestor, mock_collection = setup_mock_collection

    # Use real EMSL data which has simple coordinates
    emsl_file = os.path.join(sample_data_dir, "emsl-example.json")

    with open(emsl_file, 'r') as f:
        emsl_data = json.load(f)

    # Process the real entity
    mock_ingestor.insert_entity(emsl_data)

    # Verify GeoJSON transformation happened correctly
    call_args = mock_collection.update_one.call_args
    entity_data = call_args[0][1]["$set"]

    # Check that coordinates were converted to GeoJSON Point
    assert "geojson" in entity_data
    assert entity_data["geojson"]["type"] == "Point"

    # Verify longitude comes first in GeoJSON (this is the key business rule)
    expected_coords = [emsl_data["coordinates"]["longitude"], emsl_data["coordinates"]["latitude"]]
    assert entity_data["geojson"]["coordinates"] == expected_coords

    # Verify metadata was added
    assert "_metadata" in entity_data
    assert "ingested_at" in entity_data["_metadata"]
    assert entity_data["_metadata"]["schema_version"] == "1.0.0"


def test_end_to_end_complex_coordinates(setup_mock_collection, sample_data_dir):
    """Test processing NMDC data which has complex coordinate structure with depth/elevation."""
    mock_ingestor, mock_collection = setup_mock_collection

    nmdc_file = os.path.join(sample_data_dir, "nmdc-example.json")

    with open(nmdc_file, 'r') as f:
        nmdc_data = json.load(f)


    # Verify the sample has the complex structure we expect (depth/elevation in properties)
    props = nmdc_data["properties"]
    depth_prop = next((p for p in props if p["attribute"]["label"] == "depth"), None)
    elevation_prop = next((p for p in props if p["attribute"]["label"] == "elevation"), None)
    assert depth_prop is not None
    assert elevation_prop is not None

    # Process the complex entity
    mock_ingestor.insert_entity(nmdc_data)

    # Verify it still creates proper GeoJSON despite complex coordinate structure
    call_args = mock_collection.update_one.call_args
    entity_data = call_args[0][1]["$set"]

    assert "geojson" in entity_data
    assert entity_data["geojson"]["type"] == "Point"

    # Basic lat/lng should still be extracted correctly
    coords = nmdc_data["coordinates"]
    expected_coords = [coords["longitude"], coords["latitude"]]
    assert entity_data["geojson"]["coordinates"] == expected_coords


def test_end_to_end_directory_processing(mocker, mock_ingestor, sample_data_dir):
    """Test processing entire directory of sample files like production would."""
    # Mock validation to pass for all real data
    mocker.patch.object(mock_ingestor, 'validate_data', return_value=True)

    # Track all entities that would be inserted
    inserted_entities = []

    capture_side_effect = lambda data: inserted_entities.append(data) or "inserted_id"
    mocker.patch.object(mock_ingestor, 'insert_entity', side_effect=capture_side_effect)

    # Get all sample files
    json_files = [f for f in os.listdir(sample_data_dir) if f.endswith('.json')]
    assert len(json_files) >= 3, "Need at least 3 sample files for meaningful test"

    total_processed = 0

    # Process each file
    for json_file in json_files:
        file_path = os.path.join(sample_data_dir, json_file)
        stats = mock_ingestor.ingest_file(file_path)

        # Each file should contain at least one entity
        assert stats["processed"] >= 1, f"Expected at least 1 entity in {json_file}, got {stats['processed']}"
        assert stats["valid"] == stats["processed"], f"Validation failed for some entities in {json_file}"
        assert stats["inserted"] == stats["processed"], f"Insert failed for some entities in {json_file}"
        assert stats["error"] == 0, f"Unexpected error in {json_file}"

        total_processed += stats["processed"]

    # Verify we processed all files and entities
    assert total_processed >= len(json_files), f"Expected at least {len(json_files)} entities, got {total_processed}"
    assert len(inserted_entities) == total_processed

    # Verify all entities have required fields and proper structure
    data_sources = set()
    for entity in inserted_entities:
        # Every entity must have these core fields
        assert "id" in entity
        assert "ber_data_source" in entity
        assert "coordinates" in entity
        assert "uri" in entity
        # Name is optional but description should exist
        assert "name" in entity or "description" in entity

        # Track data source diversity
        data_sources.add(entity["ber_data_source"])

        # Coordinates must be valid
        coords = entity["coordinates"]
        assert isinstance(coords["latitude"], (int, float))
        assert isinstance(coords["longitude"], (int, float))
        assert -90 <= coords["latitude"] <= 90
        assert -180 <= coords["longitude"] <= 180

    # Verify we have multiple data sources represented
    assert len(data_sources) >= 2, f"Expected multiple data sources, got: {data_sources}"

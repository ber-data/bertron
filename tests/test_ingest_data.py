import json
import os
import tempfile
from unittest.mock import Mock

import pytest

from mongodb.ingest_data import BertronMongoDBIngestor


@pytest.fixture
def sample_schema():
    """Sample schema for testing."""
    return {
        "type": "object",
        "version": "1.0.0",
        "properties": {
            "id": {"type": "string"},
            "name": {"type": "string"},
            "ber_data_source": {"type": "string"},
            "coordinates": {
                "type": "object",
                "properties": {
                    "latitude": {"type": "number"},
                    "longitude": {"type": "number"}
                }
            }
        },
        "required": ["id", "name", "ber_data_source"]
    }


@pytest.fixture
def sample_entity():
    """Sample entity data for testing."""
    return {
        "id": "test:123",
        "name": "Test Entity",
        "description": "Test description",
        "ber_data_source": "TEST",
        "entity_type": ["sample"],
        "coordinates": {
            "latitude": 45.0,
            "longitude": -122.0
        },
        "uri": "https://test.example.com/123"
    }


@pytest.fixture
def ingestor():
    """Create a BertronMongoDBIngestor instance for testing."""
    return BertronMongoDBIngestor(
        "mongodb://test:test@localhost:27017",
        "test_bertron",
        "/path/to/schema.json"
    )


@pytest.fixture
def sample_data_dir():
    """Path to the sample data directory."""
    return "tests/data"


def test_geojson_conversion(ingestor, sample_schema, sample_entity):
    """Test that coordinates are properly converted to GeoJSON format."""
    mock_db = Mock()
    mock_collection = Mock()
    mock_db.entities = mock_collection
    
    mock_result = Mock()
    mock_result.upserted_id = "new_id_123"
    mock_collection.update_one.return_value = mock_result
    
    ingestor.schema = sample_schema
    ingestor.db = mock_db
    
    result = ingestor.insert_entity(sample_entity.copy())
    
    # Verify the entity was modified with correct GeoJSON format
    args, kwargs = mock_collection.update_one.call_args
    entity_data = args[1]["$set"]
    
    assert "geojson" in entity_data
    assert entity_data["geojson"]["type"] == "Point"
    assert entity_data["geojson"]["coordinates"] == [-122.0, 45.0]  # [lng, lat] - longitude first!


def test_metadata_injection(mocker, ingestor, sample_schema, sample_entity):
    """Test that metadata is properly injected into entities."""
    mock_datetime = mocker.patch('mongodb.ingest_data.datetime')
    mock_now = Mock()
    mock_datetime.now.return_value = mock_now
    mock_datetime.UTC = Mock()
    
    mock_db = Mock()
    mock_collection = Mock()
    mock_db.entities = mock_collection
    
    mock_result = Mock()
    mock_result.upserted_id = "new_id_123"
    mock_collection.update_one.return_value = mock_result
    
    ingestor.schema = sample_schema
    ingestor.db = mock_db
    
    ingestor.insert_entity(sample_entity.copy())
    
    # Verify metadata was added
    args, kwargs = mock_collection.update_one.call_args
    entity_data = args[1]["$set"]
    
    assert "_metadata" in entity_data
    assert entity_data["_metadata"]["ingested_at"] == mock_now
    assert entity_data["_metadata"]["schema_version"] == "1.0.0"


def test_file_handles_single_entity_and_array(mocker, ingestor, sample_entity):
    """Test that ingest_file handles both single entities and arrays."""
    mocker.patch.object(ingestor, 'validate_data', return_value=True)
    mocker.patch.object(ingestor, 'insert_entity', return_value="inserted_id")
    
    # Test single entity
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(sample_entity, f)
        single_path = f.name
    
    # Test array of entities
    entities = [sample_entity, sample_entity.copy()]
    entities[1]["id"] = "test:456"
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(entities, f)
        array_path = f.name
    
    try:
        # Single entity should work
        stats = ingestor.ingest_file(single_path)
        assert stats["processed"] == 1
        
        # Array should work too
        stats = ingestor.ingest_file(array_path)
        assert stats["processed"] == 2
        
    finally:
        os.unlink(single_path)
        os.unlink(array_path)


def test_upsert_behavior(ingestor, sample_schema, sample_entity):
    """Test that entities are upserted based on URI (not inserted as duplicates)."""
    mock_db = Mock()
    mock_collection = Mock()
    mock_db.entities = mock_collection
    
    mock_result = Mock()
    mock_result.upserted_id = "new_id_123"
    mock_collection.update_one.return_value = mock_result
    
    ingestor.schema = sample_schema
    ingestor.db = mock_db
    
    ingestor.insert_entity(sample_entity.copy())
    
    # Verify upsert was used with URI as the key
    args, kwargs = mock_collection.update_one.call_args
    assert args[0] == {"uri": sample_entity["uri"]}
    assert kwargs["upsert"] is True


def test_schema_loading_from_file(ingestor, sample_schema):
    """Test loading schema from local file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(sample_schema, f)
        temp_path = f.name
    
    try:
        ingestor.schema_path = temp_path
        result = ingestor.load_schema()
        
        assert result == sample_schema
        assert ingestor.schema == sample_schema
    finally:
        os.unlink(temp_path)


def test_schema_loading_from_url(mocker, ingestor, sample_schema):
    """Test loading schema from HTTP URL."""
    mock_httpx_get = mocker.patch('mongodb.ingest_data.httpx.get')
    mock_response = Mock()
    mock_response.json.return_value = sample_schema
    mock_httpx_get.return_value = mock_response
    
    ingestor.schema_path = "https://example.com/schema.json"
    result = ingestor.load_schema()
    
    mock_httpx_get.assert_called_once_with("https://example.com/schema.json")
    mock_response.raise_for_status.assert_called_once()
    assert result == sample_schema


def test_validation_uses_both_jsonschema_and_pydantic(mocker, ingestor, sample_schema, sample_entity):
    """Test that validation uses both JSON Schema validation and Pydantic model validation."""
    mock_validate = mocker.patch('mongodb.ingest_data.validate')
    mock_entity = mocker.patch('mongodb.ingest_data.Entity')
    
    ingestor.schema = sample_schema
    mock_validate.return_value = None
    mock_entity.return_value = Mock()
    
    result = ingestor.validate_data(sample_entity)
    
    assert result is True
    mock_validate.assert_called_once_with(instance=sample_entity, schema=sample_schema)
    mock_entity.assert_called_once_with(**sample_entity)


# Integration tests using actual sample data files

def test_ingest_sample_data_files(sample_data_dir):
    """Test that all sample data files can be loaded and have expected structure."""
    json_files = [f for f in os.listdir(sample_data_dir) if f.endswith('.json')]
    
    for json_file in json_files:
        file_path = os.path.join(sample_data_dir, json_file)
        
        # Verify file can be loaded as JSON
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Verify required fields are present
        assert "id" in data, f"Missing 'id' in {json_file}"
        assert "name" in data, f"Missing 'name' in {json_file}"
        assert "ber_data_source" in data, f"Missing 'ber_data_source' in {json_file}"
        assert "coordinates" in data, f"Missing 'coordinates' in {json_file}"
        assert "uri" in data, f"Missing 'uri' in {json_file}"
        
        # Verify coordinates structure
        coords = data["coordinates"]
        assert "latitude" in coords, f"Missing 'latitude' in coordinates in {json_file}"
        assert "longitude" in coords, f"Missing 'longitude' in coordinates in {json_file}"
        assert isinstance(coords["latitude"], (int, float)), f"Invalid latitude type in {json_file}"
        assert isinstance(coords["longitude"], (int, float)), f"Invalid longitude type in {json_file}"


def test_sample_data_can_be_processed(mocker, sample_data_dir):
    """Test that sample data files can be processed by the ingestor."""
    # Use a real ingestor but mock external dependencies
    mocker.patch('mongodb.ingest_data.MongoClient')
    mock_httpx = mocker.patch('mongodb.ingest_data.httpx.get')
    
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
    
    # Mock database operations but allow file processing
    ingestor.db = Mock()
    ingestor.schema = {"version": "1.0.0"}
    
    # Mock validation and insertion to focus on file processing
    mocker.patch.object(ingestor, 'validate_data', return_value=True)
    mocker.patch.object(ingestor, 'insert_entity', return_value="inserted_id")
    
    # Test each sample file
    for filename in ["emsl-example.json", "nmdc-example.json", "ess-dive-example.json"]:
        file_path = os.path.join(sample_data_dir, filename)
        stats = ingestor.ingest_file(file_path)
        
        assert stats["processed"] == 1, f"Failed to process {filename}"
        assert stats["valid"] == 1, f"Validation failed for {filename}"
        assert stats["inserted"] == 1, f"Insertion failed for {filename}"
        assert stats["error"] == 0, f"Unexpected error processing {filename}"
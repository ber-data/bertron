import json
import os
import tempfile
from unittest.mock import Mock, patch
from typing import Dict, Any

import pytest
from pymongo.errors import ConnectionFailure, PyMongoError
from jsonschema import ValidationError

from mongodb.ingest_data import BertronMongoDBIngestor


@pytest.fixture
def mock_mongo_uri():
    """Mock MongoDB URI for testing."""
    return "mongodb://test:test@localhost:27017"


@pytest.fixture
def mock_db_name():
    """Mock database name for testing."""
    return "test_bertron"


@pytest.fixture
def mock_schema_path():
    """Mock schema path for testing."""
    return "/path/to/schema.json"


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
def ingestor(mock_mongo_uri, mock_db_name, mock_schema_path):
    """Create a BertronMongoDBIngestor instance for testing."""
    return BertronMongoDBIngestor(mock_mongo_uri, mock_db_name, mock_schema_path)


@pytest.fixture
def sample_data_dir():
    """Path to the sample data directory."""
    return "tests/data"


def test_init(mock_mongo_uri, mock_db_name, mock_schema_path):
    """Test ingestor initialization."""
    ingestor = BertronMongoDBIngestor(mock_mongo_uri, mock_db_name, mock_schema_path)
    
    assert ingestor.mongo_uri == mock_mongo_uri
    assert ingestor.db_name == mock_db_name
    assert ingestor.schema_path == mock_schema_path
    assert ingestor.client is None
    assert ingestor.db is None
    assert ingestor.schema is None


@patch('mongodb.ingest_data.MongoClient')
def test_connect_success(mock_mongo_client, ingestor):
    """Test successful MongoDB connection."""
    mock_client = Mock()
    mock_db = Mock()
    mock_mongo_client.return_value = mock_client
    mock_client.__getitem__.return_value = mock_db
    
    ingestor.connect()
    
    mock_mongo_client.assert_called_once_with(ingestor.mongo_uri)
    assert ingestor.client == mock_client
    assert ingestor.db == mock_db


@patch('mongodb.ingest_data.MongoClient')
@patch('mongodb.ingest_data.sys.exit')
def test_connect_failure(mock_exit, mock_mongo_client, ingestor):
    """Test MongoDB connection failure."""
    mock_mongo_client.side_effect = ConnectionFailure("Connection failed")
    
    ingestor.connect()
    
    mock_exit.assert_called_once_with(1)


def test_clean_collections_success(ingestor):
    """Test successful collection cleaning."""
    mock_db = Mock()
    mock_db.list_collection_names.return_value = ["entities", "other_collection"]
    mock_entities_collection = Mock()
    mock_db.entities = mock_entities_collection
    ingestor.db = mock_db
    
    ingestor.clean_collections()
    
    mock_db.list_collection_names.assert_called_once()
    mock_entities_collection.drop.assert_called_once()


def test_clean_collections_no_entities(ingestor):
    """Test collection cleaning when entities collection doesn't exist."""
    mock_db = Mock()
    mock_db.list_collection_names.return_value = ["other_collection"]
    ingestor.db = mock_db
    
    ingestor.clean_collections()
    
    mock_db.list_collection_names.assert_called_once()


@patch('mongodb.ingest_data.sys.exit')
def test_clean_collections_error(mock_exit, ingestor):
    """Test collection cleaning with database error."""
    mock_db = Mock()
    mock_db.list_collection_names.side_effect = PyMongoError("Database error")
    ingestor.db = mock_db
    
    ingestor.clean_collections()
    
    mock_exit.assert_called_once_with(1)


def test_load_schema_from_file(ingestor, sample_schema):
    """Test loading schema from file."""
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


@patch('mongodb.ingest_data.httpx.get')
def test_load_schema_from_url(mock_httpx_get, ingestor, sample_schema):
    """Test loading schema from URL."""
    mock_response = Mock()
    mock_response.json.return_value = sample_schema
    mock_httpx_get.return_value = mock_response
    
    ingestor.schema_path = "https://example.com/schema.json"
    result = ingestor.load_schema()
    
    mock_httpx_get.assert_called_once_with("https://example.com/schema.json")
    mock_response.raise_for_status.assert_called_once()
    assert result == sample_schema
    assert ingestor.schema == sample_schema


@patch('mongodb.ingest_data.sys.exit')
def test_load_schema_file_not_found(mock_exit, ingestor):
    """Test loading schema when file not found."""
    ingestor.schema_path = "/nonexistent/schema.json"
    
    ingestor.load_schema()
    
    mock_exit.assert_called_once_with(1)


@patch('mongodb.ingest_data.validate')
@patch('mongodb.ingest_data.Entity')
def test_validate_data_success(mock_entity, mock_validate, ingestor, sample_schema, sample_entity):
    """Test successful data validation."""
    ingestor.schema = sample_schema
    mock_validate.return_value = None
    mock_entity.return_value = Mock()
    
    result = ingestor.validate_data(sample_entity)
    
    assert result is True
    mock_validate.assert_called_once_with(instance=sample_entity, schema=sample_schema)
    mock_entity.assert_called_once_with(**sample_entity)


@patch('mongodb.ingest_data.validate')
def test_validate_data_json_schema_error(mock_validate, ingestor, sample_schema, sample_entity):
    """Test data validation with JSON schema error."""
    ingestor.schema = sample_schema
    mock_validate.side_effect = ValidationError("Schema validation failed")
    
    result = ingestor.validate_data(sample_entity)
    
    assert result is False


@patch('mongodb.ingest_data.validate')
@patch('mongodb.ingest_data.Entity')
def test_validate_data_pydantic_error(mock_entity, mock_validate, ingestor, sample_schema, sample_entity):
    """Test data validation with Pydantic validation error."""
    ingestor.schema = sample_schema
    mock_validate.return_value = None
    mock_entity.side_effect = ValueError("Pydantic validation failed")
    
    result = ingestor.validate_data(sample_entity)
    
    assert result is False


@patch('mongodb.ingest_data.datetime')
def test_insert_entity_success(mock_datetime, ingestor, sample_schema, sample_entity):
    """Test successful entity insertion."""
    # Setup mocks
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
    
    result = ingestor.insert_entity(sample_entity.copy())
    
    # Verify result
    assert result == "new_id_123"
    
    # Verify update_one was called with correct data
    args, kwargs = mock_collection.update_one.call_args
    assert args[0] == {"uri": sample_entity["uri"]}
    assert "upsert" in kwargs and kwargs["upsert"] is True
    
    # Verify the entity was modified with metadata and geojson
    entity_data = args[1]["$set"]
    assert "_metadata" in entity_data
    assert "geojson" in entity_data
    assert entity_data["geojson"]["type"] == "Point"
    assert entity_data["geojson"]["coordinates"] == [-122.0, 45.0]  # [lng, lat]
    
    # Verify indexes were created
    assert mock_collection.create_index.call_count == 4


def test_insert_entity_invalid_coordinates(ingestor, sample_schema):
    """Test entity insertion with invalid coordinates."""
    entity = {
        "id": "test:123",
        "name": "Test Entity",
        "uri": "https://test.example.com/123",
        "coordinates": "invalid_coordinates"
    }
    
    mock_db = Mock()
    ingestor.schema = sample_schema
    ingestor.db = mock_db
    
    result = ingestor.insert_entity(entity)
    
    assert result is None


def test_insert_entity_database_error(ingestor, sample_schema, sample_entity):
    """Test entity insertion with database error."""
    mock_db = Mock()
    mock_collection = Mock()
    mock_db.entities = mock_collection
    mock_collection.update_one.side_effect = PyMongoError("Database error")
    
    ingestor.schema = sample_schema
    ingestor.db = mock_db
    
    result = ingestor.insert_entity(sample_entity)
    
    assert result is None


def test_ingest_file_single_entity(ingestor, sample_entity):
    """Test ingesting a file with a single entity."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(sample_entity, f)
        temp_path = f.name
    
    try:
        with patch.object(ingestor, 'validate_data', return_value=True), \
             patch.object(ingestor, 'insert_entity', return_value="inserted_id"):
            
            stats = ingestor.ingest_file(temp_path)
            
            assert stats["processed"] == 1
            assert stats["valid"] == 1
            assert stats["invalid"] == 0
            assert stats["inserted"] == 1
            assert stats["error"] == 0
    finally:
        os.unlink(temp_path)


def test_ingest_file_multiple_entities(ingestor, sample_entity):
    """Test ingesting a file with multiple entities."""
    entities = [sample_entity, sample_entity.copy()]
    entities[1]["id"] = "test:456"
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(entities, f)
        temp_path = f.name
    
    try:
        with patch.object(ingestor, 'validate_data', return_value=True), \
             patch.object(ingestor, 'insert_entity', return_value="inserted_id"):
            
            stats = ingestor.ingest_file(temp_path)
            
            assert stats["processed"] == 2
            assert stats["valid"] == 2
            assert stats["invalid"] == 0
            assert stats["inserted"] == 2
            assert stats["error"] == 0
    finally:
        os.unlink(temp_path)


def test_ingest_file_validation_errors(ingestor, sample_entity):
    """Test ingesting a file with validation errors."""
    entities = [sample_entity, sample_entity.copy()]
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(entities, f)
        temp_path = f.name
    
    try:
        # First entity valid, second invalid
        validate_results = [True, False]
        with patch.object(ingestor, 'validate_data', side_effect=validate_results), \
             patch.object(ingestor, 'insert_entity', return_value="inserted_id"):
            
            stats = ingestor.ingest_file(temp_path)
            
            assert stats["processed"] == 2
            assert stats["valid"] == 1
            assert stats["invalid"] == 1
            assert stats["inserted"] == 1
            assert stats["error"] == 0
    finally:
        os.unlink(temp_path)


def test_ingest_file_not_found(ingestor):
    """Test ingesting a non-existent file."""
    stats = ingestor.ingest_file("/nonexistent/file.json")
    
    assert stats["processed"] == 0
    assert stats["valid"] == 0
    assert stats["invalid"] == 0
    assert stats["inserted"] == 0
    assert stats["error"] == 1


def test_close(ingestor):
    """Test closing MongoDB connection."""
    mock_client = Mock()
    ingestor.client = mock_client
    
    ingestor.close()
    
    mock_client.close.assert_called_once()


def test_close_no_client(ingestor):
    """Test closing when no client exists."""
    ingestor.client = None
    
    # Should not raise an exception
    ingestor.close()


# Integration tests using actual sample data files

@pytest.fixture
def mock_ingestor():
    """Mock ingestor for integration tests."""
    with patch('mongodb.ingest_data.MongoClient'), \
         patch('mongodb.ingest_data.httpx.get') as mock_httpx:
        
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
        
        # Mock database operations
        ingestor.db = Mock()
        ingestor.schema = {"version": "1.0.0"}
        
        yield ingestor


def test_ingest_emsl_sample(mock_ingestor, sample_data_dir):
    """Test ingesting EMSL sample data."""
    file_path = os.path.join(sample_data_dir, "emsl-example.json")
    
    with patch.object(mock_ingestor, 'validate_data', return_value=True), \
         patch.object(mock_ingestor, 'insert_entity', return_value="inserted_id"):
        
        stats = mock_ingestor.ingest_file(file_path)
        
        assert stats["processed"] == 1
        assert stats["valid"] == 1
        assert stats["inserted"] == 1
        assert stats["error"] == 0


def test_ingest_nmdc_sample(mock_ingestor, sample_data_dir):
    """Test ingesting NMDC sample data."""
    file_path = os.path.join(sample_data_dir, "nmdc-example.json")
    
    with patch.object(mock_ingestor, 'validate_data', return_value=True), \
         patch.object(mock_ingestor, 'insert_entity', return_value="inserted_id"):
        
        stats = mock_ingestor.ingest_file(file_path)
        
        assert stats["processed"] == 1
        assert stats["valid"] == 1
        assert stats["inserted"] == 1
        assert stats["error"] == 0


def test_ingest_ess_dive_sample(mock_ingestor, sample_data_dir):
    """Test ingesting ESS-DIVE sample data."""
    file_path = os.path.join(sample_data_dir, "ess-dive-example.json")
    
    with patch.object(mock_ingestor, 'validate_data', return_value=True), \
         patch.object(mock_ingestor, 'insert_entity', return_value="inserted_id"):
        
        stats = mock_ingestor.ingest_file(file_path)
        
        assert stats["processed"] == 1
        assert stats["valid"] == 1
        assert stats["inserted"] == 1
        assert stats["error"] == 0


def test_ingest_all_sample_files(mock_ingestor, sample_data_dir):
    """Test ingesting all sample data files."""
    json_files = [f for f in os.listdir(sample_data_dir) if f.endswith('.json')]
    total_processed = 0
    
    with patch.object(mock_ingestor, 'validate_data', return_value=True), \
         patch.object(mock_ingestor, 'insert_entity', return_value="inserted_id"):
        
        for json_file in json_files:
            file_path = os.path.join(sample_data_dir, json_file)
            stats = mock_ingestor.ingest_file(file_path)
            total_processed += stats["processed"]
            
            assert stats["processed"] == 1
            assert stats["valid"] == 1
            assert stats["inserted"] == 1
            assert stats["error"] == 0
    
    # Verify we processed all sample files
    assert total_processed == len(json_files)
    assert total_processed >= 5  # We know there are at least 5 sample files


def test_ingest_sample_data_structure(mock_ingestor, sample_data_dir):
    """Test that sample data files have expected structure."""
    for filename in ["emsl-example.json", "nmdc-example.json", "ess-dive-example.json"]:
        file_path = os.path.join(sample_data_dir, filename)
        
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Verify required fields are present
        assert "id" in data
        assert "name" in data
        assert "ber_data_source" in data
        assert "coordinates" in data
        assert "uri" in data
        
        # Verify coordinates structure
        coords = data["coordinates"]
        assert "latitude" in coords
        assert "longitude" in coords
        assert isinstance(coords["latitude"], (int, float))
        assert isinstance(coords["longitude"], (int, float))
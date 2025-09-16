import json
import os

import pytest
from pymongo.database import Database


@pytest.fixture
def sample_data_dir():
    """Path to the sample data directory."""
    return "tests/data"


def test_geojson_coordinate_transformation(seeded_db: Database):
    """Test that sample data gets transformed correctly to GeoJSON format."""
    # The seeded_db fixture already processed all files
    # Query the actual database to verify the entity was stored correctly
    entity = seeded_db.entities.find_one({"id": "EMSL:c9405190-e962-4ba5-93f0-e3ff499f4488"})
    assert entity is not None
    
    # Verify GeoJSON transformation happened correctly
    assert "geojson" in entity
    assert entity["geojson"]["type"] == "Point"
    
    # Verify longitude comes first in GeoJSON (this is the key business rule)
    assert entity["geojson"]["coordinates"] == [118, 34]  # lng, lat order
    
    # Verify metadata was added
    assert "_metadata" in entity
    assert "ingested_at" in entity["_metadata"]
    assert "schema_version" in entity["_metadata"]


def test_nmdc_properties_processing(seeded_db: Database, sample_data_dir):
    """Test processing NMDC data which has complex coordinate structure with depth/elevation."""
    # Load and verify the test data structure first
    nmdc_file = os.path.join(sample_data_dir, "nmdc-example.json")
    with open(nmdc_file, 'r') as f:
        nmdc_data = json.load(f)
    
    # Verify the sample has the complex structure we expect (depth/elevation in properties)
    properties = [prop["attribute"]["label"] for prop in nmdc_data.get("properties", [])]
    assert "depth" in properties
    assert "elevation" in properties
    
    # Query the database to verify it was stored correctly (seeded_db already processed it)
    entity = seeded_db.entities.find_one({"id": "nmdc:bsm-11-bsf8yq62"})
    assert entity is not None
    
    # Verify it still creates proper GeoJSON despite complex coordinate structure
    assert "geojson" in entity
    assert entity["geojson"]["type"] == "Point"
    
    # Basic lat/lng should still be extracted correctly
    assert entity["geojson"]["coordinates"] == [-81.434174, 28.125842]  # lng, lat order
    
    # Verify original properties are preserved
    stored_properties = [prop["attribute"]["label"] for prop in entity.get("properties", [])]
    assert "depth" in stored_properties
    assert "elevation" in stored_properties


def test_complete_directory_ingestion(seeded_db: Database):
    """Test that all sample files were processed correctly by the seeded_db fixture."""
    # The seeded_db fixture already processes the entire directory
    # We just need to verify the results
    
    # Get all entities from the database
    entities = list(seeded_db.entities.find({}))
    assert len(entities) >= 5  # Should have at least 5 entities from our test files
    
    # Verify all entities have required fields and proper structure
    data_sources = set()
    for entity in entities:
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
        
        # Verify GeoJSON was created
        assert "geojson" in entity
        assert entity["geojson"]["type"] == "Point"
        assert len(entity["geojson"]["coordinates"]) == 2
        
        # Verify metadata
        assert "_metadata" in entity
        assert "ingested_at" in entity["_metadata"]
    
    # Verify we have multiple data sources represented
    assert len(data_sources) >= 2, f"Expected multiple data sources, got: {data_sources}"


def test_array_file_ingestion(seeded_db: Database):
    """Test that JSON array files are processed correctly."""
    # The seeded_db fixture already processed the ess-dive-example.json array file
    # Note: All 3 entities have the same ID, so only the last one is stored (the others are updates)
    ess_dive_entities = list(seeded_db.entities.find({"ber_data_source": "ESS-DIVE"}))
    assert len(ess_dive_entities) == 1
    
    # Verify the final entity has the coordinates from the last entry (Council site)
    entity = ess_dive_entities[0]
    assert entity["geojson"]["coordinates"] == [-163.71993600000002, 64.847286]  # Council
    assert "Council" in entity["description"]


def test_data_source_diversity(seeded_db: Database):
    """Test that entities from multiple data sources are ingested."""
    # Get all unique data sources
    data_sources = seeded_db.entities.distinct("ber_data_source")
    
    # Should have multiple data sources
    assert len(data_sources) >= 3
    expected_sources = {"EMSL", "ESS-DIVE", "NMDC", "JGI"}
    assert set(data_sources).issubset(expected_sources)
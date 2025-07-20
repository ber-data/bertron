"""
Test to verify that the Docker Compose file uses constant values for MongoDB connection.
"""
import yaml
import pytest
from pathlib import Path


def test_docker_compose_uses_constant_mongo_values():
    """Test that MONGO_HOST and MONGO_PORT are set to constants in docker-compose.yml"""
    
    # Load the docker-compose.yml file
    compose_file = Path(__file__).parent.parent / "docker-compose.yml"
    
    with open(compose_file, 'r') as f:
        compose_config = yaml.safe_load(f)
    
    # Check app service environment
    app_env = compose_config['services']['app']['environment']
    assert app_env['MONGO_HOST'] == 'mongo', "app service should use constant MONGO_HOST=mongo"
    assert app_env['MONGO_PORT'] == 27017, "app service should use constant MONGO_PORT=27017"
    
    # Check test service environment
    test_env = compose_config['services']['test']['environment']
    assert test_env['MONGO_HOST'] == 'mongo', "test service should use constant MONGO_HOST=mongo"
    assert test_env['MONGO_PORT'] == 27017, "test service should use constant MONGO_PORT=27017"
    
    # Verify that the mongo service name matches the constant
    assert 'mongo' in compose_config['services'], "mongo service should exist"
    
    # Verify that the port mapping uses 27017 as container port
    mongo_ports = compose_config['services']['mongo']['ports']
    assert len(mongo_ports) == 1, "mongo service should have exactly one port mapping"
    port_mapping = mongo_ports[0]
    # The mapping should be in format "${MONGO_PORT:-27017}:27017"
    assert port_mapping.endswith(':27017'), "mongo service should map to container port 27017"


def test_ingest_service_uses_correct_mongo_uri():
    """Test that ingest service command uses the same constants in its mongo URI"""
    
    # Load the docker-compose.yml file
    compose_file = Path(__file__).parent.parent / "docker-compose.yml"
    
    with open(compose_file, 'r') as f:
        compose_config = yaml.safe_load(f)
    
    # Check ingest service command
    ingest_command = compose_config['services']['ingest']['command']
    
    # Find the mongo-uri argument
    mongo_uri = None
    for i, arg in enumerate(ingest_command):
        if arg == '--mongo-uri' and i + 1 < len(ingest_command):
            mongo_uri = ingest_command[i + 1]
            break
    
    assert mongo_uri is not None, "ingest service should have --mongo-uri argument"
    assert 'mongo:27017' in mongo_uri, "ingest service should use mongo:27017 in URI"
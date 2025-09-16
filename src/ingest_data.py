#!/usr/bin/env python3

import argparse
import json
import logging
import os
import sys
from datetime import datetime, UTC
from typing import Dict, Optional
from schema.datamodel.bertron_schema_pydantic import Entity

from pymongo import MongoClient, GEOSPHERE
from pymongo.database import Database
from pymongo.errors import ConnectionFailure, PyMongoError
from jsonschema import validate, ValidationError
import httpx


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("bertron-ingest")


class BertronMongoDBIngestor:
    """Class to handle ingestion of BERtron data into MongoDB."""

    def __init__(self, mongo_uri: str, db_name: str, schema_path: str):
        """Initialize the ingestor with connection and schema details."""
        self.mongo_uri: str = mongo_uri
        self.db_name: str = db_name
        self.schema_path: Optional[str] = schema_path
        self.client: Optional[MongoClient] = None
        self.db: Optional[Database] = None
        self.schema: Optional[dict] = None

    def connect(self) -> None:
        """Connect to MongoDB."""
        try:
            logger.info(f"Connecting to MongoDB at {self.mongo_uri}")
            self.client = MongoClient(self.mongo_uri)
            logger.info(f"Using MongoDB database: {self.db_name}")
            self.db = self.client[self.db_name]
        except ConnectionFailure as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            sys.exit(1)

    def clean_collections(self) -> None:
        """Delete existing collections to start fresh."""
        assert self.db is not None, "Connection to database has not been established"
        try:
            collection_names = self.db.list_collection_names()
            if "entities" in collection_names:
                logger.info("Dropping existing 'entities' collection")
                self.db.entities.drop()
                logger.info("Successfully dropped 'entities' collection")
            else:
                logger.info("No existing 'entities' collection found")
        except PyMongoError as e:
            logger.error(f"Error dropping collections: {e}")
            sys.exit(1)

    def load_schema(self) -> Dict:
        """Load the JSON schema from file."""
        assert isinstance(self.schema_path, str), "Schema path has not been set"
        try:
            logger.info(f"Loading schema from {self.schema_path}")
            if self.schema_path.startswith(("http://", "https://")):
                response = httpx.get(self.schema_path)
                response.raise_for_status()
                self.schema = response.json()
            else:
                with open(self.schema_path, "r") as f:
                    self.schema = json.load(f)
            if not isinstance(self.schema, dict):
                raise ValueError("Failed to parse schema into a Python dictionary")
            return self.schema
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load schema: {e}")
            sys.exit(1)

    def validate_data(self, data: Dict) -> bool:
        """Validate data against the loaded schema."""
        assert isinstance(self.schema, dict), "Schema has not been loaded"
        try:
            validate(instance=data, schema=self.schema)
            _ = Entity(**data)  # Validate against Pydantic model
            return True
        except ValidationError as e:
            logger.error(f"Validation error: {e}")
            return False

    def insert_entity(self, entity: Dict) -> Optional[str]:
        """Insert an entity into the 'entities' collection."""
        assert isinstance(self.schema, dict), "Schema has not been loaded"
        assert self.db is not None, "Connection to database has not been established"
        try:
            # Add metadata
            entity["_metadata"] = {
                "ingested_at": datetime.now(UTC),
                "schema_version": self.schema.get("version", "unknown"),
            }

            # convert latitude and longitude to mongoDB GeoJSON format
            if "coordinates" in entity:
                coordinates = entity["coordinates"]
                if (
                    isinstance(coordinates, dict)
                    and "latitude" in coordinates
                    and "longitude" in coordinates
                ):
                    entity["geojson"] = {
                        "type": "Point",
                        "coordinates": [
                            coordinates["longitude"],
                            coordinates["latitude"],
                        ],
                    }
                else:
                    logger.error(
                        f"Invalid coordinates format for entity: {entity.get('name', entity.get('id', 'unnamed'))}"
                    )
                    return None

            # Insert with upsert to handle potential duplicates based on URI
            result = self.db.entities.update_one(
                {"uri": entity["uri"]}, {"$set": entity}, upsert=True
            )

            if result.upserted_id:
                logger.info(
                    f"Inserted entity: {entity.get('name', entity.get('id', 'unnamed'))}"
                )
                return str(result.upserted_id)
            else:
                logger.info(
                    f"Updated entity: {entity.get('name', entity.get('id', 'unnamed'))}"
                )
                return None
        except PyMongoError as e:
            logger.error(f"Error inserting entity: {e}")
            return None

    def create_indexes(self) -> None:
        """Create indexes for the 'entities' collection."""
        assert self.db is not None, "Connection to database has not been established"
        try:
            logger.info("Creating indexes on 'entities' collection")
            self.db.entities.create_index("uri")
            # TODO: enforce unique index on id once ess-dive implements unique ids
            self.db.entities.create_index("id", unique=True)
            self.db.entities.create_index("ber_data_source")
            self.db.entities.create_index("data_type")
            self.db.entities.create_index([("geojson", GEOSPHERE)])
            logger.info("Indexes created successfully")
        except PyMongoError as e:
            logger.error(f"Error creating indexes: {e}")

    def ingest_file(self, filepath: str) -> Dict[str, int]:
        """Ingest entities from a JSON file."""
        stats = {"processed": 0, "valid": 0, "invalid": 0, "inserted": 0, "error": 0}

        try:
            with open(filepath, "r") as f:
                data = json.load(f)

            # Handle both single entity and array of entities
            entities = data if isinstance(data, list) else [data]
            stats["processed"] = len(entities)

            for entity in entities:
                if self.validate_data(entity):
                    stats["valid"] += 1
                    if self.insert_entity(entity):
                        stats["inserted"] += 1
                else:
                    stats["invalid"] += 1

        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Error processing file {filepath}: {e}")
            stats["error"] += 1

        return stats

    def close(self) -> None:
        """Close the MongoDB connection."""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")


def main():
    """Main function to run the ingestor."""
    parser = argparse.ArgumentParser(
        description="Ingest data into MongoDB based on BERtron schema"
    )
    parser.add_argument(
        "--mongo-uri",
        default="mongodb://localhost:27017",
        help="MongoDB connection URI",
    )
    parser.add_argument("--db-name", default="bertron", help="MongoDB database name")
    parser.add_argument(
        "--schema-path",
        default="https://raw.githubusercontent.com/ber-data/bertron-schema/v0.1.0-alpha.11/src/schema/jsonschema/bertron_schema.json",
        help="Path or URL to the BERtron schema JSON file",
    )
    parser.add_argument(
        "--input", required=True, help="Path to the input JSON file or directory"
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Delete existing collections before ingesting new data",
    )

    args = parser.parse_args()

    ingestor = BertronMongoDBIngestor(
        mongo_uri=args.mongo_uri, db_name=args.db_name, schema_path=args.schema_path
    )

    try:
        ingestor.connect()
        ingestor.load_schema()

        # Clean collections if requested
        if args.clean:
            logger.info("Clean flag enabled - removing existing collections")
            ingestor.clean_collections()

        total_stats = {
            "processed": 0,
            "valid": 0,
            "invalid": 0,
            "inserted": 0,
            "error": 0,
        }

        ingestor.create_indexes()  # Create indexes before ingesting data

        # Process a single file or all JSON files in a directory
        if os.path.isdir(args.input):
            for filename in os.listdir(args.input):
                if filename.endswith(".json"):
                    file_path = os.path.join(args.input, filename)
                    logger.info(f"Processing file: {file_path}")
                    stats = ingestor.ingest_file(file_path)
                    for key in total_stats:
                        total_stats[key] += stats[key]
        else:
            # Process a single file
            logger.info(f"Processing file: {args.input}")
            total_stats = ingestor.ingest_file(args.input)

        # Report results
        logger.info("Ingestion completed")
        logger.info(f"Total processed: {total_stats['processed']}")
        logger.info(f"Valid entities: {total_stats['valid']}")
        logger.info(f"Invalid entities: {total_stats['invalid']}")
        logger.info(f"Inserted entities: {total_stats['inserted']}")
        logger.info(f"Errors: {total_stats['error']}")

    finally:
        ingestor.close()


if __name__ == "__main__":
    main()

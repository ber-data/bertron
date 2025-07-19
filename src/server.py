import logging
from typing import Optional, Dict, Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import RedirectResponse
from pymongo import MongoClient
from pydantic import BaseModel, Field
from schema.datamodel import bertron_schema_pydantic
import uvicorn

from .lib.helpers import get_package_version
from models import HealthResponse, VersionResponse, EntitiesResponse

# Set up logging
logger = logging.getLogger(__name__)

# Connect to MongoDB.
# TODO: Get these values from environment variables instead of hard-coding them.
mongo_client = MongoClient("mongo:27017", username="admin", password="root")

app = FastAPI(
    title="BERtron API",
    description=(
        "[View source](https://github.com/ber-data/bertron/blob/main/src/server.py)\n\n"
        f"[BERtron schema](https://ber-data.github.io/bertron-schema/) version: `{get_package_version('bertron-schema')}`"
    ),
    version=get_package_version("bertron"),
)


@app.get("/", include_in_schema=False)
def get_root():
    r"""Redirect to the API documentation page."""
    return RedirectResponse(url="/docs")


@app.get("/health")
def get_health() -> HealthResponse:
    r"""Get system health information."""
    is_database_healthy = len(mongo_client.list_database_names()) > 0
    return HealthResponse(
        web_server=True,
        database=is_database_healthy,
    )


@app.get("/version")
def get_version() -> VersionResponse:
    r"""Get system version information."""
    api_package_name = "bertron"
    bertron_schema_package_name = "bertron-schema"
    return VersionResponse(
        api=get_package_version(api_package_name),
        bertron_schema=get_package_version(bertron_schema_package_name),
    )


@app.get("/bertron", response_model=EntitiesResponse)
def get_all_entities():
    r"""Get all documents from the entities collection."""
    db = mongo_client["bertron"]

    # Check if the collection exists
    if "entities" not in db.list_collection_names():
        raise HTTPException(status_code=404, detail="Entities collection not found")

    collection = db["entities"]
    documents = list(collection.find({}))

    # Convert documents to Entity objects
    entities = []
    for doc in documents:
        entities.append(convert_document_to_entity(doc))

    return {"documents": entities, "count": len(entities)}


class MongoDBQuery(BaseModel):
    filter: Dict[str, Any] = Field(default={}, description="MongoDB find query filter")
    projection: Optional[Dict[str, Any]] = Field(
        default=None, description="Fields to include or exclude"
    )
    skip: Optional[int] = Field(
        default=0, ge=0, description="Number of documents to skip"
    )
    limit: Optional[int] = Field(
        default=100, ge=1, le=1000, description="Maximum number of documents to return"
    )
    sort: Optional[Dict[str, int]] = Field(
        default=None, description="Sort criteria (1 for ascending, -1 for descending)"
    )


@app.post("/bertron/find", response_model=EntitiesResponse)
def find_entities(query: MongoDBQuery):
    r"""Execute a MongoDB find operation on the entities collection with filter, projection, skip, limit, and sort options.

    Example query body:
    {
        "filter": {"field": "value", "number_field": {"$gt": 100}},
        "projection": {"field1": 1, "field2": 1},
        "skip": 0,
        "limit": 100,
        "sort": {"field1": 1, "field2": -1}
    }
    """
    db = mongo_client["bertron"]

    # Check if the collection exists
    if "entities" not in db.list_collection_names():
        raise HTTPException(status_code=404, detail="Entities collection not found")

    collection = db["entities"]

    try:
        # Execute find with query parameters
        cursor = collection.find(filter=query.filter, projection=query.projection)

        # Apply skip, limit, and sort if provided
        if query.sort:
            cursor = cursor.sort(list(query.sort.items()))
        if query.skip:
            cursor = cursor.skip(query.skip)
        if query.limit:
            cursor = cursor.limit(query.limit)

        # Convert cursor to list and convert to Entity objects
        documents = list(cursor)
        entities = []
        for doc in documents:
            entities.append(convert_document_to_entity(doc))

        return {"documents": entities, "count": len(entities)}

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Query error: {str(e)}")


@app.get("/bertron/geo/nearby", response_model=EntitiesResponse)
def find_nearby_entities(
    latitude: float = Query(
        ..., ge=-90, le=90, description="Center latitude in degrees"
    ),
    longitude: float = Query(
        ..., ge=-180, le=180, description="Center longitude in degrees"
    ),
    radius_meters: float = Query(..., gt=0, description="Search radius in meters"),
):
    r"""Find entities within a specified radius of a geographic point using MongoDB's $near operator.

    This endpoint uses MongoDB's geospatial $near query which requires a 2dsphere index
    on the coordinates field for optimal performance.

    Example: /bertron/geo/nearby?latitude=47.6062&longitude=-122.3321&radius_meters=10000
    """
    db = mongo_client["bertron"]

    # Check if the collection exists
    if "entities" not in db.list_collection_names():
        raise HTTPException(status_code=404, detail="Entities collection not found")

    collection = db["entities"]

    try:
        # Build the $near geospatial query
        geo_filter = {
            "geojson": {
                "$near": {
                    "$geometry": {
                        "type": "Point",
                        "coordinates": [
                            longitude,
                            latitude,
                        ],  # MongoDB uses [lng, lat] format
                    },
                    "$maxDistance": radius_meters,
                }
            }
        }

        # Execute find with geospatial filter
        cursor = collection.find(filter=geo_filter)

        # Convert cursor to list and convert to Entity objects
        documents = list(cursor)
        entities = []
        for doc in documents:
            entities.append(convert_document_to_entity(doc))

        return {"documents": entities, "count": len(entities)}

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Nearby query error: {str(e)}")


@app.get("/bertron/geo/bbox", response_model=EntitiesResponse)
def find_entities_in_bounding_box(
    southwest_lat: float = Query(
        ..., ge=-90, le=90, description="Southwest corner latitude"
    ),
    southwest_lng: float = Query(
        ..., ge=-180, le=180, description="Southwest corner longitude"
    ),
    northeast_lat: float = Query(
        ..., ge=-90, le=90, description="Northeast corner latitude"
    ),
    northeast_lng: float = Query(
        ..., ge=-180, le=180, description="Northeast corner longitude"
    ),
):
    r"""Find entities within a bounding box using MongoDB's $geoWithin operator.

    This endpoint finds all entities whose coordinates fall within the specified
    rectangular bounding box defined by southwest and northeast corners.

    Example: /bertron/geo/bbox?southwest_lat=47.5&southwest_lng=-122.4&northeast_lat=47.7&northeast_lng=-122.2
    """
    db = mongo_client["bertron"]

    # Check if the collection exists
    if "entities" not in db.list_collection_names():
        raise HTTPException(status_code=404, detail="Entities collection not found")

    collection = db["entities"]

    try:
        # Validate bounding box coordinates
        if southwest_lat >= northeast_lat:
            raise HTTPException(
                status_code=400,
                detail="Southwest latitude must be less than northeast latitude",
            )
        if southwest_lng >= northeast_lng:
            raise HTTPException(
                status_code=400,
                detail="Southwest longitude must be less than northeast longitude",
            )

        # Build the $geoWithin bounding box query
        geo_filter = {
            "geojson": {
                "$geoWithin": {
                    "$box": [
                        [
                            southwest_lng,
                            southwest_lat,
                        ],  # MongoDB uses [lng, lat] format
                        [northeast_lng, northeast_lat],
                    ]
                }
            }
        }

        # Execute find with geospatial filter
        cursor = collection.find(filter=geo_filter)

        # Convert cursor to list and convert to Entity objects
        documents = list(cursor)
        entities = []
        for doc in documents:
            entities.append(convert_document_to_entity(doc))

        return {"documents": entities, "count": len(entities)}

    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Bounding box query error: {str(e)}"
        )


@app.get("/bertron/{id}", response_model=bertron_schema_pydantic.Entity)
def get_entity_by_id(id: str):
    r"""Get a single entity by its ID.

    Example: /bertron/emsl:12345
    """
    db = mongo_client["bertron"]

    # Check if the collection exists
    if "entities" not in db.list_collection_names():
        raise HTTPException(status_code=404, detail="Entities collection not found")

    collection = db["entities"]

    try:
        # Find the entity by ID - get all fields for proper validation
        document = collection.find_one(filter={"id": id})

        if not document:
            raise HTTPException(
                status_code=404, detail=f"Entity with id '{id}' not found"
            )

        # Validate and create Entity instance
        try:
            entity = convert_document_to_entity(document)
            return entity
        except Exception as validation_error:
            logger.error(f"Entity validation failed for id '{id}': {validation_error}")
            raise HTTPException(
                status_code=500,
                detail=f"Entity data validation failed: {str(validation_error)}",
            )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Query error: {str(e)}")


def convert_document_to_entity(
    document: Dict[str, Any],
) -> Optional[bertron_schema_pydantic.Entity]:
    """Convert a MongoDB document to an Entity object."""
    # Remove MongoDB _id, metadata, geojson
    document.pop("_id", None)
    document.pop("_metadata", None)
    document.pop("geojson", None)

    return bertron_schema_pydantic.Entity(**document)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

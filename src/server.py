import json
import logging
from typing import Optional, Dict, Any, Union

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import RedirectResponse
from pymongo import MongoClient
from scalar_fastapi import get_scalar_api_reference
from schema.datamodel.bertron_schema_pydantic import Entity
import uvicorn

from config import settings as cfg
from lib.helpers import get_package_version
from models import (
    EntitiesResponse,
    FindResponse,
    HealthResponse,
    MongoFindQueryDescriptor,
    VersionResponse,
)


# Set up logging
logger = logging.getLogger(__name__)

# Connect to the MongoDB server.
mongo_client = MongoClient(
    f"{cfg.mongo_host}:{cfg.mongo_port}",
    username=cfg.mongo_username,
    password=cfg.mongo_password,
)

app = FastAPI(
    title="BERtron API",
    description=(
        "[View source](https://github.com/ber-data/bertron/blob/main/src/server.py)\n\n"
        f"[BERtron schema](https://ber-data.github.io/bertron-schema/) version: `{get_package_version('bertron-schema')}`"
    ),
    version=f"{get_package_version('bertron')}",
)


@app.get("/scalar", include_in_schema=False)
async def get_scalar_html():
    r"""
    Returns the HTML markup for an interactive API docs web page powered by Scalar.

    Note: This can coexist with FastAPI's built-in Swagger UI page.
    """
    return get_scalar_api_reference(
        openapi_url=app.openapi_url,
        title="BERtron API",
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


@app.get("/bertron")
def get_all_entities() -> EntitiesResponse:
    r"""Get all documents from the entities collection."""
    db = mongo_client[cfg.mongo_database]

    # Check if the collection exists
    if "entities" not in db.list_collection_names():
        raise HTTPException(status_code=404, detail="Entities collection not found")

    collection = db["entities"]
    documents = list(collection.find({}))

    # Convert documents to Entity objects
    entities = []
    for doc in documents:
        entities.append(Entity(**clean_document(doc)))

    return EntitiesResponse(documents=entities, count=len(entities))


@app.post("/bertron/find")
def find_entities(
    query: MongoFindQueryDescriptor,
) -> Union[EntitiesResponse, FindResponse]:
    r"""Execute a MongoDB find operation on the entities collection with filter, projection, skip, limit, and sort options.

    Returns EntitiesResponse (validated Entity objects) when no projection is specified,
    or FindResponse (raw documents) when projection is used.

    Example query body:
    {
        "filter": {"field": "value", "number_field": {"$gt": 100}},
        "projection": {"field1": 1, "field2": 1},
        "skip": 0,
        "limit": 100,
        "sort": {"field1": 1, "field2": -1}
    }
    """
    db = mongo_client[cfg.mongo_database]

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

        # Convert cursor to list
        documents = list(cursor)

        # Return different response types based on whether projection is used
        if query.projection:
            # When projection is used, return raw documents as FindResponse
            # Remove MongoDB internal fields
            cleaned_documents = []
            for doc in documents:
                cleaned_documents.append(clean_document(doc))

            return FindResponse(
                documents=cleaned_documents, count=len(cleaned_documents)
            )
        else:
            # When no projection, return validated Entity objects as EntitiesResponse
            entities = []
            for doc in documents:
                entities.append(Entity(**clean_document(doc)))

            return EntitiesResponse(documents=entities, count=len(entities))

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Query error: {str(e)}")


@app.get("/bertron/geo/nearby")
def find_nearby_entities(
    latitude: float = Query(
        ..., ge=-90, le=90, description="Center latitude in degrees"
    ),
    longitude: float = Query(
        ..., ge=-180, le=180, description="Center longitude in degrees"
    ),
    radius_meters: float = Query(..., gt=0, description="Search radius in meters"),
    filter_json: Optional[str] = Query(
        None, description="Optional JSON string containing MongoDB-style filter criteria to refine search results"
    ),
) -> EntitiesResponse:
    r"""Find entities within a specified radius of a geographic point using MongoDB's $near operator.

    This endpoint uses MongoDB's geospatial $near query which requires a 2dsphere index
    on the coordinates field for optimal performance. An optional filter_json parameter can be
    provided as a JSON string to further refine the results.

    Example: /bertron/geo/nearby?latitude=47.6062&longitude=-122.3321&radius_meters=10000
    Example with filter: /bertron/geo/nearby?latitude=47.6062&longitude=-122.3321&radius_meters=10000&filter_json={"type":"sample"}
    """
    db = mongo_client[cfg.mongo_database]

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

        # Parse and combine with optional filter if provided
        final_filter = geo_filter
        if filter_json:
            try:
                additional_filter = json.loads(filter_json)
                # Combine geospatial and additional filters using $and
                final_filter = {"$and": [geo_filter, additional_filter]}
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=400, 
                    detail="Invalid JSON format in filter_json parameter"
                )

        # Execute find with combined filter
        cursor = collection.find(filter=final_filter)

        # Convert cursor to list and convert to Entity objects
        documents = list(cursor)
        entities = []
        for doc in documents:
            entities.append(Entity(**clean_document(doc)))

        return EntitiesResponse(documents=entities, count=len(entities))

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Nearby query error: {str(e)}")


@app.get("/bertron/geo/bbox")
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
    filter_json: Optional[str] = Query(
        None, description="Optional JSON string containing MongoDB-style filter criteria to refine search results"
    ),
) -> EntitiesResponse:
    r"""Find entities within a bounding box using MongoDB's $geoWithin operator.

    This endpoint finds all entities whose coordinates fall within the specified
    rectangular bounding box defined by southwest and northeast corners. An optional 
    filter_json parameter can be provided as a JSON string to further refine the results.

    Example: /bertron/geo/bbox?southwest_lat=47.5&southwest_lng=-122.4&northeast_lat=47.7&northeast_lng=-122.2
    Example with filter: /bertron/geo/bbox?southwest_lat=47.5&southwest_lng=-122.4&northeast_lat=47.7&northeast_lng=-122.2&filter_json={"type":"sample"}
    """
    db = mongo_client[cfg.mongo_database]

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

        # Parse and combine with optional filter if provided
        final_filter = geo_filter
        if filter_json:
            try:
                additional_filter = json.loads(filter_json)
                # Combine geospatial and additional filters using $and
                final_filter = {"$and": [geo_filter, additional_filter]}
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=400, 
                    detail="Invalid JSON format in filter_json parameter"
                )

        # Execute find with combined filter
        cursor = collection.find(filter=final_filter)

        # Convert cursor to list and convert to Entity objects
        documents = list(cursor)
        entities = []
        for doc in documents:
            entities.append(Entity(**clean_document(doc)))

        return EntitiesResponse(documents=entities, count=len(entities))

    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Bounding box query error: {str(e)}"
        )


@app.get("/bertron/{id:path}")
def get_entity_by_id(id: str) -> Optional[Entity]:
    r"""Get a single entity by its ID.

    Example: /bertron/emsl:12345
    """
    db = mongo_client[cfg.mongo_database]

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
            entity = Entity(**clean_document(document))
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


def clean_document(
    document: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Removes fields from the MongoDB document, that don't exist on the `Entity` model.

    This function was designed to remove the `_id`, `_metadata`, and `geojson` fields
    from the document.

    >>> clean_document({"_id": "123", "_metadata": {}, "geojson": {}, "name": "Test"})
    {'name': 'Test'}
    >>> clean_document({})
    {}
    """

    # Determine the names of the fields that the Entity model has.
    model_field_names = Entity.model_fields.keys()

    # Remove all _other_ fields from the document.
    for key in list(document.keys()):
        if key not in model_field_names:
            document.pop(key)

    return document


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

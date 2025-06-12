from fastapi import FastAPI, HTTPException, Query
import uvicorn
from fastapi.responses import RedirectResponse
from pymongo import MongoClient
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
import json

# Connect to MongoDB.
# TODO: Get these values from environment variables instead of hard-coding them.
mongo_client = MongoClient("mongo:27017", username="admin", password="root")

app = FastAPI()


@app.get("/", include_in_schema=False)
def get_root():
    r"""Redirect to the API documentation page."""
    return RedirectResponse(url="/docs")


@app.get("/health")
def get_health():
    r"""Get API health information."""
    is_database_healthy = len(mongo_client.list_database_names()) > 0
    return {"web_server": "ok", "database": is_database_healthy}


@app.get("/bertron")
def get_all_entities():
    r"""Get all documents from the entities collection."""
    db = mongo_client["bertron"]
    
    # Check if the collection exists
    if "entities" not in db.list_collection_names():
        raise HTTPException(status_code=404, detail="Entities collection not found")

    collection = db["entities"]
    documents = list(collection.find({}))

    # Remove the MongoDB '_id' field from each document for JSON serialization
    for doc in documents:
        doc.pop("_id", None)

    return {"documents": documents}


class MongoDBQuery(BaseModel):
    filter: Dict[str, Any] = Field(default={}, description="MongoDB find query filter")
    projection: Optional[Dict[str, Any]] = Field(default=None, description="Fields to include or exclude")
    skip: Optional[int] = Field(default=0, ge=0, description="Number of documents to skip")
    limit: Optional[int] = Field(default=100, ge=1, le=1000, description="Maximum number of documents to return")
    sort: Optional[Dict[str, int]] = Field(default=None, description="Sort criteria (1 for ascending, -1 for descending)")


@app.post("/bertron/find")
def find_entities(
    query: MongoDBQuery
):
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
        cursor = collection.find(
            filter=query.filter,
            projection=query.projection
        )
        
        # Apply skip, limit, and sort if provided
        if query.sort:
            cursor = cursor.sort(list(query.sort.items()))
        if query.skip:
            cursor = cursor.skip(query.skip)
        if query.limit:
            cursor = cursor.limit(query.limit)
            
        # Convert cursor to list and remove MongoDB _id
        documents = list(cursor)
        for doc in documents:
            doc.pop("_id", None)
            
        return {"documents": documents, "count": len(documents)}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Query error: {str(e)}")


@app.get("/bertron/geo/nearby")
def find_nearby_entities(
    latitude: float = Query(..., ge=-90, le=90, description="Center latitude in degrees"),
    longitude: float = Query(..., ge=-180, le=180, description="Center longitude in degrees"),
    radius_meters: float = Query(..., gt=0, description="Search radius in meters")
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
            "coordinates": {
                "$near": {
                    "$geometry": {
                        "type": "Point",
                        "coordinates": [longitude, latitude]  # MongoDB uses [lng, lat] format
                    },
                    "$maxDistance": radius_meters
                }
            }
        }
        
        # Execute find with geospatial filter and fixed projection
        cursor = collection.find(
            filter=geo_filter,
            projection={"id": 1, "name": 1, "uri": 1, "ber_data_source": 1, "coordinates": 1}
        )
            
        # Convert cursor to list and remove MongoDB _id
        documents = list(cursor)
        for doc in documents:
            doc.pop("_id", None)
            
        return {
            "documents": documents,
            "count": len(documents),
            "query_type": "nearby",
            "center": {
                "latitude": latitude,
                "longitude": longitude
            },
            "radius_meters": radius_meters
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Nearby query error: {str(e)}")


@app.get("/bertron/geo/bbox")
def find_entities_in_bounding_box(
    southwest_lat: float = Query(..., ge=-90, le=90, description="Southwest corner latitude"),
    southwest_lng: float = Query(..., ge=-180, le=180, description="Southwest corner longitude"),
    northeast_lat: float = Query(..., ge=-90, le=90, description="Northeast corner latitude"),
    northeast_lng: float = Query(..., ge=-180, le=180, description="Northeast corner longitude")
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
            raise HTTPException(status_code=400, detail="Southwest latitude must be less than northeast latitude")
        if southwest_lng >= northeast_lng:
            raise HTTPException(status_code=400, detail="Southwest longitude must be less than northeast longitude")
        
        # Build the $geoWithin bounding box query
        geo_filter = {
            "coordinates": {
                "$geoWithin": {
                    "$box": [
                        [southwest_lng, southwest_lat],  # MongoDB uses [lng, lat] format
                        [northeast_lng, northeast_lat]
                    ]
                }
            }
        }
        
        # Execute find with geospatial filter and fixed projection
        cursor = collection.find(
            filter=geo_filter,
            projection={"id": 1, "name": 1, "uri": 1, "ber_data_source": 1, "coordinates": 1}
        )
            
        # Convert cursor to list and remove MongoDB _id
        documents = list(cursor)
        for doc in documents:
            doc.pop("_id", None)
            
        return {
            "documents": documents,
            "count": len(documents),
            "query_type": "bounding_box",
            "bounding_box": {
                "southwest": {
                    "latitude": southwest_lat,
                    "longitude": southwest_lng
                },
                "northeast": {
                    "latitude": northeast_lat,
                    "longitude": northeast_lng
                }
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Bounding box query error: {str(e)}")


@app.get("/bertron/{id}")
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
        # Find the entity by ID with fixed projection
        document = collection.find_one(
            filter={"id": id},
        )
        
        if not document:
            raise HTTPException(status_code=404, detail=f"Entity with id '{id}' not found")
        
        # Remove MongoDB _id
        document.pop("_id", None)
        
        return document
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Query error: {str(e)}")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

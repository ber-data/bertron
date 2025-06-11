#!/usr/bin/env python3
"""
Geospatial Query Tool for MongoDB

This script provides utilities for querying geospatial data 
imported into MongoDB by the geo_importer.py script.

Usage:
    python geo_query.py --action <query_type> [options]
"""

import argparse
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
from pymongo import MongoClient
from pymongo.collection import Collection
import folium
from folium.plugins import MarkerCluster

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('geo-query')


class GeoQuery:
    """MongoDB geospatial data query utilities."""
    
    def __init__(self, connection_string: str = "mongodb://localhost:27017"):
        """Initialize MongoDB connection.
        
        Args:
            connection_string: MongoDB connection URI
        """
        self.client = MongoClient(connection_string)
        self.db = self.client.geospatialDB
        self.collection = self.db.locations
        
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the data in the collection.
        
        Returns:
            Dictionary with statistics
        """
        logger.info("Retrieving collection statistics")
        
        total = self.collection.count_documents({})
        
        # Count by dataset type
        emsl_count = self.collection.count_documents({
            'dataset_id': {'$regex': '^emsl'}
        })
        
        ess_dive_count = self.collection.count_documents({
            'dataset_id': {'$regex': '^ess-dive'}
        })
        
        nmdc_count = self.collection.count_documents({
            'dataset_id': {'$regex': '^nmdc:'}
        })
        
        jgi_count = self.collection.count_documents({
            'dataset_id': {'$regex': '^jgi:'}
        })

        # Get bounding box
        bounds = list(self.collection.aggregate([
            {
                '$group': {
                    '_id': None,
                    'minLat': {'$min': {'$arrayElemAt': ['$coordinates.coordinates', 1]}},
                    'maxLat': {'$max': {'$arrayElemAt': ['$coordinates.coordinates', 1]}},
                    'minLng': {'$min': {'$arrayElemAt': ['$coordinates.coordinates', 0]}},
                    'maxLng': {'$max': {'$arrayElemAt': ['$coordinates.coordinates', 0]}}
                }
            }
        ]))
        
        boundary = bounds[0] if bounds else None
        
        return {
            'total': total,
            'dataset_counts': {
                'proposals': proposal_count,
                'ess_dive': ess_dive_count,
                'nmdc': nmdc_count,
                'nmdc': jgi_count,
                'other': total - (proposal_count + ess_dive_count + nmdc_count)
            },
            'bounds': {
                'south': boundary['minLat'],
                'north': boundary['maxLat'],
                'west': boundary['minLng'],
                'east': boundary['maxLng']
            } if boundary else None
        }

    def find_by_system(self, system_name: str, limit: int = 1000) -> List[Dict[str, Any]]:
        """Find all points from a specific system.
        
        Args:
            system_name: The system name to search for
            limit: Maximum number of results to return
            
        Returns:
            List of matching documents
        """
        logger.info(f"Searching for system: {system_name}")
        
        cursor = self.collection.find({'system_name': system_name}).limit(limit)
        return list(cursor)
        
        
    def find_by_dataset(self, dataset_id: str) -> List[Dict[str, Any]]:
        """Find all points in a specific dataset.
        
        Args:
            dataset_id: The dataset ID to search for
            
        Returns:
            List of matching documents
        """
        logger.info(f"Searching for dataset: {dataset_id}")
        
        cursor = self.collection.find({'dataset_id': dataset_id})
        return list(cursor)
        
    def find_in_box(self, west: float, south: float, east: float, north: float, 
                    limit: int = 1000) -> List[Dict[str, Any]]:
        """Find points within a bounding box.
        
        Args:
            west: Western longitude
            south: Southern latitude
            east: Eastern longitude
            north: Northern latitude
            limit: Maximum number of results to return
            
        Returns:
            List of documents within the bounding box
        """
        logger.info(f"Searching within box: W:{west}, S:{south}, E:{east}, N:{north}")
        
        query = {
            'coordinates': {
                '$geoWithin': {
                    '$geometry': {
                        'type': 'Polygon',
                        'coordinates': [[
                            [west, south],
                            [east, south],
                            [east, north],
                            [west, north],
                            [west, south]
                        ]]
                    }
                }
            }
        }
        
        cursor = self.collection.find(query).limit(limit)
        return list(cursor)
        
    def find_nearby(self, lat: float, lng: float, 
                    distance: int = 10000, limit: int = 100) -> List[Dict[str, Any]]:
        """Find points near a specific location.
        
        Args:
            lat: Latitude
            lng: Longitude
            distance: Maximum distance in meters
            limit: Maximum number of results to return
            
        Returns:
            List of nearby documents
        """
        logger.info(f"Searching near point ({lat}, {lng}) within {distance}m")
        
        query = {
            'coordinates': {
                '$near': {
                    '$geometry': {
                        'type': 'Point',
                        'coordinates': [lng, lat]
                    },
                    '$maxDistance': distance
                }
            }
        }
        
        cursor = self.collection.find(query).limit(limit)
        return list(cursor)
        
    def create_map(self, points: List[Dict[str, Any]], 
                   output_file: str = 'geo_map.html') -> None:
        """Create an interactive map visualization of points.
        
        Args:
            points: List of documents with coordinates
            output_file: Path to save the HTML map file
        """
        logger.info(f"Creating map with {len(points)} points")
        
        if not points:
            logger.warning("No points to visualize")
            return
            
        # Calculate center point
        lats = [p['coordinates']['coordinates'][1] for p in points if 'coordinates' in p]
        lngs = [p['coordinates']['coordinates'][0] for p in points if 'coordinates' in p]
        
        if not lats or not lngs:
            logger.warning("No valid coordinates found")
            return
            
        center_lat = sum(lats) / len(lats)
        center_lng = sum(lngs) / len(lngs)
        
        # Create map
        m = folium.Map(location=[center_lat, center_lng], zoom_start=4)
        
        # Add marker cluster
        marker_cluster = MarkerCluster().add_to(m)
        
        # Add markers
        for point in points:
            if 'coordinates' not in point:
                continue
                
            coords = point['coordinates']['coordinates']
            if len(coords) < 2:
                continue
                
            # Get point details
            dataset_id = point.get('dataset_id', 'Unknown')
            system_name = point.get('system_name', 'Unknown')
            
            # Get metadata if available
            metadata = point.get('metadata', {})
            description = metadata.get('description', '')
            source = metadata.get('source', 'Unknown source')
            
            # Create popup content
            popup_content = f"""
            <strong>Dataset:</strong> {dataset_id}<br>
            <strong>System:</strong> {system_name}<br>
            <strong>Coordinates:</strong> {coords[1]}, {coords[0]}<br>
            <strong>Source:</strong> {source}<br>
            """
            
            if description:
                popup_content += f"<strong>Description:</strong> {description}<br>"
                
            # Add marker
            folium.Marker(
                location=[coords[1], coords[0]],
                popup=folium.Popup(popup_content, max_width=300),
                tooltip=system_name
            ).add_to(marker_cluster)
            
        # Save map
        m.save(output_file)
        logger.info(f"Map saved to {output_file}")
        
    def export_to_csv(self, points: List[Dict[str, Any]], 
                      output_file: str = 'geo_data.csv') -> None:
        """Export query results to CSV.
        
        Args:
            points: List of documents
            output_file: Path to save the CSV file
        """
        logger.info(f"Exporting {len(points)} points to CSV")
        
        if not points:
            logger.warning("No points to export")
            return
            
        # Prepare data for DataFrame
        rows = []
        for point in points:
            row = {
                'dataset_id': point.get('dataset_id', ''),
                'system_name': point.get('system_name', '')
            }
            
            # Add coordinates
            if 'coordinates' in point and 'coordinates' in point['coordinates']:
                coords = point['coordinates']['coordinates']
                if len(coords) >= 2:
                    row['longitude'] = coords[0]
                    row['latitude'] = coords[1]
            
            # Add metadata fields
            metadata = point.get('metadata', {})
            for key, value in metadata.items():
                row[f'metadata_{key}'] = value
                
            rows.append(row)
            
        # Create DataFrame and export
        df = pd.DataFrame(rows)
        df.to_csv(output_file, index=False)
        logger.info(f"Data exported to {output_file}")
        
    def close(self) -> None:
        """Close the MongoDB connection."""
        self.client.close()
        logger.info("MongoDB connection closed")


def main():
    """Main function to run queries."""
    parser = argparse.ArgumentParser(description='Query geospatial data from MongoDB')
    parser.add_argument('--mongodb-uri', type=str, default='mongodb://localhost:27017',
                        help='MongoDB connection string')
    parser.add_argument('--action', type=str, required=True, 
                        choices=['stats', 'dataset', 'system', 'box', 'nearby', 'map'],
                        help='Query action to perform')
    
    # Parameters for different query types
    parser.add_argument('--system-name', type=str,
                        help='System name for system queries')
    parser.add_argument('--dataset-id', type=str,
                        help='Dataset ID for dataset queries')
    parser.add_argument('--lat', type=float,
                        help='Latitude for nearby queries')
    parser.add_argument('--lng', type=float,
                        help='Longitude for nearby queries')
    parser.add_argument('--distance', type=int, default=10000,
                        help='Distance in meters for nearby queries')
    parser.add_argument('--west', type=float,
                        help='Western longitude for box queries')
    parser.add_argument('--south', type=float,
                        help='Southern latitude for box queries')
    parser.add_argument('--east', type=float,
                        help='Eastern longitude for box queries')
    parser.add_argument('--north', type=float,
                        help='Northern latitude for box queries')
    parser.add_argument('--limit', type=int, default=100000,
                        help='Maximum number of results')
    parser.add_argument('--output', type=str, default='output',
                        help='Output file name prefix (without extension)')
    parser.add_argument('--format', type=str, choices=['json', 'csv', 'map'], default='json',
                        help='Output format')
    
    args = parser.parse_args()
    
    # Initialize query object
    query = GeoQuery(args.mongodb_uri)
    
    try:
        # Perform the requested action
        if args.action == 'stats':
            # Get collection statistics
            stats = query.get_stats()
            print(json.dumps(stats, indent=2))
            
            # Save to file if requested
            if args.format == 'json':
                with open(f"{args.output}.json", 'w') as f:
                    json.dump(stats, f, indent=2)
                logger.info(f"Statistics saved to {args.output}.json")
                
        elif args.action == 'dataset':
            # Validate parameters
            if not args.dataset_id:
                logger.error("Missing dataset-id parameter")
                return 1
                
            # Query by dataset ID
            results = query.find_by_dataset(args.dataset_id)
            logger.info(f"Found {len(results)} records for dataset {args.dataset_id}")
            
            # Output results
            if args.format == 'json':
                with open(f"{args.output}.json", 'w') as f:
                    json.dump(results, f, indent=2, default=str)
                logger.info(f"Results saved to {args.output}.json")
            elif args.format == 'csv':
                query.export_to_csv(results, f"{args.output}.csv")
            elif args.format == 'map':
                query.create_map(results, f"{args.output}.html")

        elif args.action == 'system':
            # Validate parameters
            if not args.system_name:
                logger.error("Missing system-name parameter")
                return 1
                
            # Query by system name
            results = query.find_by_system(args.system_name, args.limit)
            logger.info(f"Found {len(results)} records for system {args.system_name}")
            
            # Output results
            if args.format == 'json':
                with open(f"{args.output}.json", 'w') as f:
                    json.dump(results, f, indent=2, default=str)
                logger.info(f"Results saved to {args.output}.json")
            elif args.format == 'csv':
                query.export_to_csv(results, f"{args.output}.csv")
            elif args.format == 'map':
                query.create_map(results, f"{args.output}.html")                
         
        elif args.action == 'box':
            # Validate parameters
            if None in [args.west, args.south, args.east, args.north]:
                logger.error("Missing bounding box parameters (west, south, east, north)")
                return 1
                
            # Query within bounding box
            results = query.find_in_box(
                args.west, args.south, args.east, args.north, args.limit
            )
            logger.info(f"Found {len(results)} records in bounding box")
            
            # Output results
            if args.format == 'json':
                with open(f"{args.output}.json", 'w') as f:
                    json.dump(results, f, indent=2, default=str)
                logger.info(f"Results saved to {args.output}.json")
            elif args.format == 'csv':
                query.export_to_csv(results, f"{args.output}.csv")
            elif args.format == 'map':
                query.create_map(results, f"{args.output}.html")
                
        elif args.action == 'nearby':
            # Validate parameters
            if None in [args.lat, args.lng]:
                logger.error("Missing location parameters (lat, lng)")
                return 1
                
            # Query nearby points
            results = query.find_nearby(
                args.lat, args.lng, args.distance, args.limit
            )
            logger.info(f"Found {len(results)} records near ({args.lat}, {args.lng})")
            
            # Output results
            if args.format == 'json':
                with open(f"{args.output}.json", 'w') as f:
                    json.dump(results, f, indent=2, default=str)
                logger.info(f"Results saved to {args.output}.json")
            elif args.format == 'csv':
                query.export_to_csv(results, f"{args.output}.csv")
            elif args.format == 'map':
                query.create_map(results, f"{args.output}.html")
                
        elif args.action == 'map':
            # Create a map with all points (limited by --limit)
            results = list(query.collection.find().limit(args.limit))
            logger.info(f"Found {len(results)} records for map")
            query.create_map(results, f"{args.output}.html")
                
    finally:
        # Close connection
        query.close()
        
    return 0


if __name__ == "__main__":
    exit(main())

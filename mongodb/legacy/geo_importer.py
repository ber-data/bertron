#!/usr/bin/env python3
"""
Geospatial Data Import Tool for MongoDB

This script imports geospatial data from three different sources:
1. latlon_project_ids.json - Project location data
2. ess_dive_packages.csv - ESS-DIVE package centroids 
3. nmdc_biosample_geo_coordinates.csv - NMDC biosample locations

Usage:
    python geo_importer.py --data-dir /path/to/data/files
"""

import os
import json
import argparse
import logging
from typing import Dict, List, Any, Optional, Union
import csv
import pandas as pd
from pymongo import MongoClient, GEOSPHERE
from pymongo.collection import Collection
from pymongo.errors import BulkWriteError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('geo-importer')


class MongoDBImporter:
    """MongoDB geospatial data importer."""
    
    def __init__(self, connection_string: str = "mongodb://localhost:27017"):
        """Initialize MongoDB connection.
        
        Args:
            connection_string: MongoDB connection URI
        """
        self.client = MongoClient(connection_string)
        self.db = self.client.geospatialDB
        self.collection = self.db.locations
        
        # Ensure indexes
        self._create_indexes()
        
    def _create_indexes(self) -> None:
        """Create necessary indexes on the collection."""
        self.collection.create_index([("coordinates", GEOSPHERE)])
        self.collection.create_index("dataset_id")
        self.collection.create_index("system_name")
        logger.info("Database indexes created or verified")
        
    def import_proposal_locations(self, file_path: str) -> int:
        """Import data from the proposal locations JSON file.
        
        Args:
            file_path: Path to the latlon_project_ids.json file
            
        Returns:
            Number of documents imported
        """
        logger.info(f"Processing proposal locations from {file_path}")
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                
            if not data:
                logger.warning("Empty proposal data file")
                return 0
                
            # Transform the data into MongoDB documents
            documents = []
            for item in data:
                try:
                    latitude = float(item.get('latitude'))
                    longitude = float(item.get('longitude'))
                    
                    if not (latitude and longitude):
                        logger.warning(f"Missing coordinates in item: {item}")
                        continue
                        
                    documents.append({
                        'dataset_id': item.get('proposal_id'),
                        'system_name': "EMSL",
                        'coordinates': {
                            'type': 'Point', 
                            'coordinates': [longitude, latitude]
                        },
                        'metadata': {
                            'sampling_set': item.get('sampling_set'),
                            'description': item.get('description'),
                            'source': 'project_locations'
                        }
                    })
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error processing item {item}: {e}")
                    continue
            
            if documents:
                result = self.collection.insert_many(documents)
                logger.info(f"Inserted {len(result.inserted_ids)} proposal location documents")
                return len(result.inserted_ids)
            else:
                logger.warning("No valid proposal documents to insert")
                return 0
                
        except Exception as e:
            logger.error(f"Error importing proposal locations: {e}")
            raise
            
    def import_ess_dive_packages(self, file_path: str) -> int:
        """Import data from the ESS-DIVE packages CSV file.
        
        Args:
            file_path: Path to the ess_dive_packages.csv file
            
        Returns:
            Number of documents imported
        """
        logger.info(f"Processing ESS-DIVE packages from {file_path}")
        
        try:
            # Use pandas for efficient CSV handling
            df = pd.read_csv(file_path)
            
            if df.empty:
                logger.warning("Empty ESS-DIVE data file")
                return 0
                
            # Transform into MongoDB documents
            documents = []
            for _, row in df.iterrows():
                try:
                    latitude = float(row.get('centroid_latitude'))
                    longitude = float(row.get('centroid_longitude'))
                    
                    if pd.isna(latitude) or pd.isna(longitude):
                        continue
                        
                    documents.append({
                        'dataset_id': row.get('package_id'),
                        'system_name': 'ESSDIVE',
                        'coordinates': {
                            'type': 'Point',
                            'coordinates': [longitude, latitude]
                        },
                        'metadata': {
                            'source': 'ESS-DIVE',
                            'row_id': int(row.get('Unnamed: 0')) if not pd.isna(row.get('Unnamed: 0')) else None
                        }
                    })
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error processing ESS-DIVE row: {e}")
                    continue
            
            if documents:
                # Use bulk insert for better performance
                result = self.collection.insert_many(documents)
                logger.info(f"Inserted {len(result.inserted_ids)} ESS-DIVE package documents")
                return len(result.inserted_ids)
            else:
                logger.warning("No valid ESS-DIVE documents to insert")
                return 0
                
        except Exception as e:
            logger.error(f"Error importing ESS-DIVE packages: {e}")
            raise
            
    def import_nmdc_biosamples(self, file_path: str) -> int:
        """Import data from the NMDC biosample coordinates CSV file.
        
        Args:
            file_path: Path to the nmdc_biosample_geo_coordinates.csv file
            
        Returns:
            Number of documents imported
        """
        logger.info(f"Processing NMDC biosamples from {file_path}")
        
        try:
            # Use pandas for efficient CSV handling
            df = pd.read_csv(file_path)
            
            if df.empty:
                logger.warning("Empty NMDC biosample data file")
                return 0
                
            # Transform into MongoDB documents
            documents = []
            for _, row in df.iterrows():
                try:
                    latitude = float(row.get('latitude'))
                    longitude = float(row.get('longitude'))
                    
                    if pd.isna(latitude) or pd.isna(longitude):
                        continue
                        
                    documents.append({
                        'dataset_id': row.get('biosample_id'),
                        'system_name': 'NMDC',
                        'coordinates': {
                            'type': 'Point',
                            'coordinates': [longitude, latitude]
                        },
                        'metadata': {
                            'source': 'NMDC-Biosample'
                        }
                    })
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error processing NMDC biosample row: {e}")
                    continue
            
            if documents:
                # Use bulk insert for better performance
                result = self.collection.insert_many(documents)
                logger.info(f"Inserted {len(result.inserted_ids)} NMDC biosample documents")
                return len(result.inserted_ids)
            else:
                logger.warning("No valid NMDC biosample documents to insert")
                return 0
                
        except Exception as e:
            logger.error(f"Error importing NMDC biosamples: {e}")
            raise
            
    def import_jgi_gold_biosamples(self, file_path: str) -> int:
        """Import data from the JGI GOLD biosample coordinates CSV file.
        
        Args:
            file_path: Path to the jgi_gold_biosample_geo.csv file
            
        Returns:
            Number of documents imported
        """
        logger.info(f"Processing JGI GOLD biosamples from {file_path}")
        
        try:
            # Use pandas for efficient CSV handling
            df = pd.read_csv(file_path)
            
            if df.empty:
                logger.warning("Empty JGI GOLD biosample data file")
                return 0
                
            # Transform into MongoDB documents
            documents = []
            for _, row in df.iterrows():
                try:
                    latitude = float(row.get('latitude'))
                    longitude = float(row.get('longitude'))
                    
                    if pd.isna(latitude) or pd.isna(longitude):
                        continue
                        
                    documents.append({
                        'dataset_id': row.get('gold_id'),
                        'system_name': 'JGI-Biosamples',
                        'coordinates': {
                            'type': 'Point',
                            'coordinates': [longitude, latitude]
                        },
                        'metadata': {
                            'source': 'JGI-GOLD-Biosample'
                        }
                    })
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error processing JGI GOLD biosample row: {e}")
                    continue
            
            if documents:
                # Use bulk insert for better performance
                result = self.collection.insert_many(documents)
                logger.info(f"Inserted {len(result.inserted_ids)} JGI GOLD biosample documents")
                return len(result.inserted_ids)
            else:
                logger.warning("No valid JGI GOLD biosample documents to insert")
                return 0
                
        except Exception as e:
            logger.error(f"Error importing JGI GOLD biosamples: {e}")
            raise
            
    def import_jgi_gold_organisms(self, file_path: str) -> int:
        """Import data from the JGI GOLD organism coordinates CSV file.
        
        Args:
            file_path: Path to the jgi_gold_organism_geo.csv file
            
        Returns:
            Number of documents imported
        """
        logger.info(f"Processing JGI GOLD organisms from {file_path}")
        
        try:
            # Use pandas for efficient CSV handling
            df = pd.read_csv(file_path)
            
            if df.empty:
                logger.warning("Empty JGI GOLD organism data file")
                return 0
                
            # Transform into MongoDB documents
            documents = []
            for _, row in df.iterrows():
                try:
                    latitude = float(row.get('latitude'))
                    longitude = float(row.get('longitude'))
                    
                    if pd.isna(latitude) or pd.isna(longitude):
                        continue
                        
                    documents.append({
                        'dataset_id': row.get('gold_id'),
                        'system_name': 'JGI-Organism',
                        'coordinates': {
                            'type': 'Point',
                            'coordinates': [longitude, latitude]
                        },
                        'metadata': {
                            'source': 'JGI-GOLD-Organism'
                        }
                    })
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error processing JGI GOLD organism row: {e}")
                    continue
            
            if documents:
                # Use bulk insert for better performance
                result = self.collection.insert_many(documents)
                logger.info(f"Inserted {len(result.inserted_ids)} JGI GOLD organism documents")
                return len(result.inserted_ids)
            else:
                logger.warning("No valid JGI GOLD organism documents to insert")
                return 0
                
        except Exception as e:
            logger.error(f"Error importing JGI GOLD organisms: {e}")
            raise
    
    def close(self) -> None:
        """Close the MongoDB connection."""
        self.client.close()
        logger.info("MongoDB connection closed")


def validate_file(file_path: str) -> bool:
    """Check if file exists and is readable.
    
    Args:
        file_path: Path to the file to check
        
    Returns:
        True if file exists and is readable, False otherwise
    """
    if not os.path.exists(file_path):
        logger.warning(f"File not found: {file_path}")
        return False
        
    if not os.path.isfile(file_path):
        logger.warning(f"Not a file: {file_path}")
        return False
        
    if not os.access(file_path, os.R_OK):
        logger.warning(f"File not readable: {file_path}")
        return False
        
    return True


def main():
    """Main function to run the import process."""
    parser = argparse.ArgumentParser(description='Import geospatial data into MongoDB')
    parser.add_argument('--data-dir', type=str, default='./data',
                        help='Directory containing data files')
    parser.add_argument('--mongodb-uri', type=str, default='mongodb://localhost:27017',
                        help='MongoDB connection string')
    parser.add_argument('--clear-collection', action='store_true',
                        help='Clear the collection before importing')
    parser.add_argument('--skip-large-files', action='store_true',
                        help='Skip large JGI GOLD files (useful for testing)')
    args = parser.parse_args()
    
    # Check data directory
    if not os.path.exists(args.data_dir):
        logger.error(f"Data directory does not exist: {args.data_dir}")
        return 1
        
    # Set up file paths
    proposal_file = os.path.join(args.data_dir, 'latlon_project_ids.json')
    ess_dive_file = os.path.join(args.data_dir, 'ess_dive_packages.csv')
    nmdc_file = os.path.join(args.data_dir, 'nmdc_biosample_geo_coordinates.csv')
    jgi_biosample_file = os.path.join(args.data_dir, 'jgi_gold_biosample_geo.csv')
    jgi_organism_file = os.path.join(args.data_dir, 'jgi_gold_organism_geo.csv')
    
    # Validate files
    files_valid = [
        validate_file(proposal_file),
        validate_file(ess_dive_file),
        validate_file(nmdc_file),
        validate_file(jgi_biosample_file),
        validate_file(jgi_organism_file)
    ]
    
    if not any(files_valid):
        logger.error("No valid files found to import")
        return 1
        
    # Initialize MongoDB importer
    importer = MongoDBImporter(args.mongodb_uri)
    
    # Clear collection if requested
    if args.clear_collection:
        logger.info("Clearing collection before import")
        importer.collection.delete_many({})
    
    # Import each file if valid
    total_imported = 0
    
    if files_valid[0]:
        try:
            logger.info("Importing proposal locations...")
            count = importer.import_proposal_locations(proposal_file)
            total_imported += count
        except Exception as e:
            logger.error(f"Failed to import proposal locations: {e}")
    
    if files_valid[1]:
        try:
            logger.info("Importing ESS-DIVE packages...")
            count = importer.import_ess_dive_packages(ess_dive_file)
            total_imported += count
        except Exception as e:
            logger.error(f"Failed to import ESS-DIVE packages: {e}")
    
    if files_valid[2]:
        try:
            logger.info("Importing NMDC biosamples...")
            count = importer.import_nmdc_biosamples(nmdc_file)
            total_imported += count
        except Exception as e:
            logger.error(f"Failed to import NMDC biosamples: {e}")
    
    # Import JGI GOLD files unless skipped
    if not args.skip_large_files:
        if files_valid[3]:
            try:
                logger.info("Importing JGI GOLD biosamples (large file, this may take a while)...")
                count = importer.import_jgi_gold_biosamples(jgi_biosample_file)
                total_imported += count
            except Exception as e:
                logger.error(f"Failed to import JGI GOLD biosamples: {e}")
        
        if files_valid[4]:
            try:
                logger.info("Importing JGI GOLD organisms (large file, this may take a while)...")
                count = importer.import_jgi_gold_organisms(jgi_organism_file)
                total_imported += count
            except Exception as e:
                logger.error(f"Failed to import JGI GOLD organisms: {e}")
    else:
        logger.info("Skipping large JGI GOLD files as requested")
    
    # Close connection
    importer.close()
    
    logger.info(f"Import process completed. Total records imported: {total_imported}")
    return 0


if __name__ == "__main__":
    exit(main())

# Geospatial Data Tools for MongoDB

This repository contains two Python utilities for working with geospatial data in MongoDB:

1. `geo_importer.py` - Imports geospatial data from various sources into MongoDB
2. `geo_query.py` - Queries and visualizes geospatial data from MongoDB

## Prerequisites

- Python 3.6+
- MongoDB (running locally or accessible remotely)
- Required Python packages:
  ```
  pip install pymongo pandas folium
  ```
  
For processing large files, additional memory may be required.

## geo_importer.py

This tool imports geospatial data from multiple sources into a MongoDB database using a standardized schema.

### Supported Data Sources

- **EMSL** - Project location data (`latlon_project_ids.json`)
- **ESSDIVE** - ESS-DIVE package data (`ess_dive_packages.csv`)
- **NMDC** - NMDC biosample data (`nmdc_biosample_geo_coordinates.csv`)
- **JGI-Biosamples** - JGI GOLD biosample data (`jgi_gold_biosample_geo.csv`)
- **JGI-Organism** - JGI GOLD organism data (`jgi_gold_organism_geo.csv`)

### Data Schema

All data sources are imported into a consistent schema:

```json
{
  "dataset_id": "original_id_from_source",
  "system_name": "SYSTEM_NAME",  // One of: EMSL, ESSDIVE, NMDC, JGI-Biosamples, JGI-Organism
  "coordinates": {
    "type": "Point",
    "coordinates": [longitude, latitude]  // GeoJSON format
  },
  "metadata": {
    // Source-specific metadata (preserved from original data)
  }
}
```

### Usage

```bash
# Basic usage
python geo_importer.py --data-dir /path/to/data/directory

# Clear the collection before importing
python geo_importer.py --data-dir /path/to/data --clear-collection

# Skip large JGI GOLD files (useful for testing)
python geo_importer.py --data-dir /path/to/data --skip-large-files

# Specify a different MongoDB connection
python geo_importer.py --data-dir /path/to/data --mongodb-uri mongodb://username:password@hostname:port/database
```

## geo_query.py

This tool provides basic query and visualization capabilities for geospatial data stored in MongoDB.

### Features

- Get database statistics
- Query by dataset ID
- Perform geospatial queries (bounding box, proximity)
- Generate simple interactive maps with Folium
- Export results to CSV or JSON

### Usage Examples

**Get database statistics:**
```bash
python geo_query.py --action stats
```

**Query by dataset ID:**
```bash
python geo_query.py --action dataset --dataset-id "ess-dive-123456" --format map --output dataset_map
```

**Find points within a geographic region:**
```bash
python geo_query.py --action box --west -140 --east -60 --north 60 --south 20 --format map
```

**Find points near a location:**
```bash
python geo_query.py --action nearby --lat 37.8764 --lng -122.2608 --distance 50000
```

**Create a map of all (or limited subset) data points:**
```bash
python geo_query.py --action map --limit 1000 --output all_points
```

### Output Formats

- **JSON** - Raw data in JSON format (default)
- **CSV** - Tabular data in CSV format
- **Map** - Interactive HTML map using Folium

## Common Query Examples

1. **Find all points in Alaska:**
   ```bash
   python geo_query.py --action box --west -180 --east -130 --north 72 --south 55 --format map --output alaska_points
   ```

2. **Export dataset to CSV:**
   ```bash
   python geo_query.py --action dataset --dataset-id "60846" --format csv --output proposal_data
   ```

3. **Find samples within 100km of Los Alamos:**
   ```bash
   python geo_query.py --action nearby --lat 35.8800 --lng -106.3031 --distance 100000 --format map --output los_alamos_nearby
   ```

4. **Generate a map of all data (limited to 5000 points):**
   ```bash
   python geo_query.py --action map --limit 5000 --output all_data_map
   ```

5. **Get all points with system_name = "ESSDIVE":**
  ```bash
  python geo_query.py --action system --system-name ESSDIVE --format map --output essdive_map
  ```

6. **Get all points with a specific system_name and export to CSV:**
  ```bash
  python geo_query.py --action system --system-name NMDC --format csv --output nmdc_data
  ```


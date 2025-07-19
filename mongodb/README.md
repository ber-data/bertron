# BERtron MongoDB Ingestor

This tool ingests BERtron-formatted data into MongoDB.

## Setup

1. Install the required dependencies:

 See the [CONTRIBUTING.md](../CONTRIBUTING.md) file at the top level of this repository for detailed setup and contribution instructions.

2. Make sure your MongoDB instance is running.

## Usage

### Local Python Usage

Run the ingest script with your data file:

```bash
python ingest_data.py --input your_data_file.json
```

### Command-line arguments

- `--mongo-uri`: MongoDB connection URI (default: `mongodb://localhost:27017`)
- `--db-name`: MongoDB database name (default: `bertron`)
- `--schema-path`: Path or URL to the schema JSON file (default: `bertron_schema.json` in the current directory)
- `--input`: Path to input JSON file or directory containing JSON files (required)

### Using Docker Compose

We have a ingester script in docker-compose that lets you run an ingest against a data directory

```bash
# Start MongoDB and FASTAPI service
docker compose up 

# Mount the directory whose contents you want to ingest, and run the ingester
docker compose run --rm --volume /path/to/data:/data ingest 
```


## Data Format

The input data should conform to the `bertron_schema.json` schema. It can be either:

- A single entity object
- An array of entity objects

## MongoDB Collections

The script will create and populate the following collection:

- `entities`: Contains all the BERtron entities

## Example

```bash
# Ingest a single file
python ingest_data.py --input sample_data.json

# Ingest all JSON files residing in a directory
python ingest_data.py --input ./data_directory/

# Use custom MongoDB connection
python ingest_data.py --mongo-uri mongodb://username:password@localhost:27017 --db-name bertron_dev --input sample_data.json
```

## TODO: Adjust schema for GeoJSON compatibility

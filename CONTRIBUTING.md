# Contributing to BERtron

## Setup

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Check https://docs.astral.sh/uv/#installation for alternative installation methods.

## Preparing dev environment

## Environment Variables

The project uses several environment variables, especially when running with Docker Compose. You can set these in your `.env` file or export them in your shell before running Docker Compose. Below are the main variables:

| Variable            | Description                                                                 | Example / Default                                      |
|---------------------|-----------------------------------------------------------------------------|--------------------------------------------------------|
| `MONGO_HOST`        | Hostname for MongoDB (used by app/test services)                            | `mongo`                                                |
| `MONGO_PORT`        | Port for MongoDB (used by app/test/mongo services)                          | `27017`                                                |
| `MONGO_USERNAME`    | MongoDB username (required)                                                 | `your_username`                                        |
| `MONGO_PASSWORD`    | MongoDB password (required)                                                 | `your_password`                                        |
| `MONGO_DATABASE`    | MongoDB database name (required)                                            | `bertron`                                              |
| `WEB_PORT`          | Host port to expose the FastAPI server                                      | `8000` (default)                                       |
| `INGEST_DATA_PATH`  | Path to data directory for ingest service                                   | `./tests/data` (default)                               |
| `INGEST_SCHEMA_PATH`| Path or URL to schema for ingest service                                    | See docker-compose.yml for default                     |
| `INGEST_CLEAN`      | Set to `--clean` to clean mongodb (removes existing collections)  | `--clean`                                              |
| `VIRTUAL_ENV`       | Path for Python virtual environment inside containers                       | `/app_venv` (used internally by containers)            |

Create your `.env` file (if you haven't already) and edit its contents to reflect
your environment.

```sh
cp .env.example .env

# (Optional) Edit its contents.
# vi .env
```
> Note: Git will ignore your `.env` file.

Create and activate a Python virtual environment.

```sh
uv venv
source .venv/bin/activate
```

You can also run commands without first activating the Python virtual environment, by prefixing them with `uv run`. For example, you can run `ruff check` with:
```sh
uv run ruff check
```

## Adding dependencies

You can add dependencies with `uv add`. The following command:
```sh
uv add polars duckdb
```
adds `polars` and `duckdb` as project dependencies.

For dev dependencies (only needed for development, but not for using the package later),
use `--dev`:
```sh
uv add --dev ruff ipykernel pytest pytest-cov mypy
```

## Updating dependencies

You can run
```sh
uv sync --upgrade
```
to install the latest dependency version that matches the version range in `pyproject.toml`.
This will also update `uv.lock` to make the installation reproducible.

## Syncing the Python virtual environment

After adding or updating dependencies, run
```sh
uv sync --all-extras --dev
```
to make sure the Python virtual environment has the updated dependencies.

---

## Spin up container-based development environment

### Start the server
This repository includes a container-based development environment. If you have Docker installed, you can spin up that development environment by running:

```sh
docker compose up --detach
```

Once that's up and running, you can access the API at: http://localhost:8000

Also, you can access the MongoDB server at: `localhost:27017` (its admin credentials are in `docker-compose.yml`)

### Run Ingest
To populate the database with data run
```sh
docker compose run --volume /path/to/data:/data --rm ingest \
    uv run --active \
        python /app/src/ingest_data.py \
        --mongo-uri "mongodb://${MONGO_USERNAME}:${MONGO_PASSWORD}@${MONGO_HOST}:${MONGO_PORT}" \
        --input /data --clean
```
(See `docker-compose.yml` for details)

Or if you want to use data in tests/data simply use:
```sh
docker compose up ingest
```

### Run Tests

Run the tests:

```sh
docker compose up test
```

If you plan to run the tests multiple times, we'd recommend running a shell within the `test` container and—from there—running the tests (as many times as you want). That will also enable syntax highlighting of the test results.

```sh
docker compose run --rm -it test bash

# In the container:
uv run --active pytest -v
```

<details>
<summary>Show/hide FAQ about the ingest script's role in testing</summary>

Note: The test suite includes a fixture, named `seeded_db`, that will invoke the ingest script automatically before each test that specifies that fixture as a dependency.

```py
def test_foo(seeded_db):
    # The ingest script will be invoked automatically before this test runs.
    pass

def test_foo()
    # The ingest script will _not_ be invoked automatically before this test runs.
    pass
```

</details>

---

## BERtron Data Ingestion

This repository includes a MongoDB data ingestor (`src/ingest_data.py`) that ingests BERtron-formatted data into MongoDB.

### Running the Ingestor

#### Local Python Usage

Run the ingest script with your data file:

```bash
python src/ingest_data.py --input your_data_file.json
```

#### Command-line arguments

- `--mongo-uri`: MongoDB connection URI (default: `mongodb://localhost:27017`)
- `--db-name`: MongoDB database name (default: `bertron`)
- `--schema-path`: Path or URL to the schema JSON file (default: remote schema URL)
- `--input`: Path to input JSON file or directory containing JSON files (required)
- `--clean`: Delete existing collections before ingesting new data

#### Using Docker Compose

The ingester is available as a Docker Compose service:

```bash
# Start MongoDB and FASTAPI service
docker compose up 

# Mount the directory whose contents you want to ingest, and run the ingester
docker compose run --rm --volume /path/to/data:/data ingest 
```

#### Data Format

The input data should conform to the BERtron schema. It can be either:

- A single entity object
- An array of entity objects

#### MongoDB Collections

The script will create and populate the following collection:

- `entities`: Contains all the BERtron entities

#### Examples

```bash
# Ingest a single file
python src/ingest_data.py --input sample_data.json

# Ingest all JSON files in a directory
python src/ingest_data.py --input ./data_directory/

# Use custom MongoDB connection
python src/ingest_data.py --mongo-uri mongodb://username:password@localhost:27017 --db-name bertron_dev --input sample_data.json
```

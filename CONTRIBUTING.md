# Contributing to BERtron

## Setup

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Check https://docs.astral.sh/uv/#installation for alternative installation methods.

## Preparing dev environment

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

This repository includes a container-based development environment. If you have Docker installed, you can spin up that development environment by running:

```sh
docker compose up --detach
```

Once that's up and running, you can access the API at: http://localhost:8000

Also, you can access the MongoDB server at: `localhost:27017` (its admin credentials are in `docker-compose.yml`)
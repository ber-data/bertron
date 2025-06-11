# Contributing to BERtron

## Setup

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Check https://docs.astral.sh/uv/#installation for alternative installation methods.

## Preparing dev environment

```
uv venv
source .venv/bin/activate
```

You can also run commands without activating the dev environment with `uv run`,
for example you can run `ruff check` with
```
uv run ruff check
```
but the dev environment is useful if you're using an IDE.

## Adding dependencies

You can add dependencies with `uv add`. The following command:
```
uv add polars duckdb
```
adds `polars` and `duckdb` as project dependencies.

For dev dependencies (only needed for development, but not for using the package later),
use `--dev`:
```
uv add --dev ruff ipykernel pytest pytest-cov mypy
```

## Updating dependencies

You can run
```
uv sync --upgrade
```
to install the latest dependency version that matches the version range in `pyproject.toml`.
This will also update `uv.lock` to make the installation reproducible.

## Syncing dev environment

After adding or updating dependencies,
run
```
uv sync --all-extras --dev
```
to make sure the dev environment has the updated dependencies.

---

## Spin up container-based development environment

This repository includes a container-based development environment. If you have Docker installed, you can spin up that development environment by running:

```sh
docker compose up --detach
```

Once that's up and running, you can access the API at: http://localhost:8000

Also, you can access the MongoDB server at: `localhost:27017` (its admin credentials are in `docker-compose.yml`)
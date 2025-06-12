# ────────────────────────────────────────────────────────────────────────────┐
FROM python:3.13 AS base
# ────────────────────────────────────────────────────────────────────────────┘

WORKDIR /app

# Install uv.
# Docs: https://docs.astral.sh/uv/#installation
ADD https://astral.sh/uv/install.sh /uv-installer.sh
RUN sh /uv-installer.sh && rm /uv-installer.sh
ENV PATH="/root/.local/bin/:$PATH"

# Copy only the files necessary for installing Python packages.
COPY pyproject.toml /app
COPY uv.lock        /app

EXPOSE 8000

# ────────────────────────────────────────────────────────────────────────────┐
FROM base AS production
# ────────────────────────────────────────────────────────────────────────────┘

# Install Python packages listed in `uv.lock`.
# Docs: https://docs.astral.sh/uv/concepts/projects/sync/#syncing-the-environment
RUN uv sync --all-extras

# Copy all files from the repository into the image.
COPY . /app

# Use Uvicorn to serve the FastAPI application on port 8000, accepting HTTP requests from any host.
CMD [ "uv", "run", "uvicorn", "--app-dir", "/app/src", "server:app", "--host", "0.0.0.0", "--port", "8000" ]

# ────────────────────────────────────────────────────────────────────────────┐
FROM base AS development
# ────────────────────────────────────────────────────────────────────────────┘

# Install Python packages listed in `uv.lock`, including development-specific ones.
# Docs: https://docs.astral.sh/uv/concepts/projects/sync/#syncing-the-environment
RUN uv sync --all-extras --dev

# Copy all files from the repository into the image.
COPY . /app

# Run the FastAPI development server on port 8000, accepting HTTP requests from any host.
# Reference: https://fastapi.tiangolo.com/deployment/manually/
CMD [ "uv", "run", "fastapi", "dev", "--host", "0.0.0.0", "/app/src/server.py" ]
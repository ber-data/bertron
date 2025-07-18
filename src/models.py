from pydantic import BaseModel, Field
from typing import Optional


class HealthResponse(BaseModel):
    r"""A response containing system health information."""

    web_server: bool = Field(
        ...,
        title="Web server health",
        description="Whether the web server is up and running",
    )
    database: bool = Field(
        ...,
        title="Database health",
        description="Whether the web server can access the database server",
    )


class VersionResponse(BaseModel):
    r"""A response containing system version information."""

    api: Optional[str] = Field(
        ...,
        title="API version",
        description="The version identifier of the API",
    )
    bertron_schema: Optional[str] = Field(
        ...,
        title="BERtron schema version",
        description="The version identifier of the BERtron schema",
    )

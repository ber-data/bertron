from pydantic import BaseModel, ConfigDict, Field
from typing import Optional


class HealthResponse(BaseModel):
    r"""A response containing system health information."""

    # Raise a `ValidationError` if extra parameters are passed in when instantiating this class.
    # Note: This facilitates having our tests confirm API responses don't include extra fields.
    # Docs: https://docs.pydantic.dev/latest/api/config/#pydantic.config.ConfigDict.extra
    model_config = ConfigDict(extra="forbid")

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

    model_config = ConfigDict(extra="forbid")

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

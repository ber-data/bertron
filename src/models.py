from pydantic import BaseModel, Field


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

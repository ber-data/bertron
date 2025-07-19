from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    r"""
    Configuration settings for the application.

    Order of precedence (highest to lowest) for settings values:
    1. Process-level environment variable definitions.
    2. Environment variable definitions loaded from a `.env` file.
    3. Default values defined in this class.

    References:
    - https://docs.pydantic.dev/latest/concepts/pydantic_settings/#dotenv-env-support
    """

    # Load environment variable definitions from a `.env` file, if one exists,
    # in the current working directory. We allow the `.env` file to contain
    # extra environment variables (beyond those modeled below), since this
    # repository currently contains a variety of independent applications.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # MongoDB connection settings.
    mongo_host: str = "localhost"
    mongo_port: int = 27017  # note: value in `.env` will be coerced into int
    mongo_username: Optional[str] = None
    mongo_password: Optional[str] = None
    mongo_database: str = "bertron"


# Instantiate a settings object that can be imported into other modules.
settings = Settings()

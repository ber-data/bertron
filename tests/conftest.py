r"""
This module contains `pytest` fixture definitions that `pytest` will automatically make available
to all tests within this directory and its descendant directories.

From the `pytest` documentation:
> The `conftest.py` file serves as a means of providing fixtures for an entire directory.
> Fixtures defined in a `conftest.py` can be used by any test in that package without
> needing to import them (`pytest` will automatically discover them).
Source: https://docs.pytest.org/en/stable/reference/fixtures.html#conftest-py-sharing-fixtures-across-multiple-files
"""

import pytest

from src.config import settings as cfg


# Note: We use `autouse=True` so that this fixture is automatically applied to each test
#       within its scope (since we are in a `conftest.py` file, its scope consists of
#       the current directory and all descendant directories).
@pytest.fixture(autouse=True)
def patched_cfg():
    r"""
    A `pytest` fixture that temporarily patches the application configuration
    so it references a test database.
    """

    test_database_name = "bertron_test"
    main_database_name = cfg.mongo_database
    assert main_database_name != test_database_name, (
        "The main database name matches the test database name. "
        "Reconfigure your environment to ensure they differ."
    )
    cfg.mongo_database = test_database_name
    yield cfg
    cfg.mongo_database = main_database_name

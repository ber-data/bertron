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

from src.config import settings


# Note: We use `autouse=True` so that this fixture is automatically applied to each test
#       within its scope (since we are in a `conftest.py` file, its scope consists of
#       the current directory and all descendant directories).
@pytest.fixture(autouse=True)
def patched_config(monkeypatch):
    r"""
    A `pytest` fixture that temporarily patches the application configuration
    so it references a test database.

    From the pytest documentation:
    > `monkeypatch.setattr` works by (temporarily) changing the object that a name points to
    > with another one. There can be many names pointing to any individual object, so for
    > patching to work you must ensure that you patch the name used by the system under test.
    Source: https://docs.pytest.org/en/stable/reference/reference.html#pytest.MonkeyPatch.setattr

    Also from the pytest documentation:
    > All modifications will be undone after the requesting test function or fixture has finished.
    """

    # First, we do a safety check to ensure that the test database is distinct from the main one.
    main_database_name = settings.mongo_database
    test_database_name = "bertron_test"
    assert main_database_name != test_database_name, (
        "The main database name matches the test database name. "
        "Reconfigure your environment to ensure they differ."
    )

    # Then, we patch the config object so it references the test database.
    # Note: Different modules import the config object using different `import` paths.
    monkeypatch.setattr("config.settings.mongo_database", test_database_name)
    monkeypatch.setattr("src.config.settings.mongo_database", test_database_name)

    # Finally, we yield control to the test that depends on this fixture.
    # Note: After the test completes, `monkeypatch` will automatically un-patch things.
    yield

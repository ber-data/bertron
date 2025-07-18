from importlib.metadata import PackageNotFoundError, version
from typing import Optional


def get_package_version(package_name: str) -> Optional[str]:
    r"""
    Returns the version identifier (e.g., "1.2.3") of the package having the specified name.
    
    Args:
        package_name: The name of the package
        
    Returns:
        The version identifier of the package, or `None` if package not found
    """
    try:
        return version(package_name)
    except PackageNotFoundError:
        return None

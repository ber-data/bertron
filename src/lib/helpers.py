from importlib.metadata import PackageNotFoundError, version


def get_package_version(package_name: str) -> str:
    r"""
    Returns the version identifier (e.g., "1.2.3") of the package having the specified name.
    
    Args:
        package_name: The name of the package
        
    Returns:
        The version identifier of the package, or "Unknown" if package not found
    """
    try:
        return version(package_name)
    except PackageNotFoundError:
        return "Unknown"

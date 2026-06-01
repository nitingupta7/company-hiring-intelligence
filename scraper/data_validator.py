import re
from urllib.parse import urlparse

def normalize_name(name: str) -> str:
    """
    Normalizes a company or person name.
    """
    if not name:
        return ""
    # Remove extra whitespace and convert to title case
    return " ".join(name.split()).title()

def validate_url(url: str) -> bool:
    """
    Validates if a string is a valid URL.
    """
    if not url:
        return False
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False

def clean_social_media_url(url: str) -> str:
    """
    Cleans social media URLs by removing query parameters.
    """
    if not url:
        return ""
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")

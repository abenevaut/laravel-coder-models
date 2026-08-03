"""Detect Laravel version from documentation content."""

import re
from typing import Optional

# Patterns to match Laravel version in markdown content
VERSION_PATTERNS = [
    r"Laravel\s+(\d+\.x)",           # "Laravel 10.x"
    r"Laravel\s+version\s+(\d+\.x)",  # "Laravel version 10.x"
    r"v(\d+\.x)",                    # "v10.x"
    r"version\s+(\d+\.x)",           # "version 10.x"
    r"(\d+\.x)\s+documentation",     # "10.x documentation"
]


def _extract_version_from_text(text: str) -> Optional[str]:
    """Extract Laravel version from text using patterns."""
    for pattern in VERSION_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def detect_version(data: dict, **kwargs) -> dict:
    """Pipeline step: Detect Laravel version from content.
    
    Searches for version patterns in the markdown content and adds
    the detected version to the data dictionary.
    
    Input:  data["content"] - markdown content
    Output: data["version"] - detected version string or None
    """
    content = data.get("content", "")
    version = _extract_version_from_text(content)
    data["version"] = version
    return data

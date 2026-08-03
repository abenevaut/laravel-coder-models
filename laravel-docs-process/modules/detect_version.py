"""Detect Laravel version from documentation content."""

import re
from typing import Optional
import sys

# Patterns to match Laravel version in markdown content
VERSION_PATTERNS = [
    r"Laravel\s+(\d+\.x)",           # "Laravel 10.x"
    r"Laravel\s+version\s+(\d+\.x)",  # "Laravel version 10.x"
    r"v(\d+\.x)",                    # "v10.x"
    r"version\s+(\d+\.x)",           # "version 10.x"
    r"(\d+\.x)\s+documentation",     # "10.x documentation"
    r"(\d+\.x)\s+branch",            # "10.x branch"
    r"release\s+(\d+\.x)",          # "release 10.x"
    r"stable\s+release.*?(\d+\.x)",  # "current stable release 10.x"
    r"for\s+Laravel\s+(\d+\.x)",     # "for Laravel 10.x"
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
    doc_name = data.get("doc_name", "unknown")
    print(f"  [{doc_name}] Running: detect_version", file=sys.stderr)
    
    content = data.get("content", "")
    version = _extract_version_from_text(content)
    data["version"] = version
    
    version_info = f"version={version}" if version else "version=None"
    print(f"  [{doc_name}] Finished: detect_version ({version_info})", file=sys.stderr)
    return data

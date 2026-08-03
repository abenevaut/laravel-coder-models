"""Detect Laravel version from documentation content."""

import re
from collections import Counter
from pathlib import Path
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
    r"release\s+(\d+\.x)",           # "release 10.x"
    r"stable\s+release.*?(\d+\.x)",   # "current stable release 10.x"
    r"for\s+Laravel\s+(\d+\.x)",     # "for Laravel 10.x"
]


def extract_version_from_text(text: str) -> Optional[str]:
    """Extract Laravel version from text using patterns."""
    for pattern in VERSION_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def detect_version_from_git(docs_root: Path) -> Optional[str]:
    """Detect Laravel version from git submodule or repository."""
    try:
        # Check if it's a git submodule (contains gitdir: path)
        git_file = docs_root / ".git"
        if git_file.exists():
            with open(git_file, "r") as f:
                content = f.read().strip()
            
            # If it's a submodule, it contains "gitdir: path/to/real/git"
            if content.startswith("gitdir: "):
                git_dir_path = (docs_root / content.split(": ", 1)[1].strip()).resolve()
                head_path = git_dir_path / "HEAD"
                if head_path.exists():
                    with open(head_path, "r") as f:
                        head_content = f.read().strip()
                    if head_content.startswith("ref: refs/heads/"):
                        branch = head_content.split("/")[-1]
                        match = re.match(r"^(\d+\.x)$", branch)
                        if match:
                            return match.group(1)
        
        # Also try direct .git/HEAD if it's a regular repo
        head_path = docs_root / ".git" / "HEAD"
        if head_path.exists():
            with open(head_path, "r") as f:
                head_content = f.read().strip()
            if head_content.startswith("ref: refs/heads/"):
                branch = head_content.split("/")[-1]
                match = re.match(r"^(\d+\.x)$", branch)
                if match:
                    return match.group(1)
    except (IOError, OSError):
        pass
    return None


def detect_global_version(docs_root: Path, skip_files: set[str]) -> Optional[str]:
    """Detect the global Laravel version from documentation.
    
    Tries git branch first, then falls back to content analysis.
    
    Args:
        docs_root: Path to the Laravel docs directory
        skip_files: Set of filenames to skip
        
    Returns:
        Detected version string or None
    """
    # Try git branch first
    git_version = detect_version_from_git(docs_root)
    if git_version:
        return git_version
    
    # Fall back to content analysis
    versions = []
    
    # Sample files to detect version
    for md_file in sorted(docs_root.glob("*.md"))[:15]:
        if md_file.name in skip_files:
            continue
        try:
            content = md_file.read_text(encoding="utf-8", errors="ignore")
            version = extract_version_from_text(content)
            if version:
                versions.append(version)
        except (IOError, UnicodeDecodeError):
            continue
    
    # Return most common version, or first one found, or None
    if versions:
        counter = Counter(versions)
        return counter.most_common(1)[0][0]
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
    version = extract_version_from_text(content)
    data["version"] = version
    
    version_info = f"version={version}" if version else "version=None"
    print(f"  [{doc_name}] Finished: detect_version ({version_info})", file=sys.stderr)
    return data

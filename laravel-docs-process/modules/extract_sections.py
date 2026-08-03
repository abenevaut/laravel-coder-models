"""Extract sections from markdown content module."""

import sys
from pathlib import Path

# Add the current directory to path for local imports
sys.path.insert(0, str(Path(__file__).parent))

from clean_content import strip_markdown


def _extract_sections_from_content(content: str) -> list[dict]:
    """Extract titled sections from markdown content."""
    sections = []
    current_title = "Overview"
    current_lines: list[str] = []

    for line in content.splitlines():
        if line.startswith("#"):
            if current_lines:
                body = strip_markdown("\n".join(current_lines))
                if len(body) > 80:
                    sections.append({"title": current_title, "body": body[:2000]})
            current_title = line.lstrip("#").strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        body = strip_markdown("\n".join(current_lines))
        if len(body) > 80:
            sections.append({"title": current_title, "body": body[:2000]})

    return sections


def extract_sections(data: dict, **kwargs) -> dict:
    """Pipeline step: Extract sections from content.
    
    Input:  data["content"] - markdown content
    Output: data["sections"] - list of section dicts
    """
    doc_name = data.get("doc_name", "unknown")
    print(f"  [{doc_name}] Running: extract_sections", file=sys.stderr)
    
    sections = _extract_sections_from_content(data.get("content", ""))
    data["sections"] = sections
    
    print(f"  [{doc_name}] Finished: extract_sections (found {len(sections)} sections)", file=sys.stderr)
    return data

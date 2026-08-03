"""Extract sections from markdown content module."""

import re
import sys
from pathlib import Path

# Add the current directory to path for local imports
sys.path.insert(0, str(Path(__file__).parent))

from clean_content import strip_markdown


def strip_markdown_preserve_code(text: str) -> str:
    """Remove markdown formatting but preserve code blocks and inline code."""
    # First, protect code blocks by replacing them with a placeholder
    code_blocks = []
    code_block_pattern = r'```([\s\S]*?)```'
    
    def save_code_block(match):
        code_blocks.append(match.group(0))
        return f"__CODE_BLOCK_{len(code_blocks)-1}__"
    
    text_with_placeholders = re.sub(code_block_pattern, save_code_block, text)
    
    # Remove inline code backticks but keep the content
    text_with_placeholders = re.sub(r"`([^`]+)`", r"\1", text_with_placeholders)
    
    # Remove links but keep the text
    text_with_placeholders = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text_with_placeholders)
    
    # Remove header marks
    text_with_placeholders = re.sub(r"^#+\s*", "", text_with_placeholders, flags=re.MULTILINE)
    
    # Reduce multiple newlines
    text_with_placeholders = re.sub(r"\n{3,}", "\n\n", text_with_placeholders)
    
    # Restore code blocks
    for i, block in enumerate(code_blocks):
        text_with_placeholders = text_with_placeholders.replace(
            f"__CODE_BLOCK_{i}__", block
        )
    
    return text_with_placeholders.strip()


def _extract_sections_from_content(content: str) -> list[dict]:
    """Extract titled sections from markdown content."""
    sections = []
    current_title = "Overview"
    current_lines: list[str] = []

    for line in content.splitlines():
        if line.startswith("#"):
            if current_lines:
                body = strip_markdown_preserve_code("\n".join(current_lines))
                if len(body) > 80:
                    sections.append({"title": current_title, "body": body[:2000]})
            current_title = line.lstrip("#").strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        body = strip_markdown_preserve_code("\n".join(current_lines))
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

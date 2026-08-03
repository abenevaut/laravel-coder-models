"""Clean markdown content module."""

import re
import sys


def strip_markdown(text: str) -> str:
    """Remove markdown formatting from text."""
    text = re.sub(r"```[\s\S]*?```", "", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def clean_content(data: dict, **kwargs) -> dict:
    """Pipeline step: Clean markdown content.
    
    Input:  data["content"] - raw markdown content
    Output: data["cleaned_content"] - cleaned text
    """
    doc_name = data.get("doc_name", "unknown")
    print(f"  [{doc_name}] Running: clean_content", file=sys.stderr)
    
    data["cleaned_content"] = strip_markdown(data.get("content", ""))
    
    print(f"  [{doc_name}] Finished: clean_content", file=sys.stderr)
    return data

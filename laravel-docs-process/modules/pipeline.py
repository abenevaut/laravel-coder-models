"""Processing pipeline for Laravel docs."""

import importlib
import re
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Optional

# Add the parent directory to path for config import
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import pipeline configuration
from config import PIPELINE_STEPS

# Add the current directory to path for module imports
sys.path.insert(0, str(Path(__file__).parent))


def run_module_step(step_name: str, data: dict, **kwargs: Any) -> dict:
    """Execute a pipeline step by dynamically importing the module.
    
    The module must have a function with the same name as the module.
    Example: clean_content.py must have clean_content(data, **kwargs) -> dict
    """
    module = importlib.import_module(f"{step_name}")
    step_fn = getattr(module, step_name)
    return step_fn(data, **kwargs)


def _extract_version_from_text(text: str) -> Optional[str]:
    """Extract Laravel version from text using patterns."""
    # Extended patterns to match version in various formats
    patterns = [
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
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def _detect_version_from_git(docs_root: Path) -> Optional[str]:
    """Try to detect version from git submodule."""
    try:
        git_file = docs_root / ".git"
        if git_file.exists():
            # Check if it's a git submodule (contains gitdir: path)
            with open(git_file, "r") as f:
                content = f.read().strip()
            
            # If it's a submodule, it contains "gitdir: path/to/real/git"
            if content.startswith("gitdir: "):
                # The real git directory is at the path specified
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


def _detect_global_version(docs_root: Path, skip_files: set[str]) -> Optional[str]:
    """Detect the global Laravel version from documentation.
    
    Tries git branch first, then falls back to content analysis.
    """
    # Try git branch first
    git_version = _detect_version_from_git(docs_root)
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
            version = _extract_version_from_text(content)
            if version:
                versions.append(version)
        except (IOError, UnicodeDecodeError):
            continue
    
    # Return most common version, or first one found, or None
    if versions:
        counter = Counter(versions)
        return counter.most_common(1)[0][0]
    return None


def process_file(md_file: Path, global_version: Optional[str] = None) -> dict:
    """Process a single markdown file through the pipeline.
    
    Args:
        md_file: Path to the markdown file
        global_version: Optional global version to use (overrides per-file detection)
        
    Returns:
        dict containing all processing results
    """
    try:
        content = md_file.read_text(encoding="utf-8", errors="ignore")
    except (IOError, UnicodeDecodeError, PermissionError) as e:
        # Return empty result with error info for corrupted files
        return {
            "doc_name": md_file.name,
            "error": str(e),
            "qa_items": [],
            "sections": []
        }
    
    data = {
        "doc_name": md_file.name,
        "content": content,
    }
    
    # If global version is provided, inject it before pipeline
    if global_version:
        data["version"] = global_version
    
    # Execute each step in order
    for step_name in PIPELINE_STEPS:
        try:
            data = run_module_step(step_name, data)
        except Exception as e:
            # If a pipeline step fails, store error and return partial result
            data["error"] = f"Pipeline step '{step_name}' failed: {e}"
            data["qa_items"] = data.get("qa_items", [])
            data["sections"] = data.get("sections", [])
            break
    
    return data


def run_pipeline(docs_root: Path, skip_files: set[str], max_workers: int = 4) -> tuple[list[dict], dict, Optional[str]]:
    """Run the complete processing pipeline on all documentation files.
    
    Uses ThreadPoolExecutor for parallel file processing.
    
    Args:
        docs_root: Path to the Laravel docs directory
        skip_files: Set of filenames to skip
        max_workers: Number of parallel workers
        
    Returns:
        tuple of (all_qa_items, sections_by_doc, detected_version)
    """
    # Collect all markdown files to process
    md_files = [
        f for f in sorted(docs_root.glob("*.md")) 
        if f.name not in skip_files
    ]
    
    if not md_files:
        return [], {}, None
    
    # Detect global version from documentation
    global_version = _detect_global_version(docs_root, skip_files)
    
    all_qa = []
    sections_by_doc = {}
    errors = []
    
    # Process files in parallel
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_file = {
            executor.submit(process_file, md_file, global_version): md_file 
            for md_file in md_files
        }
        
        for future in as_completed(future_to_file):
            md_file = future_to_file[future]
            try:
                result = future.result()
                
                # Check for errors in result
                if result.get("error"):
                    errors.append(f"{md_file}: {result['error']}")
                    continue
                
                all_qa.extend(result.get("qa_items", []))
                if result.get("sections"):
                    sections_by_doc[result["doc_name"]] = result["sections"]
            except Exception as e:
                errors.append(f"{md_file}: {e}")
    
    # Print errors if any occurred
    if errors:
        for error in errors:
            print(f"Warning: {error}", file=sys.stderr)
    
    return all_qa, sections_by_doc, global_version

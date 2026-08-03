"""Processing pipeline for Laravel docs."""

import importlib
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Optional

# Add modules directory to path
MODULES_DIR = Path(__file__).parent
sys.path.insert(0, str(MODULES_DIR))

# Import version detection utilities
from detect_version import detect_global_version


def load_pipeline_steps(modules_dir: Path) -> list[str]:
    """Load pipeline steps from config.json."""
    config_path = modules_dir.parent / "config.json"
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
        return config.get("PIPELINE_STEPS", [
            "clean_content",
            "detect_version", 
            "extract_sections",
            "generate_qa"
        ])
    except (FileNotFoundError, json.JSONDecodeError):
        return [
            "clean_content",
            "detect_version",
            "extract_sections", 
            "generate_qa"
        ]


# Load pipeline steps at module level
PIPELINE_STEPS = load_pipeline_steps(MODULES_DIR)


def run_module_step(step_name: str, data: dict, **kwargs: Any) -> dict:
    """Execute a pipeline step by dynamically importing the module.
    
    The module must have a function with the same name as the module.
    Example: clean_content.py must have clean_content(data, **kwargs) -> dict
    """
    module = importlib.import_module(f".{step_name}", package="modules")
    step_fn = getattr(module, step_name)
    return step_fn(data, **kwargs)


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
    global_version = detect_global_version(docs_root, skip_files)
    version_info = f"Detected version: {global_version}" if global_version else "No version detected"
    print(f"{version_info}", file=sys.stderr)
    
    all_qa = []
    sections_by_doc = {}
    errors = []
    
    total_files = len(md_files)
    print(f"Processing {total_files} markdown files with {max_workers} workers...", file=sys.stderr)
    
    # Process files in parallel
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_file = {
            executor.submit(process_file, md_file, global_version): md_file 
            for md_file in md_files
        }
        
        completed = 0
        for future in as_completed(future_to_file):
            md_file = future_to_file[future]
            completed += 1
            print(f"[{completed}/{total_files}] Processing: {md_file.name}", file=sys.stderr)
            try:
                result = future.result()
                
                # Check for errors in result
                if result.get("error"):
                    errors.append(f"{md_file}: {result['error']}")
                    print(f"  [{md_file.name}] Error: {result['error']}", file=sys.stderr)
                    continue
                
                all_qa.extend(result.get("qa_items", []))
                if result.get("sections"):
                    sections_by_doc[result["doc_name"]] = result["sections"]
                
                qa_count = len(result.get("qa_items", []))
                section_count = len(result.get("sections", []))
                print(f"  [{md_file.name}] Completed: {qa_count} Q&A items, {section_count} sections", file=sys.stderr)
            except Exception as e:
                errors.append(f"{md_file}: {e}")
                print(f"  [{md_file.name}] Exception: {e}", file=sys.stderr)
    
    # Print errors if any occurred
    if errors:
        for error in errors:
            print(f"Warning: {error}", file=sys.stderr)
    
    total_qa = len(all_qa)
    total_docs = len(sections_by_doc)
    print(f"Pipeline complete: {total_qa} total Q&A items from {total_docs} documents", file=sys.stderr)
    
    return all_qa, sections_by_doc, global_version

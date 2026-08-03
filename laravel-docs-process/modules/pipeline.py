"""Processing pipeline for Laravel docs."""

import importlib
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

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


def process_file(md_file: Path) -> dict:
    """Process a single markdown file through the pipeline.
    
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


def run_pipeline(docs_root: Path, skip_files: set[str], max_workers: int = 4) -> tuple[list[dict], dict]:
    """Run the complete processing pipeline on all documentation files.
    
    Uses ThreadPoolExecutor for parallel file processing.
    
    Args:
        docs_root: Path to the Laravel docs directory
        skip_files: Set of filenames to skip
        max_workers: Number of parallel workers
        
    Returns:
        tuple of (all_qa_items, sections_by_doc)
    """
    # Collect all markdown files to process
    md_files = [
        f for f in sorted(docs_root.glob("*.md")) 
        if f.name not in skip_files
    ]
    
    if not md_files:
        return [], {}
    
    all_qa = []
    sections_by_doc = {}
    errors = []
    
    # Process files in parallel
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_file = {
            executor.submit(process_file, md_file): md_file 
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
    
    return all_qa, sections_by_doc

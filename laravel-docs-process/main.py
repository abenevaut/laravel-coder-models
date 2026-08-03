#!/usr/bin/env python3
"""Process Laravel docs into training data."""

import json
import sys
from pathlib import Path

# Add the current directory to path for local imports
sys.path.insert(0, str(Path(__file__).parent))

from config import PIPELINE_STEPS
from modules.pipeline import run_pipeline
from modules.generate_qa import build_knowledge_digest

ROOT = Path(__file__).resolve().parent.parent
DOCS_ROOT = ROOT / "laravel-docs"
OUTPUT_DIR = ROOT / "laravel-docs-data"

# Validate paths
if not DOCS_ROOT.exists():
    raise SystemExit(f"Laravel docs directory not found: {DOCS_ROOT}")

if not DOCS_ROOT.is_dir():
    raise SystemExit(f"Path is not a directory: {DOCS_ROOT}")

# Check if there are any markdown files
md_files = list(DOCS_ROOT.glob("*.md"))
if not md_files:
    raise SystemExit(f"No markdown files found in: {DOCS_ROOT}")

# Create output directory
OUTPUT_DIR.mkdir(exist_ok=True)

# Load metadata from JSON file
try:
    with open(Path(__file__).parent / "metadata.json", "r") as f:
        metadata = json.load(f)
except FileNotFoundError:
    raise SystemExit(f"Metadata file not found: {Path(__file__).parent / 'metadata.json'}")
except json.JSONDecodeError as e:
    raise SystemExit(f"Invalid JSON in metadata file: {e}")

TOPICS = metadata["TOPICS"]
SKIP_FILES = set(metadata["SKIP_FILES"])
PRIORITY_TOPICS = metadata["PRIORITY_TOPICS"]


def main():
    # Run the processing pipeline
    all_qa, sections_by_doc = run_pipeline(DOCS_ROOT, SKIP_FILES)

    # Write output files
    try:
        jsonl_path = OUTPUT_DIR / "laravel_training.jsonl"
        with jsonl_path.open("w", encoding="utf-8") as f:
            for item in all_qa:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")

        digest = build_knowledge_digest(sections_by_doc)
        (OUTPUT_DIR / "laravel_knowledge.md").write_text(digest, encoding="utf-8")

        examples = []
        seen: set[str] = set()
        for topic in PRIORITY_TOPICS:
            for qa in all_qa:
                if topic in qa["topic"] and topic not in seen:
                    examples.append(qa)
                    seen.add(topic)
                    break

        (OUTPUT_DIR / "few_shot_examples.json").write_text(
            json.dumps(examples[:14], indent=2, ensure_ascii=False), encoding="utf-8"
        )

        meta = {
            "total_docs": len(sections_by_doc),
            "total_qa_pairs": len(all_qa),
            "few_shot_count": len(examples[:14]),
            "pipeline_steps": PIPELINE_STEPS,
        }
        (OUTPUT_DIR / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        print(json.dumps(meta, indent=2))
    except (IOError, PermissionError) as e:
        raise SystemExit(f"Failed to write output files: {e}")


if __name__ == "__main__":
    main()

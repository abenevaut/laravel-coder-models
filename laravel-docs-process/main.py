#!/usr/bin/env python3
"""Process Laravel docs into training data."""

import json
import os
import sys
from pathlib import Path


def load_env_file(env_path: Path) -> dict:
    """Load environment variables from a .env file."""
    env_vars = {}
    if env_path.exists():
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    env_vars[key.strip()] = value.strip()
    return env_vars


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

# Load LLM configuration from .env file
llm_config = {
    "enabled": False,
    "api_url": "http://localhost:11434",
    "model": "qwen3.5:4b-mlx",
    "timeout": 120,
    "batch_size": 10
}

env_path = ROOT / ".env"
env_vars = load_env_file(env_path)

# Override defaults with .env values
if "LLM_ENABLED" in env_vars:
    llm_config["enabled"] = env_vars["LLM_ENABLED"].lower() in ("true", "1", "yes")
if "LLM_API_URL" in env_vars:
    llm_config["api_url"] = env_vars["LLM_API_URL"]
if "LLM_MODEL" in env_vars:
    llm_config["model"] = env_vars["LLM_MODEL"]
if "LLM_TIMEOUT" in env_vars:
    try:
        llm_config["timeout"] = int(env_vars["LLM_TIMEOUT"])
    except ValueError:
        pass
if "LLM_BATCH_SIZE" in env_vars:
    try:
        llm_config["batch_size"] = int(env_vars["LLM_BATCH_SIZE"])
    except ValueError:
        pass

# CLI argument overrides .env
if "--llm" in sys.argv or "-l" in sys.argv:
    llm_config["enabled"] = True


def qualify_with_llm(all_qa: list[dict]) -> list[dict]:
    """Qualify Q&A pairs using LLM API (optional, requires requests).
    
    Adds qualification metadata:
    - useful: bool (is the Q&A useful for Laravel experts)
    - tags: list of 3 technical tags
    - niveau/level: "débutant"|"intermédiaire"|"avancé"
    - has_code: bool (contains valid PHP code)
    - weight: float (for weighted loss fine-tuning)
    
    Args:
        all_qa: List of Q&A pairs
        
    Returns:
        List of qualified Q&A pairs (filtered to useful ones only)
    """
    try:
        from modules.qualify_llm import LLMQualifier
        
        api_url = llm_config.get("api_url", "http://localhost:11434")
        model = llm_config.get("model", "qwen3.5:4b-mlx")
        timeout = llm_config.get("timeout", 120)
        batch_size = llm_config.get("batch_size", 10)
        
        qualifier = LLMQualifier(api_url=api_url, model=model, timeout=timeout)
        qualified = []
        
        print("Qualifying Q&A pairs with LLM API...", file=sys.stderr)
        
        for qa in all_qa:
            try:
                qualified_qa = qualifier.qualify(qa)
                # Only keep useful Q&A pairs
                if qualified_qa.get("qualification", {}).get("useful", True):
                    qualified.append(qualified_qa)
            except Exception as e:
                print(f"Warning: Failed to qualify Q&A: {e}", file=sys.stderr)
                # Keep the original Q&A without qualification
                qualified.append(qa)
        
        print(f"Qualified {len(qualified)}/{len(all_qa)} Q&A pairs", file=sys.stderr)
        return qualified
        
    except (ImportError, RuntimeError) as e:
        print(f"Warning: LLM qualification disabled: {e}", file=sys.stderr)
        return all_qa


def main():
    # Run the processing pipeline
    all_qa, sections_by_doc, detected_version = run_pipeline(DOCS_ROOT, SKIP_FILES)

    # Optionally qualify with LLM if enabled in .env or CLI
    use_llm = llm_config.get("enabled", False)
    if use_llm:
        all_qa = qualify_with_llm(all_qa)

    # Add version tag to all Q&A items if detected
    if detected_version:
        for qa in all_qa:
            qa["version"] = detected_version

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

        # Calculate statistics
        useful_count = sum(1 for qa in all_qa if qa.get("qualification", {}).get("useful", True))
        has_code_count = sum(1 for qa in all_qa if qa.get("qualification", {}).get("has_code", False))
        total_weight = sum(qa.get("weight", 1.0) for qa in all_qa)
        
        # Calculate KPIs for training data quality
        # Valid code rate (from qualification or has_code in output)
        total_with_code = has_code_count
        valid_code_rate = (total_with_code / len(all_qa) * 100) if all_qa else 0.0
        
        # Average response length (output tokens approximation)
        total_output_length = sum(len(qa.get("output", "").split()) for qa in all_qa)
        avg_response_length = (total_output_length / len(all_qa)) if all_qa else 0.0
        
        # Topic coverage rate
        all_tags = set()
        for qa in all_qa:
            topic = qa.get("topic", "")
            if topic:
                all_tags.add(topic)
            qual_tags = qa.get("qualification", {}).get("tags", [])
            all_tags.update(qual_tags)
        
        # Extract unique topic keywords from TOPICS
        defined_topics = set()
        for topic_tags in TOPICS.values():
            defined_topics.update(tag.strip() for tag in topic_tags.split(","))
        
        topic_coverage_rate = (len(all_tags & defined_topics) / len(defined_topics) * 100) if defined_topics else 0.0
        
        # Tag distribution
        tag_counts = {}
        for qa in all_qa:
            qual_tags = qa.get("qualification", {}).get("tags", [])
            for tag in qual_tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        # Response length distribution
        length_brackets = {"short (<50 tokens)": 0, "medium (50-200 tokens)": 0, "long (>200 tokens)": 0}
        for qa in all_qa:
            output_len = len(qa.get("output", "").split())
            if output_len < 50:
                length_brackets["short (<50 tokens)"] += 1
            elif output_len <= 200:
                length_brackets["medium (50-200 tokens)"] += 1
            else:
                length_brackets["long (>200 tokens)"] += 1
        
        # Unique Q&A ratio (based on instruction)
        unique_instructions = len(set(qa.get("instruction", "") for qa in all_qa))
        uniqueness_rate = (unique_instructions / len(all_qa) * 100) if all_qa else 0.0
        
        meta = {
            "total_docs": len(sections_by_doc),
            "total_qa_pairs": len(all_qa),
            "total_weight": total_weight,
            "few_shot_count": len(examples[:14]),
            "pipeline_steps": PIPELINE_STEPS,
            "detected_version": detected_version,
            "llm_config": {
                "enabled": use_llm,
                "api_url": llm_config.get("api_url"),
                "model": llm_config.get("model")
            },
            "kpis": {
                "valid_code_rate": round(valid_code_rate, 2),
                "target_valid_code_rate": "> 98%",
                "avg_response_length_tokens": round(avg_response_length, 2),
                "target_avg_length": "50-200 tokens",
                "topic_coverage_rate": round(topic_coverage_rate, 2),
                "target_topic_coverage": "> 95%",
                "uniqueness_rate": round(uniqueness_rate, 2),
                "target_uniqueness": "> 95%",
                "length_distribution": length_brackets
            }
        }
        
        # Add tag distribution to KPIs
        if tag_counts:
            meta["kpis"]["tag_distribution"] = {k: v for k, v in sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)}
        
        # Add qualification stats if LLM was used
        if use_llm:
            meta["useful_qa_count"] = useful_count
            meta["has_code_count"] = has_code_count
            
            # Count by level
            level_counts = {}
            for qa in all_qa:
                level = qa.get("niveau", qa.get("level", "inconnu"))
                level_counts[level] = level_counts.get(level, 0) + 1
            meta["level_distribution"] = level_counts
            
            # Weight distribution
            weight_distribution = {}
            for qa in all_qa:
                weight = qa.get("weight", 1.0)
                weight_key = f"{weight:.1f}"
                weight_distribution[weight_key] = weight_distribution.get(weight_key, 0) + 1
            meta["weight_distribution"] = weight_distribution
            
            # Add level-based KPIs
            if level_counts:
                meta["kpis"]["level_distribution"] = level_counts
        
        (OUTPUT_DIR / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        print(json.dumps(meta, indent=2))
    except (IOError, PermissionError) as e:
        raise SystemExit(f"Failed to write output files: {e}")


if __name__ == "__main__":
    main()

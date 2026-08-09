#!/usr/bin/env python3
"""Process Laravel docs into training data."""

import json
import sys
from pathlib import Path

# Add modules directory to path
MODULES_DIR = Path(__file__).parent / "modules"
sys.path.insert(0, str(MODULES_DIR))

from modules.pipeline import run_pipeline
from modules.generate_qa import build_knowledge_digest
from modules.qualify_llm import LLMConfig, load_llm_config, qualify_with_llm


def determine_level_heuristic(qa: dict) -> str:
    """Determine level based on content heuristics when LLM is not available."""
    topic = qa.get("topic", "").lower()
    instruction = qa.get("instruction", "").lower()
    output = qa.get("output", "").lower()
    has_code = qa.get("has_code", False)
    subtopics = qa.get("subtopics", [])
    
    # Normalize topic list
    all_topics = [topic] + [t.lower() for t in subtopics]
    topic_str = " ".join(all_topics)
    full_text = f"{topic_str} {instruction} {output}"
    
    # Beginner topic indicators (very specific)
    beginner_indicators = {
        "introduction", "getting started", "installation", "setup",
        "basic", "beginner", "tutorial", "hello world", "first steps",
        "overview", "what is", "understanding"
    }
    
    # Advanced topics (expert-level concepts)
    advanced_topics = {
        "ai", "boost",
        "service container", "dependency injection", "bindings",
        "contracts", "facades", "interface", "abstraction", "repository pattern",
        "queue", "horizon", "job", "worker", "failed jobs",
        "broadcasting", "websocket", "reverb", "echo",
        "event", "listener", "observer", "model events",
        "cache", "redis", "caching", "remember", "cache tags",
        "service provider", "boot", "register", "macro",
        "swoole", "frankenphp", "octane",
        "passport", "sanctum", "oauth"
    }
    
    # Intermediate topics (common Laravel features)
    intermediate_topics = {
        "authentication", "authorization", 
        "artisan", "scheduling", "commands", "command",
        "eloquent", "relationships", "polymorphic", "morphto", "pivot",
        "container", "migration", "schema", "database", "table", "column",
        "model", "query", "builder",
        "controller", "resource controller", "invokable",
        "request", "form request", "validation", "validate",
        "response", "json", "redirect", "view", "blade",
        "route", "routing", "named routes", "route model binding",
        "session", "cookie", "flash", "localization",
        "logging", "exception", "error handling",
        "configuration", "environment", "env", "config",
        "middleware", "policies", "gates", "policy"
    }
    
    # Check for beginner indicators first (only if no code)
    if not has_code:
        for indicator in beginner_indicators:
            if indicator in full_text:
                return "débutant"
    
    # Check for advanced topics in topic or subtopics
    for topic_keyword in advanced_topics:
        if topic_keyword in topic_str:
            return "avancé"
    
    # Also check for advanced keywords in instruction/output
    for topic_keyword in advanced_topics:
        if topic_keyword in instruction or topic_keyword in output:
            return "avancé"
    
    # Check for intermediate topics in topic or subtopics
    for topic_keyword in intermediate_topics:
        if topic_keyword in topic_str:
            return "intermédiaire"
    
    # Also check for intermediate keywords in instruction/output
    for topic_keyword in intermediate_topics:
        if topic_keyword in instruction or topic_keyword in output:
            return "intermédiaire"
    
    # Default: everything else is intermediate
    return "intermédiaire"


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


def main():
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

    # Load LLM configuration
    env_path = ROOT / ".env"
    env_vars = load_env_file(env_path)
    llm_config = load_llm_config(env_vars, sys.argv)

    # Run the processing pipeline
    all_qa, sections_by_doc, detected_version = run_pipeline(DOCS_ROOT, SKIP_FILES)

    # Optionally qualify with LLM if enabled
    if llm_config.enabled:
        all_qa = qualify_with_llm(all_qa, llm_config)

    # Add version tag to all Q&A items if detected
    if detected_version:
        for qa in all_qa:
            qa["version"] = detected_version

    # Ensure all Q&A items have qualification metadata for future manipulation
    # This allows splitting by score, filtering by usefulness, etc.
    for qa in all_qa:
        # Add qualification metadata if not present (LLM was disabled)
        if "qualification" not in qa:
            qa["qualification"] = {
                "useful": True,
                "tags": [],
                "level": determine_level_heuristic(qa),
                "has_code": False,
                "has_valid_code": False
            }
        
        # Sync has_code from top-level to qualification if present
        if "has_code" in qa:
            qa["qualification"]["has_code"] = qa["has_code"]
        
        # Sync has_valid_code from top-level to qualification if present
        if "has_valid_code" in qa:
            qa["qualification"]["has_valid_code"] = qa["has_valid_code"]
        
        # Add subtopics as tags to qualification for topic coverage calculation
        if "subtopics" in qa:
            qa["qualification"]["tags"] = qa["subtopics"]
        
        # Add niveau/level if not present
        if "niveau" not in qa:
            qa["niveau"] = qa["qualification"].get("level", "intermédiaire")
        if "level" not in qa:
            qa["level"] = qa["qualification"].get("level", "intermédiaire")
        
        # Add weight if not present (default based on level)
        if "weight" not in qa:
            level = qa.get("level", "intermédiaire")
            level_weights = {"débutant": 1.0, "intermédiaire": 1.5, "avancé": 2.0}
            qa["weight"] = level_weights.get(level, 1.0)
        
        # Calculate a composite score for filtering/sorting
        # Score formula: weight * (1 + has_code_bonus + useful_bonus + valid_code_bonus)
        qual = qa.get("qualification", {})
        has_code = qual.get("has_code", False)
        has_valid_code = qual.get("has_valid_code", False)
        useful = qual.get("useful", True)
        weight = qa.get("weight", 1.0)
        
        # Score calculation
        score = weight
        if has_code:
            score *= 1.3  # 30% bonus for code
        if has_valid_code:
            score *= 1.2  # Additional 20% bonus for valid code
        if useful:
            score *= 1.1  # 10% bonus for being useful
        
        qa["score"] = round(score, 4)

    # Write output files
    try:
        jsonl_path = OUTPUT_DIR / "laravel_training.jsonl"
        with jsonl_path.open("w", encoding="utf-8") as f:
            for item in all_qa:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")

        digest = build_knowledge_digest(sections_by_doc)
        (OUTPUT_DIR / "laravel_knowledge.md").write_text(digest, encoding="utf-8")

        # Generate few-shot examples
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
        has_valid_code_count = sum(1 for qa in all_qa if qa.get("qualification", {}).get("has_valid_code", False))
        total_weight = sum(qa.get("weight", 1.0) for qa in all_qa)
        
        # Calculate KPIs for training data quality
        total_with_code = has_code_count
        # NEW: valid_code_rate now measures code that is both present AND syntactically valid
        valid_code_rate = (has_valid_code_count / len(all_qa) * 100) if all_qa else 0.0
        # Keep the old rate as code_present_rate for reference
        code_present_rate = (has_code_count / len(all_qa) * 100) if all_qa else 0.0
        
        # Average response length
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
        
        # Unique Q&A ratio
        unique_instructions = len(set(qa.get("instruction", "") for qa in all_qa))
        uniqueness_rate = (unique_instructions / len(all_qa) * 100) if all_qa else 0.0
        
        meta = {
            "total_docs": len(sections_by_doc),
            "total_qa_pairs": len(all_qa),
            "total_weight": total_weight,
            "few_shot_count": len(examples[:14]),
            "detected_version": detected_version,
            "llm_config": {
                "enabled": llm_config.enabled,
                "api_url": llm_config.api_url,
                "model": llm_config.model
            },
            "kpis": {
                "valid_code_rate": round(valid_code_rate, 2),
                "code_present_rate": round(code_present_rate, 2),
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
        if llm_config.enabled:
            meta["useful_qa_count"] = useful_count
            meta["has_code_count"] = has_code_count
            meta["has_valid_code_count"] = has_valid_code_count
            
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
        
        # Also add level distribution even if LLM was not used
        if not llm_config.enabled:
            level_counts = {}
            for qa in all_qa:
                level = qa.get("niveau", qa.get("level", "inconnu"))
                level_counts[level] = level_counts.get(level, 0) + 1
            meta["level_distribution"] = level_counts
            meta["kpis"]["level_distribution"] = level_counts
        
        (OUTPUT_DIR / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        print(json.dumps(meta, indent=2))
    except (IOError, PermissionError) as e:
        raise SystemExit(f"Failed to write output files: {e}")


if __name__ == "__main__":
    main()

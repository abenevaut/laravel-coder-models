"""Generate Q&A items from sections module with code priority."""

import json
import re
import sys
import random
from pathlib import Path


def load_metadata() -> dict:
    """Load metadata from metadata.json file."""
    metadata_path = Path(__file__).parent.parent / "metadata.json"
    try:
        with open(metadata_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"TOPICS": {}}


# Load metadata at module level
METADATA = load_metadata()


def get_doc_topics(doc_name: str) -> list[str]:
    """Get all topic keywords for a document from metadata."""
    topics_str = METADATA.get("TOPICS", {}).get(doc_name, "")
    if not topics_str:
        return []
    
    # Split by comma and strip whitespace
    topics = [t.strip() for t in topics_str.split(",") if t.strip()]
    return topics


def has_php_code(text: str) -> bool:
    """Check if text contains PHP code.
    
    Uses the benchmark's has_php_code function for consistency.
    
    Args:
        text: Text to check for PHP code
        
    Returns:
        True if PHP code is detected
    """
    # Import benchmark's function
    try:
        benchmark_path = Path(__file__).parent.parent.parent / "benchmark" / "scripts"
        sys.path.insert(0, str(benchmark_path))
        from metrics import has_php_code as benchmark_has_php_code
        return benchmark_has_php_code(text)
    except (ImportError, ModuleNotFoundError):
        # Fallback to local implementation if benchmark not available
        if not text:
            return False
        
        # Laravel-specific patterns that indicate code
        LARAVEL_FUNCTIONS = [
            r'\bRoute::',
            r'\bModel::',
            r'\bDB::',
            r'\bAuth::',
            r'\bRequest::',
            r'\bResponse::',
            r'\bView::',
            r'\bValidator::',
            r'\bSchema::',
            r'\bEloquent\b',
            r'\bArtisan::',
            r'\bCache::',
            r'\bSession::',
            r'\bLog::',
            r'\bQueue::',
            r'\bEvent::',
            r'\bBroadcast::',
            r'->save\(\)',
            r'->find\(\)',
            r'->where\(\)',
            r'->get\(\)',
            r'->first\(\)',
            r'->all\(\)',
            r'->create\(\)',
            r'->update\(\)',
            r'->delete\(\)',
        ]
        
        LARAVEL_KEYWORDS = [
            'route', 'model', 'controller', 'migration', 'eloquent',
            'blade', 'middleware', 'validation', 'authentication',
            'authorization', 'request', 'response', 'view', 'cache',
            'session', 'queue', 'event', 'job', 'command', 'service',
            'provider', 'facade', 'container', 'dependency', 'injection',
            'database', 'schema', 'migration', 'seeder', 'factory',
            'test', 'feature', 'unit', 'http', 'json', 'api',
            'sanctum', 'passport', 'socialite', 'broadcasting',
            'websocket', 'reverb', 'octane', 'horizon', 'telescope',
            'scout', 'algolia', 'meilisearch'
        ]
        
        # Check for PHP code blocks
        if re.search(r'```php', text):
            return True
        
        # Check for inline PHP
        if '<?php' in text or '<?=' in text:
            return True
        
        # Check for Laravel-specific patterns
        for pattern in LARAVEL_FUNCTIONS:
            if re.search(pattern, text):
                return True
        
        # Check for Laravel keywords in code context
        # This matches the benchmark's logic
        for keyword in LARAVEL_KEYWORDS:
            if re.search(rf'\b{keyword}\b', text, re.IGNORECASE):
                # Check if it's in a code-like context
                if '::' in text or '->' in text or '(' in text:
                    return True
        
        return False


def has_valid_php_code(section: dict) -> bool:
    """Check if a section contains valid PHP code based on validation metadata.
    """
    code_validation = section.get('code_validation')
    if code_validation:
        has_valid = code_validation.get('has_valid_code', False)
        if has_valid:
            return True
        valid_count = code_validation.get('valid_code_block_count', 0)
        if valid_count > 0:
            return True
    body = section.get('body', '')
    return has_php_code(body)


def _make_qa(doc_name: str, section: dict) -> dict:
    """Generate a Q&A item from a documentation section.
    
    Args:
        doc_name: Document name
        section: Section dict with 'title' and 'body'
        
    Returns:
        Q&A item dict
    """
    base_topic = doc_name.replace(".md", "").replace("-", " ")
    question = f"Explain {base_topic}: {section['title']}"
    
    # Check if section contains valid code (using validation metadata if available)
    body = section.get("body", "")
    code_present = has_php_code(body)
    code_valid = has_valid_php_code(section)
    
    # Get all subtopics for this document from metadata
    subtopics = get_doc_topics(doc_name)
    
    # If no subtopics found, use the base topic
    topic = base_topic if not subtopics else subtopics[0]
    
    # Build Q&A item with validation metadata
    qa_item = {
        "instruction": question,
        "input": "",
        "output": body,
        "topic": topic,
        "has_code": code_present,
        "has_valid_code": code_valid,
        "code_valid": code_valid,  # Alias for backwards compatibility
        "subtopics": subtopics,  # Store all subtopics for coverage calculation
    }
    
    # Add validation metadata if available
    code_validation = section.get('code_validation')
    if code_validation:
        qa_item["code_validation"] = {
            "has_valid_code": code_validation.get('has_valid_code', code_valid),
            "code_block_count": code_validation.get('code_block_count', 0),
            "valid_code_block_count": code_validation.get('valid_code_block_count', 0),
            "validation_errors": code_validation.get('validation_errors', []),
        }
    
    return qa_item


def build_knowledge_digest(sections_by_doc: dict) -> str:
    """Build a knowledge digest markdown from processed sections."""
    lines = [
        "# Laravel Expert Knowledge Base (official docs)\n",
        "Comprehensive Laravel documentation processed for training.\n",
    ]

    for doc_name, sections in sorted(sections_by_doc.items()):
        topic = doc_name.replace(".md", "")
        lines.append(f"\n## {topic.upper()}")
        for sec in sections[:3]:
            summary = sec["body"][:350].replace("\n", " ")
            lines.append(f"- **{sec['title']}**: {summary}")

    return "\n".join(lines)


def generate_qa(data: dict, **kwargs) -> dict:
    """Pipeline step: Generate Q&A items from sections.
    
    Strategy: Balance code coverage and topic diversity.
    - Priority to sections WITH valid code (target: >50% valid code rate)
    - Include sections WITHOUT code for topic coverage (target: >30%)
    - Maximum of 6 Q&A per document
    - Minimum of 2 sections with valid code per document
    
    Input:  data["doc_name"] - document name
            data["sections"] - list of section dicts
    Output: data["qa_items"] - list of Q&A dicts
    """
    doc_name = data.get("doc_name", "unknown")
    print(f"  [{doc_name}] Running: generate_qa", file=sys.stderr)
    
    sections = data.get("sections", [])
    max_qa = 6  # Maximum Q&A per document
    min_code_sections = 5  # Minimum code sections required (with valid code)
    
    if not sections:
        data["qa_items"] = []
        print(f"  [{doc_name}] Finished: generate_qa (generated 0 Q&A items, 0 with code)", file=sys.stderr)
        return data
    
    # Separate sections by code validity
    sections_with_valid_code = []
    sections_with_invalid_code = []
    sections_without_code = []
    
    for sec in sections:
        # Use the new has_valid_php_code function that checks validation metadata
        if has_valid_php_code(sec):
            sections_with_valid_code.append(sec)
        elif has_php_code(sec.get("body", "")):
            sections_with_invalid_code.append(sec)
        else:
            sections_without_code.append(sec)
    
    # If document has less than min_code_sections with valid code, 
    # try to use sections with any code (even if not validated)
    if len(sections_with_valid_code) < min_code_sections:
        # Fall back to using sections with code (valid or not)
        all_code_sections = sections_with_valid_code + sections_with_invalid_code
        if len(all_code_sections) >= min_code_sections:
            sections_with_valid_code = all_code_sections
            sections_with_invalid_code = []
        else:
            # Still not enough code sections
            data["qa_items"] = []
            print(f"  [{doc_name}] Finished: generate_qa (generated 0 Q&A items, 0 with code) [insufficient code sections]", file=sys.stderr)
            return data
    
    # Sort sections by proximity to target length (125 tokens)
    # This helps achieve optimal average response length (~125 tokens)
    target_length = 125
    sections_with_valid_code.sort(key=lambda sec: abs(len(sec.get("body", "").split()) - target_length))
    sections_with_invalid_code.sort(key=lambda sec: abs(len(sec.get("body", "").split()) - target_length))
    sections_without_code.sort(key=lambda sec: abs(len(sec.get("body", "").split()) - target_length))
    
    # Target: Maximize valid code rate - use as many valid code sections as possible
    # This ensures valid_code_rate is maximized
    code_qa_count = min(len(sections_with_valid_code), max_qa)
    non_code_qa_count = max_qa - code_qa_count
    
    # Generate Q&A items
    qa_items = []
    
    # Add longest valid code sections first
    for sec in sections_with_valid_code[:code_qa_count]:
        qa_items.append(_make_qa(doc_name, sec))
    
    # If we still need more Q&A items and have sections with invalid code, add them
    remaining_slots = max_qa - len(qa_items)
    if remaining_slots > 0 and sections_with_invalid_code:
        for sec in sections_with_invalid_code[:remaining_slots]:
            qa_items.append(_make_qa(doc_name, sec))
            remaining_slots -= 1
    
    # Add longest non-code sections to reach max_qa
    if remaining_slots > 0:
        for sec in sections_without_code[:remaining_slots]:
            qa_items.append(_make_qa(doc_name, sec))
    
    data["qa_items"] = qa_items
    
    code_count = sum(1 for qa in qa_items if qa.get("has_code"))
    valid_code_count = sum(1 for qa in qa_items if qa.get("has_valid_code"))
    covered_topics = set()
    for qa in qa_items:
        covered_topics.update(qa.get("subtopics", []))
        covered_topics.add(qa.get("topic", ""))
    
    print(f"  [{doc_name}] Finished: generate_qa (generated {len(qa_items)} Q&A items, {code_count} with code, {valid_code_count} with valid code, topics: {len(covered_topics)})", file=sys.stderr)
    return data

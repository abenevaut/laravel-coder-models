"""Metrics calculation for Laravel LLM benchmark.

This module contains all the KPI calculation functions used to evaluate
LLM performance on Laravel documentation Q&A pairs.
"""

import json
import re
from typing import Any, Optional
from collections import Counter, defaultdict


# Laravel-specific patterns for validation
LARAVEL_FUNCTIONS = [
    r'\\Route::',
    r'\\Model::',
    r'\\DB::',
    r'\\Auth::',
    r'\\Request::',
    r'\\Response::',
    r'\\View::',
    r'\\Validator::',
    r'\\Schema::',
    r'\\Eloquent',
    r'\\Artisan::',
    r'\\Cache::',
    r'\\Session::',
    r'\\Log::',
    r'\\Queue::',
    r'\\Event::',
    r'\\Broadcast::',
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


def calculate_code_valid_rate(qa_items: list[dict]) -> float:
    """Calculate the rate of Q&A pairs with valid PHP code.
    
    Args:
        qa_items: List of Q&A dictionaries
        
    Returns:
        Percentage of items with valid PHP code
    """
    if not qa_items:
        return 0.0
    
    code_count = 0
    for qa in qa_items:
        output = qa.get("output", "")
        if has_php_code(output):
            code_count += 1
    
    return (code_count / len(qa_items)) * 100


def has_php_code(text: str) -> bool:
    """Check if text contains PHP code.
    
    Args:
        text: Text to check
        
    Returns:
        True if PHP code is detected
    """
    if not text:
        return False
    
    # Check for PHP code blocks
    php_blocks = re.findall(r'```php(.*?)```', text, re.DOTALL)
    if php_blocks:
        return True
    
    # Check for inline PHP
    if '<?php' in text or '<?=' in text:
        return True
    
    # Check for Laravel-specific patterns
    for pattern in LARAVEL_FUNCTIONS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    
    # Check for Laravel keywords in code context
    for keyword in LARAVEL_KEYWORDS:
        if re.search(rf'\b{keyword}\b', text, re.IGNORECASE):
            # Check if it's in a code-like context
            if '::' in text or '->' in text or '(' in text:
                return True
    
    return False


def calculate_topic_coverage_rate(qa_items: list[dict], defined_topics: set[str]) -> float:
    """Calculate the percentage of defined topics covered in Q&A pairs.
    
    Args:
        qa_items: List of Q&A dictionaries
        defined_topics: Set of defined topic keywords
        
    Returns:
        Coverage percentage
    """
    if not defined_topics:
        return 0.0
    
    covered_topics = set()
    
    for qa in qa_items:
        topic = qa.get("topic", "")
        if topic:
            covered_topics.add(topic.lower())
        
        # Also check tags
        tags = qa.get("qualification", {}).get("tags", [])
        for tag in tags:
            if tag.lower() in defined_topics:
                covered_topics.add(tag.lower())
    
    return (len(covered_topics & defined_topics) / len(defined_topics)) * 100


def calculate_avg_response_length(qa_items: list[dict]) -> float:
    """Calculate average response length in tokens.
    
    Args:
        qa_items: List of Q&A dictionaries
        
    Returns:
        Average number of tokens per response
    """
    if not qa_items:
        return 0.0
    
    total_tokens = sum(len(qa.get("output", "").split()) for qa in qa_items)
    return total_tokens / len(qa_items)


def calculate_uniqueness_rate(qa_items: list[dict]) -> float:
    """Calculate the uniqueness rate of instructions.
    
    Args:
        qa_items: List of Q&A dictionaries
        
    Returns:
        Percentage of unique instructions
    """
    if not qa_items:
        return 0.0
    
    unique_instructions = len(set(qa.get("instruction", "") for qa in qa_items))
    return (unique_instructions / len(qa_items)) * 100


def calculate_length_distribution(qa_items: list[dict]) -> dict[str, int]:
    """Calculate distribution of response lengths.
    
    Args:
        qa_items: List of Q&A dictionaries
        
    Returns:
        Dictionary with length brackets and counts
    """
    distribution = {
        "short (<50 tokens)": 0,
        "medium (50-200 tokens)": 0,
        "long (>200 tokens)": 0
    }
    
    for qa in qa_items:
        output = qa.get("output", "")
        token_count = len(output.split())
        
        if token_count < 50:
            distribution["short (<50 tokens)"] += 1
        elif token_count <= 200:
            distribution["medium (50-200 tokens)"] += 1
        else:
            distribution["long (>200 tokens)"] += 1
    
    return distribution


def calculate_level_distribution(qa_items: list[dict]) -> dict[str, int]:
    """Calculate distribution of difficulty levels.
    
    Args:
        qa_items: List of Q&A dictionaries
        
    Returns:
        Dictionary with level distribution
    """
    levels = defaultdict(int)
    
    for qa in qa_items:
        level = qa.get("level", qa.get("niveau", "intermédiaire"))
        levels[level] += 1
    
    return dict(levels)


def calculate_tag_distribution(qa_items: list[dict]) -> dict[str, int]:
    """Calculate distribution of tags from qualification.
    
    Args:
        qa_items: List of Q&A dictionaries
        
    Returns:
        Dictionary with tag counts, sorted by frequency
    """
    tag_counts = Counter()
    
    for qa in qa_items:
        tags = qa.get("qualification", {}).get("tags", [])
        tag_counts.update(tags)
    
    return dict(tag_counts.most_common())


def calculate_weight_distribution(qa_items: list[dict]) -> dict[str, int]:
    """Calculate distribution of weights.
    
    Args:
        qa_items: List of Q&A dictionaries
        
    Returns:
        Dictionary with weight distribution
    """
    weight_counts = defaultdict(int)
    
    for qa in qa_items:
        weight = qa.get("weight", 1.0)
        weight_key = f"{weight:.1f}"
        weight_counts[weight_key] += 1
    
    return dict(weight_counts)


def calculate_score_distribution(qa_items: list[dict], bins: list[float] = [0, 1.5, 2.0, 3.0]) -> dict[str, int]:
    """Calculate distribution of composite scores.
    
    Args:
        qa_items: List of Q&A dictionaries
        bins: Score bins for distribution
        
    Returns:
        Dictionary with score brackets and counts
    """
    distribution = {}
    
    for i in range(len(bins) - 1):
        lower = bins[i]
        upper = bins[i + 1]
        if i == len(bins) - 2:
            label = f">={lower:.1f}"
        else:
            label = f"{lower:.1f}-{upper:.1f}"
        distribution[label] = 0
    
    for qa in qa_items:
        score = qa.get("score", 0)
        for i in range(len(bins) - 1):
            if bins[i] <= score < bins[i + 1]:
                if i == len(bins) - 2:
                    label = f">={bins[i]:.1f}"
                else:
                    label = f"{bins[i]:.1f}-{bins[i+1]:.1f}"
                distribution[label] += 1
                break
    
    return distribution


def detect_hallucination_rate(qa_items: list[dict]) -> float:
    """Detect hallucination rate by checking for Laravel-specific inaccuracies.
    
    Args:
        qa_items: List of Q&A dictionaries
        
    Returns:
        Percentage of items with potential hallucinations
    """
    if not qa_items:
        return 0.0
    
    hallucination_count = 0
    
    # Common Laravel hallucination patterns
    hallucination_patterns = [
        # Non-existent Laravel functions
        r'\\bLaravel::nonExistent\b',
        r'\\bApp::fakeMethod\b',
        r'\\bRoute::invalidVerb\b',
        # Non-existent packages
        r'\\bNonExistentPackage\b',
        r'\\buse NonExistent\b',
        # Incorrect syntax - PHP 4 style function declaration (with function NAME)
        # This pattern specifically matches named functions with old syntax: function name() {
        # It does NOT match closures: function () { or function ($param) {
        r'\\bfunction\s+\w+\s*\([^)]*\)\s*\{',
        # JavaScript var in PHP context
        r'\\bvar\s+\$',
        # Impossible combinations
        r'\\bLaravel 15\.x\b',
        r'\\bPHP 9\.0\b',
    ]
    
    for qa in qa_items:
        output = qa.get("output", "")
        for pattern in hallucination_patterns:
            if re.search(pattern, output, re.IGNORECASE):
                hallucination_count += 1
                break
    
    return (hallucination_count / len(qa_items)) * 100


def calculate_quality_score(qa_items: list[dict]) -> float:
    """Calculate overall quality score (0-100).
    
    Args:
        qa_items: List of Q&A dictionaries
        
    Returns:
        Composite quality score
    """
    if not qa_items:
        return 0.0
    
    # Calculate individual metrics
    code_rate = calculate_code_valid_rate(qa_items)
    avg_length = calculate_avg_response_length(qa_items)
    uniqueness = calculate_uniqueness_rate(qa_items)
    
    # Normalize metrics to 0-100 scale
    # Code rate: 0-100 (already in %)
    # Avg length: target 50-200, normalize around 125
    length_score = max(0, 100 - abs(avg_length - 125))
    # Uniqueness: 0-100 (already in %)
    
    # Weighted average
    quality_score = (
        code_rate * 0.3 +    # 30% weight for code rate
        length_score * 0.2 +  # 20% weight for response length
        uniqueness * 0.2 +    # 20% weight for uniqueness
        30                   # 30% base score
    )
    
    return min(100, max(0, quality_score))


def extract_defined_topics(metadata_path: str) -> set[str]:
    """Extract defined topics from metadata.json.
    
    Args:
        metadata_path: Path to metadata.json file
        
    Returns:
        Set of all defined topic keywords
    """
    try:
        import json as json_module
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json_module.load(f)
        
        topics = set()
        for topic_tags in metadata.get("TOPICS", {}).values():
            for tag in topic_tags.split(","):
                topics.add(tag.strip().lower())
        
        return topics
    except (FileNotFoundError, json_module.JSONDecodeError):
        # Fallback to common Laravel topics
        return set(LARAVEL_KEYWORDS)

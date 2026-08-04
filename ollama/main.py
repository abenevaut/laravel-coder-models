#!/usr/bin/env python3
"""Generate Ollama Modelfile for Laravel fine-tuning.

Usage:
    python3 ollama/main.py --from mistral:7b
    python3 ollama/main.py --from mistral:7b --output my-laravel-coder
    python3 ollama/main.py --base-model llama3.2:3b --output laravel-coder-llama

This script generates an Ollama Modelfile using the processed Laravel documentation
data (laravel_training.jsonl) and metadata (meta.json) to create a specialized
Laravel expert model.
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime


DATA_DIR = Path(__file__).parent.parent / "laravel-docs-data"
META_FILE = DATA_DIR / "meta.json"
TRAINING_FILE = DATA_DIR / "laravel_training.jsonl"


def load_metadata() -> dict:
    """Load metadata from meta.json file."""
    if not META_FILE.exists():
        raise FileNotFoundError(f"Metadata file not found: {META_FILE}")
    
    with open(META_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def count_training_items() -> int:
    """Count the number of training items in laravel_training.jsonl."""
    if not TRAINING_FILE.exists():
        raise FileNotFoundError(f"Training file not found: {TRAINING_FILE}")
    
    count = 0
    with open(TRAINING_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                count += 1
    return count


def extract_topics_from_metadata(metadata: dict) -> list[str]:
    """Extract unique topics from metadata tag_distribution."""
    topics = set()
    tag_distribution = metadata.get("kpis", {}).get("tag_distribution", {})
    
    for tag in tag_distribution.keys():
        topics.add(tag)
    
    return sorted(topics)


def get_kpis(metadata: dict) -> dict:
    """Extract KPIs from metadata."""
    return metadata.get("kpis", {})


def get_version(metadata: dict) -> str:
    """Get Laravel version from metadata."""
    return metadata.get("detected_version", "13.x")


def load_sample_conversations(count: int = 100) -> list[dict]:
    """Load sample conversations from training data for MESSAGE examples."""
    if not TRAINING_FILE.exists():
        return []
    
    conversations = []
    with open(TRAINING_FILE, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i >= count:
                break
            if line.strip():
                try:
                    data = json.loads(line)
                    conversations.append({
                        "instruction": data.get("instruction", ""),
                        "output": data.get("output", ""),
                        "topic": data.get("topic", "Laravel"),
                        "version": data.get("version", "13.x")
                    })
                except json.JSONDecodeError:
                    continue
    return conversations


def format_topics_list(topics: list[str], max_items: int = 15) -> str:
    """Format topics list for SYSTEM prompt."""
    if len(topics) <= max_items:
        return ", ".join(topics)
    
    # Group by category
    core_topics = [t for t in topics if any(word in t.lower() for word in ["routing", "controller", "middleware", "request", "response", "validation"])]
    orm_topics = [t for t in topics if any(word in t.lower() for word in ["eloquent", "model", "database", "migration", "query", "relationship"])]
    auth_topics = [t for t in topics if any(word in t.lower() for word in ["auth", "sanctum", "passport", "guard", "policy"])]
    other_topics = [t for t in topics if t not in core_topics and t not in orm_topics and t not in auth_topics]
    
    formatted = []
    if core_topics:
        formatted.append("Core: " + ", ".join(core_topics[:5]))
    if orm_topics:
        formatted.append("Eloquent/ORM: " + ", ".join(orm_topics[:5]))
    if auth_topics:
        formatted.append("Authentication: " + ", ".join(auth_topics[:5]))
    if other_topics:
        formatted.append("Other: " + ", ".join(other_topics[:5]))
    
    return "; ".join(formatted) + ("..." if len(topics) > max_items else "")


def generate_system_prompt(metadata: dict, training_count: int, topics: list[str]) -> str:
    """Generate comprehensive SYSTEM prompt based on metadata and training data."""
    version = get_version(metadata)
    kpis = get_kpis(metadata)
    
    valid_code_rate = kpis.get("valid_code_rate", 100.0)
    topic_coverage = kpis.get("topic_coverage_rate", 100.0)
    uniqueness_rate = kpis.get("uniqueness_rate", 99.44)
    avg_length = kpis.get("avg_response_length_tokens", 114.51)
    
    formatted_topics = format_topics_list(topics)
    
    system_prompt = f"""You are Bob, a legendary senior PHP and Laravel architect with over 10 years of hands-on experience building production Laravel applications at scale.

## Identity
- Your name is Bob. Always introduce yourself as Bob when asked who you are.
- You ONLY specialize in PHP and Laravel ecosystem development. Politely decline non-PHP/Laravel topics.
- You speak like a seasoned mentor: precise, practical, opinionated when it matters, never hand-wavy.
- You always respond in French, using clear and professional language.

## Laravel Version Support
You support Laravel {version}. **Always identify the user's Laravel version BEFORE giving solutions.**

### Version detection (do this first)
Inspect the user's code, files, or context for:
1. **composer.json** — `"laravel/framework": "^{version}"`
2. **bootstrap/app.php** — Check for Application::configure() (Laravel 11+) or traditional structure (Laravel 10)
3. **config/app.php** — providers/middleware arrays
4. **Feature signals** — bootstrap/providers.php (11+), routes/console.php patterns
5. **User statement** — if they mention a specific Laravel version, use that

If the version is unclear, **ask one short clarifying question** before giving version-specific code. Never silently assume a version when the answer would differ.

### Version-specific answers
- State which Laravel version your answer targets: e.g. "For Laravel 11+..." or "On Laravel 10, use..."
- When APIs differ across versions, show the correct approach for the detected version and briefly note what changed in other versions
- Prefer official patterns for that release (middleware registration, service provider layout, routing, validation, Eloquent casts, etc.)

## Expertise (10+ years)
You have deep mastery of the entire Laravel framework and PHP ecosystem for version {version}:
- Core: routing, middleware, controllers, requests, responses, validation
- Eloquent ORM: relationships (hasMany, belongsTo, morphTo, etc.), scopes, casts, mutators, accessors, query optimization, N+1 prevention
- Database: migrations, seeders, factories, query builder, transactions, indexing strategies
- Architecture: service container, service providers, facades, contracts, repository patterns
- Auth: Sanctum, Passport, Fortify, policies, gates, multi-guard setups
- Queues & Jobs: Horizon, failed job handling, batching, unique jobs, rate limiting
- Events, listeners, observers, model events
- Blade, Livewire, Inertia, Vue/React integration patterns
- API design: REST, resources, API versioning, pagination, filtering
- Testing: PHPUnit, Pest, feature/unit tests, mocking, database testing, HTTP tests
- DevOps: Sail, Forge, Vapor, Octane, deployment, caching (Redis), sessions
- Packages: Scout, Telescope, Pulse, Pennant, Cashier, Socialite, Reverb, broadcasting
- PHP 8.x: enums, attributes, readonly, fibers, strict types, PSR standards

### Specialized Topics
{formatted_topics}

## Response Style
- Give production-ready PHP/Laravel code with proper namespaces, type hints, and Laravel conventions
- Prefer Laravel's built-in features over reinventing the wheel
- **Lead with detected (or assumed) Laravel version** when it affects the answer
- Warn about common pitfalls (N+1 queries, mass assignment, missing indexes, queue timeouts)
- Use artisan commands, config patterns, and env conventions correctly for the target version
- Structure answers: version note → brief explanation → code → key notes/warnings
- Always provide working, testable code examples with proper error handling
- Explain the "why" behind your answers, not just the "how"

## Rules
- Never generate code for Python, JavaScript frameworks (unless Laravel frontend integration), Go, Ruby, etc.
- Always follow PSR-12 and Laravel naming conventions
- Use `php artisan make:*` commands when suggesting new files
- Reference official Laravel patterns from laravel.com docs for the applicable version
- Always respond in French

## Quality Standards
This model was trained on {training_count:,} Laravel documentation Q&A pairs with:
- Code validity rate: {valid_code_rate:.1f}%
- Topic coverage rate: {topic_coverage:.1f}%
- Uniqueness rate: {uniqueness_rate:.1f}%
- Average response length: {avg_length:.1f} tokens

## Training Data
Trained on comprehensive Laravel {version} documentation covering all major framework components and patterns.

[Knowledge base retained — Bob maintains full Laravel {version} expertise]"""
    
    return system_prompt


def generate_template() -> str:
    """Generate TEMPLATE for fine-tuning."""
    template = """[INST] {{ .Prompt }} [/INST]
{{ .Response }}"""
    return template


def generate_messages(samples: list[dict]) -> str:
    """Generate MESSAGE examples from sample conversations."""
    if not samples:
        return ""
    
    messages = []
    for sample in samples:  # Use all provided samples
        instruction = sample.get("instruction", "")
        output = sample.get("output", "")
        topic = sample.get("topic", "Laravel")
        
        if instruction and output:
            # Clean up the output for the message
            clean_output = output.replace('"""', '"').replace("\n\n\n", "\n\n")
            messages.append(f'MESSAGE user """[{topic}] {instruction}"""')
            messages.append(f'MESSAGE assistant """{clean_output}"""')
    
    return "\n".join(messages)


def generate_modelfile(base_model: str, output_path: Path, metadata: dict, training_count: int, samples: list[dict]) -> str:
    """Generate the complete Modelfile content."""
    version = get_version(metadata)
    kpis = get_kpis(metadata)
    topics = extract_topics_from_metadata(metadata)
    
    system_prompt = generate_system_prompt(metadata, training_count, topics)
    template = generate_template()
    messages = generate_messages(samples)
    
    # Generate timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    
    valid_code_rate = kpis.get("valid_code_rate", 100.0)
    topic_coverage = kpis.get("topic_coverage_rate", 100.0)
    
    modelfile_content = f"""# Laravel Coder Model - Generated {timestamp}
# Base: {base_model} | Persona: Bob | Specialty: PHP/Laravel only
# Training data: {training_count:,} Q&A pairs from Laravel {version} documentation
# Quality metrics: {valid_code_rate:.1f}% code valid, {topic_coverage:.1f}% topic coverage

FROM {base_model}

PARAMETER temperature 0.3
PARAMETER top_p 0.9
PARAMETER num_ctx 8192
PARAMETER num_predict 2048

"""
    
    modelfile_content += f'SYSTEM """{system_prompt}"""\n\n'
    
    if messages:
        modelfile_content += f"{messages}\n\n"
    
    modelfile_content += f'TEMPLATE """{template}"""\n\n'
    
    modelfile_content += f"LICENSE \"\"\"MIT License — {base_model.split(':')[0]} (original model) + Laravel docs (MIT)\"\"\""
    
    return modelfile_content


def main():
    parser = argparse.ArgumentParser(
        description="Generate Ollama Modelfile for Laravel fine-tuning"
    )
    parser.add_argument(
        "--from",
        "--base-model",
        type=str,
        required=True,
        dest="base_model",
        help="Base model to use (e.g., mistral:7b, llama3.2:3b)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output file name (without extension). Default: laravel-coder-<base-model>"
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=100,
        help="Number of sample conversations to include in MESSAGE (default: 100, max: 540)"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Minimal output"
    )
    
    args = parser.parse_args()
    
    # Load metadata
    try:
        metadata = load_metadata()
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        print("   Run laravel-docs-process/main.py first to generate data.", file=sys.stderr)
        sys.exit(1)
    
    # Count training items
    try:
        training_count = count_training_items()
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        print("   Run laravel-docs-process/main.py first to generate data.", file=sys.stderr)
        sys.exit(1)
    
    # Load sample conversations
    samples = load_sample_conversations(args.samples)
    
    # Extract topics
    topics = extract_topics_from_metadata(metadata)
    
    # Determine output path
    if args.output:
        output_file = Path(args.output)
    else:
        # Sanitize model name for filename
        safe_name = args.base_model.replace(":", "-").replace("/", "-")
        output_file = Path(f"laravel-coder-{safe_name}.Modelfile")
    
    # Ensure output is in ollama directory
    if output_file.parent == Path("."):
        output_file = Path(__file__).parent / output_file
    
    # Generate Modelfile
    modelfile_content = generate_modelfile(
        base_model=args.base_model,
        output_path=output_file,
        metadata=metadata,
        training_count=training_count,
        samples=samples
    )
    
    # Save Modelfile
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(modelfile_content)
    
    if not args.quiet:
        print(f"Modelfile generated: {output_file}")
        print(f"   Base model: {args.base_model}")
        print(f"   Training data: {training_count:,} Q&A pairs")
        print(f"   Laravel version: {get_version(metadata)}")
        print(f"   Topics covered: {len(topics)}")
        print(f"   Sample messages: {len(samples)}")
        print()
        print("To create the model with Ollama:")
        print(f"   ollama create {output_file.name} -f {output_file}")
        print()
        print("To run the model:")
        print(f"   ollama run {output_file.name}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

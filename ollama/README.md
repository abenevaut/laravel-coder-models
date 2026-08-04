# Ollama Modelfile Generator for Laravel Coder

This directory contains the script to generate Ollama Modelfiles for fine-tuning Laravel expert models.

## Usage

Generate a Modelfile for a specific base model:

```bash
# Generate with default output name (100 samples)
python3 ollama/main.py --from mistral:7b

# Generate with custom output name
python3 ollama/main.py --from mistral:7b --output laravel-coder-mistral

# Generate with custom number of sample messages (default: 100)
python3 ollama/main.py --from llama3.2:3b --output laravel-coder-llama --samples 200

# Use all available training data (540 samples)
python3 ollama/main.py --from mistral:7b --samples 540

# Quiet mode (minimal output)
python3 ollama/main.py --from mistral:7b --quiet
```

## Output

The script generates a Modelfile with the following structure:

```
# Laravel Coder Model - Generated <timestamp>
# Base: <model> | Persona: Bob | Specialty: PHP/Laravel only
# Training data: X Q&A pairs from Laravel 13.x documentation
# Quality metrics: XX% code valid, XX% topic coverage

FROM <model>

PARAMETER temperature 0.3
PARAMETER top_p 0.9
PARAMETER num_ctx 8192
PARAMETER num_predict 2048

SYSTEM """...
   - Bob persona with 10+ years Laravel experience
   - Version detection guidelines
   - Expertise areas (Core, Eloquent, Auth, etc.)
   - Response style and rules
   - Quality standards from training data"""

MESSAGE user """[topic] question"""
MESSAGE assistant """answer"""
...

TEMPLATE """[INST] {{ .Prompt }} [/INST]
{{ .Response }}"""

LICENSE """MIT License"""
```

## Requirements

- Python 3.7+
- Processed Laravel documentation data in `laravel-docs-data/`
  - `meta.json` - Metadata with KPIs and version info
  - `laravel_training.jsonl` - Training Q&A pairs

## Create the Model with Ollama

After generating the Modelfile, create and run the model:

```bash
# Create the model
ollama create laravel-coder-mistral-7b -f ollama/laravel-coder-mistral-7b.Modelfile

# Run the model
ollama run laravel-coder-mistral-7b
```

## Features

- **Automatic data detection**: Reads from `laravel-docs-data/` directory
- **Comprehensive SYSTEM prompt**: Includes persona, expertise, guidelines, and quality metrics
- **Sample conversations**: Includes real Q&A pairs as MESSAGE examples
- **Flexible output**: Custom output file names supported
- **Version-aware**: Detects and includes Laravel version from metadata

## Data Sources

The Modelfile is generated using:
- Version: `detected_version` from meta.json
- Topics: `tag_distribution` from meta.json kpis
- Training count: Number of entries in laravel_training.jsonl
- KPIs: Quality metrics from meta.json
- Samples: First N entries from laravel_training.jsonl

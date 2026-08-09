## Laravel Docs Processor

This project processes Laravel documentation into training data for fine-tuning language models.

## Initialization and Execution

### 1. Initialize the Laravel docs git submodule:
```bash
git submodule add --branch 13.x https://github.com/laravel/docs.git laravel-docs
git submodule update --remote
```

### 2. Run the processing script:
```bash
python3 laravel-docs-process/main.py
```

### 3. Run with LLM qualification (Mistral API):
```bash
# Enable LLM qualification
python3 laravel-docs-process/main.py --llm

# Or set LLM_ENABLED=true in .env file
```

## LLM Configuration

The project supports both **Mistral API** (recommended) and **Ollama** (local).

### Mistral API (Recommended)
1. Get your API key from [Mistral Console](https://console.mistral.ai/)
2. Configure in `.env`:
```bash
LLM_ENABLED=true
LLM_API_URL=https://api.mistral.ai/v1
LLM_MODEL=mistral-small
LLM_API_KEY=your_api_key_here
```

3. Install required dependencies:
```bash
pip install -r requirements.txt
```

### Ollama (Local Alternative)
If you prefer local LLM:
```bash
LLM_ENABLED=true
LLM_API_URL=http://localhost:11434
LLM_MODEL=llama3.2:3b
LLM_API_KEY=
```

Run Ollama server:
```bash
ollama serve
ollama pull llama3.2:3b
```

## Output Files

The processor generates the following files in `laravel-docs-data/`:
- `laravel_training.jsonl` - Training data in JSONL format
- `laravel_knowledge.md` - Knowledge digest
- `few_shot_examples.json` - Example Q&A pairs
- `meta.json` - Processing metadata and KPIs

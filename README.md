## Initialization and Execution

Initialize the Laravel docs git submodule:
```bash
git submodule add --branch 13.x https://github.com/laravel/docs.git laravel-docs
git submodule update --remote
```

Run the processing script:
```bash
python3 laravel-docs-process/main.py
```

Run with LLM qualification:
```bash
python3 laravel-docs-process/main.py --llm
```

Install LLM dependencies:
```bash
pip install -r requirements.txt
ollama serve
ollama pull qwen3.5:4b-mlx
```

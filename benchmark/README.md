# Laravel LLM Benchmark

## 🚀 Installation

```bash
pip install -r requirements.txt
```

## 📊 Commandes

### Benchmark de base
```bash
# Exécuter le benchmark complet
python benchmark/main.py

# Évaluer seulement les 100 premières paires (plus rapide)
python benchmark/main.py --limit 100

# Spécifier un nom de modèle
python benchmark/main.py --model "mistral-small"
```

### Benchmark de comparaison
```bash
# Benchmarker Mistral API
python benchmark/main.py --model "mistral-small" --output benchmark/results/mistral

# Benchmarker Ollama local
python benchmark/main.py --model "ollama-mistral:7b" --output benchmark/results/ollama

# Comparer avec les résultats précédents
python benchmark/main.py --model "comparaison" --compare
```

### Options de sortie
```bash
# Générer seulement le rapport JSON
python benchmark/main.py --json

# Générer seulement le rapport HTML
python benchmark/main.py --html

# Mode silencieux (pas d'affichage console)
python benchmark/main.py --quiet
```

## 📁 Sortie

- **JSON** : `benchmark/results/benchmark_{model}_{timestamp}.json`
- **HTML** : `benchmark/reports/report_{timestamp}.html`
- **Comparaison** : `benchmark/reports/comparison_{timestamp}.html`

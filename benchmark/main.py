#!/usr/bin/env python3
"""Main benchmark execution script.

This script runs the complete Laravel LLM benchmark and generates reports.
Usage:
    python run_benchmark.py                    # Run with default data
    python run_benchmark.py --data-path /path/to/laravel_training.jsonl  # Custom data
    python run_benchmark.py --limit 100        # Evaluate first 100 items only
    python run_benchmark.py --model ollama     # Benchmark Ollama model
    python run_benchmark.py --compare           # Compare with previous results
"""

#!/usr/bin/env python3
"""Main benchmark execution script.

This script runs the complete Laravel LLM benchmark and generates reports.
Usage:
    python main.py                    # Run with default data
    python main.py --data-path /path/to/laravel_training.jsonl  # Custom data
    python main.py --limit 100        # Evaluate first 100 items only
    python main.py --model ollama     # Benchmark Ollama model
    python main.py --compare           # Compare with previous results
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from scripts.evaluator import LaravelEvaluator
from scripts.report import generate_html_report, generate_comparison_report, generate_json_report


def main():
    parser = argparse.ArgumentParser(description="Laravel LLM Benchmark")
    parser.add_argument("--data-path", type=str, 
                        help="Path to laravel_training.jsonl file")
    parser.add_argument("--model", type=str, default="laravel-coder",
                        help="Model name for this benchmark")
    parser.add_argument("--limit", type=int, default=None,
                        help="Limit number of Q&A pairs to evaluate")
    parser.add_argument("--output", type=str, 
                        help="Output directory for reports")
    parser.add_argument("--json", action="store_true",
                        help="Output JSON report only")
    parser.add_argument("--html", action="store_true",
                        help="Output HTML report only")
    parser.add_argument("--compare", action="store_true",
                        help="Compare with previous benchmark results")
    parser.add_argument("--quiet", action="store_true",
                        help="Minimal output")
    
    args = parser.parse_args()
    
    if not args.quiet:
        print("🚀 Laravel LLM Benchmark")
        print("=" * 50)
    
    # Initialize evaluator
    evaluator = LaravelEvaluator(
        data_path=args.data_path,
        model_name=args.model
    )
    
    # Load and evaluate data
    if not args.quiet:
        print(f"📖 Chargement des données depuis: {evaluator.data_path}")
    
    evaluator.load_data(limit=args.limit)
    
    if not args.quiet:
        print(f"📊 Évaluation de {len(evaluator.qa_items)} paires Q/R...")
    
    result = evaluator.evaluate(limit=args.limit)
    
    if not args.quiet:
        print(f"✅ Benchmark terminé en {result.execution_time:.2f} secondes")
        print(f"\n📈 Résultats:")
        print(f"   Taux de code valide: {result.code_valid_rate:.2f}%")
        print(f"   Couverture des topics: {result.topic_coverage_rate:.2f}%")
        print(f"   Longueur moyenne: {result.avg_response_length:.2f} tokens")
        print(f"   Taux d'unicité: {result.uniqueness_rate:.2f}%")
        print(f"   Taux d'hallucination: {result.hallucination_rate:.2f}%")
        print(f"   Score de qualité: {result.quality_score:.2f}/100")
        print(f"   Version Laravel: {result.version or 'N/A'}")
    
    # Save results
    output_dir = args.output if args.output else None
    
    # Always save JSON
    json_path = evaluator.save_results(result, output_dir)
    if not args.quiet:
        print(f"\n💾 JSON rapport sauvegardé: {json_path}")
    
    # Generate HTML report unless --json only
    if not args.json:
        html_path = generate_html_report([result.to_dict()], output_dir)
        if not args.quiet:
            print(f"📄 HTML rapport sauvegardé: {html_path}")
    
    # Generate comparison if requested
    if args.compare:
        if not args.quiet:
            print("\n🔄 Comparaison avec les résultats précédents...")
        
        # Load previous results
        benchmark_dir = Path(__file__).parent
        results_dir = Path(output_dir) if output_dir else benchmark_dir / "results"
        previous_results = []
        
        if results_dir.exists():
            for json_file in results_dir.glob("benchmark_*.json"):
                if json_file.name != Path(json_path).name:  # Exclude current
                    try:
                        with open(json_file, 'r', encoding='utf-8') as f:
                            previous_results.append(json.load(f))
                    except (json.JSONDecodeError, IOError):
                        continue
        
        if previous_results:
            all_results = [result.to_dict()] + previous_results
            comparison_path = generate_comparison_report(all_results, output_dir)
            if not args.quiet:
                print(f"📊 Rapport de comparaison: {comparison_path}")
                print(f"   Comparaison avec {len(previous_results)} résultat(s) précédent(s)")
        else:
            if not args.quiet:
                print("⚠️  Aucun résultat précédent trouvé pour la comparaison")
    
    if not args.quiet:
        print("\n✨ Benchmark terminé avec succès!")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

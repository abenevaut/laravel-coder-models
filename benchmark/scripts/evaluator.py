"""Laravel LLM Evaluator.

Main benchmark module that evaluates LLM performance on Laravel documentation
Q&A pairs using multiple KPIs.
"""

import json
import time
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

from .metrics import (
    calculate_code_valid_rate,
    calculate_topic_coverage_rate,
    calculate_avg_response_length,
    calculate_uniqueness_rate,
    calculate_length_distribution,
    calculate_level_distribution,
    calculate_tag_distribution,
    calculate_weight_distribution,
    calculate_score_distribution,
    detect_hallucination_rate,
    calculate_quality_score,
    extract_defined_topics,
)


@dataclass
class BenchmarkResult:
    """Container for benchmark results."""
    model_name: str
    timestamp: str
    data_source: str
    total_qa_pairs: int
    
    # KPIs
    code_valid_rate: float = 0.0
    topic_coverage_rate: float = 0.0
    avg_response_length: float = 0.0
    uniqueness_rate: float = 0.0
    hallucination_rate: float = 0.0
    quality_score: float = 0.0
    
    # Distributions
    length_distribution: dict = field(default_factory=dict)
    level_distribution: dict = field(default_factory=dict)
    tag_distribution: dict = field(default_factory=dict)
    weight_distribution: dict = field(default_factory=dict)
    score_distribution: dict = field(default_factory=dict)
    
    # Additional metadata
    version: Optional[str] = None
    execution_time: float = 0.0
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "model_name": self.model_name,
            "timestamp": self.timestamp,
            "data_source": self.data_source,
            "total_qa_pairs": self.total_qa_pairs,
            "kpis": {
                "code_valid_rate": round(self.code_valid_rate, 2),
                "target_code_valid_rate": "> 50%",
                "topic_coverage_rate": round(self.topic_coverage_rate, 2),
                "target_topic_coverage": "> 95%",
                "avg_response_length": round(self.avg_response_length, 2),
                "target_avg_length": "50-200 tokens",
                "uniqueness_rate": round(self.uniqueness_rate, 2),
                "target_uniqueness": "> 95%",
                "hallucination_rate": round(self.hallucination_rate, 2),
                "target_hallucination": "< 1%",
                "quality_score": round(self.quality_score, 2),
            },
            "distributions": {
                "length": self.length_distribution,
                "level": self.level_distribution,
                "tag": {k: v for k, v in list(self.tag_distribution.items())[:20]},
                "weight": self.weight_distribution,
                "score": self.score_distribution,
            },
            "version": self.version,
            "execution_time": round(self.execution_time, 2),
        }


class LaravelEvaluator:
    """Main evaluator class for Laravel LLM benchmarking."""
    
    def __init__(self, data_path: Optional[str] = None, model_name: str = "laravel-coder"):
        """Initialize the evaluator.
        
        Args:
            data_path: Path to laravel_training.jsonl or directory
            model_name: Name of the model being evaluated
        """
        self.data_path = data_path or Path(__file__).parent.parent.parent / "laravel-docs-data" / "laravel_training.jsonl"
        self.model_name = model_name
        self.qa_items = []
        self.metadata_path = Path(__file__).parent.parent.parent / "laravel-docs-process" / "metadata.json"
    
    def load_data(self, limit: Optional[int] = None) -> list[dict]:
        """Load Q&A pairs from JSONL file.
        
        Args:
            limit: Maximum number of items to load (None for all)
            
        Returns:
            List of Q&A dictionaries
        """
        data_path = Path(self.data_path)
        
        if not data_path.exists():
            # Try alternative paths
            alt_paths = [
                Path(__file__).parent.parent.parent / "laravel-docs-data" / "laravel_training.jsonl",
                Path(__file__).parent.parent.parent.parent / "laravel-docs-data" / "laravel_training.jsonl",
                Path("../laravel-docs-data/laravel_training.jsonl"),
            ]
            for p in alt_paths:
                if p.exists():
                    data_path = p
                    break
        
        if not data_path.exists():
            raise FileNotFoundError(f"Could not find laravel_training.jsonl at {self.data_path}")
        
        self.qa_items = []
        with open(data_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if limit and i >= limit:
                    break
                try:
                    item = json.loads(line)
                    self.qa_items.append(item)
                except json.JSONDecodeError:
                    continue
        
        return self.qa_items
    
    def extract_version(self) -> Optional[str]:
        """Extract version from Q&A items."""
        versions = set()
        for qa in self.qa_items:
            if "version" in qa:
                versions.add(qa["version"])
        
        if len(versions) == 1:
            return list(versions)[0]
        elif versions:
            # Return most common version
            from collections import Counter
            return Counter(versions).most_common(1)[0][0]
        return None
    
    def evaluate(self, limit: Optional[int] = None) -> BenchmarkResult:
        """Run full benchmark evaluation.
        
        Args:
            limit: Maximum number of items to evaluate
            
        Returns:
            BenchmarkResult with all KPIs
        """
        start_time = time.time()
        
        # Load data
        self.load_data(limit)
        
        if not self.qa_items:
            raise ValueError("No Q&A pairs loaded for evaluation")
        
        # Extract defined topics from metadata
        defined_topics = extract_defined_topics(self.metadata_path)
        
        # Calculate all KPIs
        code_valid_rate = calculate_code_valid_rate(self.qa_items)
        topic_coverage_rate = calculate_topic_coverage_rate(self.qa_items, defined_topics)
        avg_response_length = calculate_avg_response_length(self.qa_items)
        uniqueness_rate = calculate_uniqueness_rate(self.qa_items)
        hallucination_rate = detect_hallucination_rate(self.qa_items)
        quality_score = calculate_quality_score(self.qa_items)
        
        # Calculate distributions
        length_distribution = calculate_length_distribution(self.qa_items)
        level_distribution = calculate_level_distribution(self.qa_items)
        tag_distribution = calculate_tag_distribution(self.qa_items)
        weight_distribution = calculate_weight_distribution(self.qa_items)
        score_distribution = calculate_score_distribution(self.qa_items)
        
        # Extract version
        version = self.extract_version()
        
        execution_time = time.time() - start_time
        
        result = BenchmarkResult(
            model_name=self.model_name,
            timestamp=datetime.now().isoformat(),
            data_source=str(self.data_path),
            total_qa_pairs=len(self.qa_items),
            code_valid_rate=code_valid_rate,
            topic_coverage_rate=topic_coverage_rate,
            avg_response_length=avg_response_length,
            uniqueness_rate=uniqueness_rate,
            hallucination_rate=hallucination_rate,
            quality_score=quality_score,
            length_distribution=length_distribution,
            level_distribution=level_distribution,
            tag_distribution=tag_distribution,
            weight_distribution=weight_distribution,
            score_distribution=score_distribution,
            version=version,
            execution_time=execution_time,
        )
        
        return result
    
    def save_results(self, result: BenchmarkResult, output_path: Optional[str] = None) -> str:
        """Save benchmark results to JSON file.
        
        Args:
            result: BenchmarkResult to save
            output_path: Output file path (default: benchmark/results/)
            
        Returns:
            Path to saved file
        """
        output_dir = Path(output_path) if output_path else Path(__file__).parent.parent / "results"
        output_dir.mkdir(exist_ok=True, parents=True)
        
        filename = f"benchmark_{self.model_name}_{result.timestamp.replace(':', '-').replace('.', '-')}.json"
        filepath = output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)
        
        return str(filepath)
    
    def compare_models(self, results: list[BenchmarkResult]) -> dict:
        """Compare multiple benchmark results.
        
        Args:
            results: List of BenchmarkResult objects
            
        Returns:
            Comparison dictionary
        """
        if not results:
            return {}
        
        comparison = {
            "models": [r.model_name for r in results],
            "kpis": {}
        }
        
        # Compare each KPI
        kpis_to_compare = [
            "code_valid_rate",
            "topic_coverage_rate",
            "avg_response_length",
            "uniqueness_rate",
            "hallucination_rate",
            "quality_score",
        ]
        
        for kpi in kpis_to_compare:
            comparison["kpis"][kpi] = {
                r.model_name: getattr(r, kpi)
                for r in results
            }
        
        # Find best model for each KPI
        comparison["best"] = {}
        for kpi in kpis_to_compare:
            values = {r.model_name: getattr(r, kpi) for r in results}
            best_model = max(values, key=values.get)
            comparison["best"][kpi] = best_model
        
        return comparison

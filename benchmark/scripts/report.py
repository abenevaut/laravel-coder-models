"""Report generation for Laravel LLM benchmark.

Generates HTML and JSON reports with visualizations of benchmark results.
"""

import json
from pathlib import Path
from typing import Any, Optional
from datetime import datetime

try:
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    import matplotlib.pyplot as plt
    from matplotlib import cm
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


def generate_html_report(results: list[dict], output_path: Optional[str] = None) -> str:
    """Generate HTML report from benchmark results.
    
    Args:
        results: List of benchmark result dictionaries
        output_path: Output file path
        
    Returns:
        Path to generated HTML file
    """
    if not results:
        raise ValueError("No results to generate report from")
    
    # Sort by timestamp (newest first)
    results = sorted(results, key=lambda x: x.get("timestamp", ""), reverse=True)
    latest = results[0]
    
    output_dir = Path(output_path) if output_path else Path(__file__).parent.parent / "reports"
    output_dir.mkdir(exist_ok=True, parents=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"report_{timestamp}.html"
    filepath = output_dir / filename
    
    # Generate HTML content
    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Benchmark Rapport - Laravel LLM</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background: white;
            border-radius: 10px;
            padding: 30px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #6366f1;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #555;
            margin-top: 30px;
        }}
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .kpi-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .kpi-card h3 {{
            margin: 0 0 10px 0;
            font-size: 14px;
            opacity: 0.9;
        }}
        .kpi-card .value {{
            font-size: 32px;
            font-weight: bold;
        }}
        .kpi-card .target {{
            font-size: 12px;
            opacity: 0.8;
            margin-top: 5px;
        }}
        .status-good {{
            background: rgba(255,255,255,0.2);
            padding: 2px 8px;
            border-radius: 4px;
            display: inline-block;
            margin-top: 5px;
        }}
        .status-bad {{
            background: rgba(255,0,0,0.2);
            padding: 2px 8px;
            border-radius: 4px;
            display: inline-block;
            margin-top: 5px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #6366f1;
            color: white;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
        .chart-container {{
            position: relative;
            height: 400px;
            margin: 30px 0;
        }}
        .model-comparison {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }}
        .comparison-card {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            border-left: 4px solid #6366f1;
        }}
        .best-badge {{
            background: #10b981;
            color: white;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            display: inline-block;
            margin-left: 10px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Laravel LLM Benchmark Report</h1>
        
        <div style="margin: 20px 0; color: #666;">
            <strong>Modèle:</strong> {latest.get('model_name', 'N/A')} | 
            <strong>Date:</strong> {latest.get('timestamp', 'N/A')} | 
            <strong>Version Laravel:</strong> {latest.get('version', 'N/A')} | 
            <strong>Total Q&A:</strong> {latest.get('total_qa_pairs', 0)}
        </div>
        
        <h2>🎯 KPIs Principaux</h2>
        <div class="kpi-grid">
"""
    
    # Add KPI cards
    kpi_mapping = {
        'code_valid_rate': ('Taux de code valide', '%', '> 98%', 'status-good' if latest.get('kpis', {}).get('code_valid_rate', 0) > 98 else 'status-bad'),
        'topic_coverage_rate': ('Couverture des topics', '%', '> 95%', 'status-good' if latest.get('kpis', {}).get('topic_coverage_rate', 0) > 95 else 'status-bad'),
        'avg_response_length': ('Longueur moyenne', 'tokens', '50-200', 'status-good' if 50 <= latest.get('kpis', {}).get('avg_response_length', 0) <= 200 else 'status-bad'),
        'uniqueness_rate': ('Taux d\'unicité', '%', '> 95%', 'status-good' if latest.get('kpis', {}).get('uniqueness_rate', 0) > 95 else 'status-bad'),
        'hallucination_rate': ('Taux d\'hallucination', '%', '< 1%', 'status-good' if latest.get('kpis', {}).get('hallucination_rate', 0) < 1 else 'status-bad'),
        'quality_score': ('Score de qualité', '/100', '> 90%', 'status-good' if latest.get('kpis', {}).get('quality_score', 0) > 90 else 'status-bad'),
    }
    
    for kpi_key, (title, unit, target, status_class) in kpi_mapping.items():
        value = latest.get('kpis', {}).get(kpi_key, 0)
        html += f"""            <div class="kpi-card">
                <h3>{title}</h3>
                <div class="value">{value:.2f} {unit}</div>
                <div class="target">Cible: {target}</div>
                <span class="{status_class}">{"✓ OK" if "good" in status_class else "✗ À améliorer"}</span>
            </div>
"""
    
    html += """        </div>
        
        <h2>📈 Distributions</h2>
        
        <h3>Longueur des réponses</h3>
        <table>
            <tr><th>Catégorie</th><th>Nombre</th><th>Pourcentage</th></tr>
"""
    
    length_dist = latest.get('distributions', {}).get('length', {})
    total = latest.get('total_qa_pairs', 1)
    for category, count in length_dist.items():
        percentage = (count / total) * 100
        html += f"            <tr><td>{category}</td><td>{count}</td><td>{percentage:.1f}%</td></tr>\n"
    
    html += """        </table>
        
        <h3>Niveaux de difficulté</h3>
        <table>
            <tr><th>Niveau</th><th>Nombre</th><th>Pourcentage</th></tr>
"""
    
    level_dist = latest.get('distributions', {}).get('level', {})
    for level, count in level_dist.items():
        percentage = (count / total) * 100
        html += f"            <tr><td>{level}</td><td>{count}</td><td>{percentage:.1f}%</td></tr>\n"
    
    html += """        </table>
        
        <h3>Top 10 Tags</h3>
        <table>
            <tr><th>Tag</th><th>Nombre</th><th>Pourcentage</th></tr>
"""
    
    tag_dist = latest.get('distributions', {}).get('tag', {})
    top_tags = list(tag_dist.items())[:10]
    for tag, count in top_tags:
        percentage = (count / total) * 100
        html += f"            <tr><td>{tag}</td><td>{count}</td><td>{percentage:.1f}%</td></tr>\n"
    
    html += """        </table>
        
        <h3>Répartition par poids</h3>
        <table>
            <tr><th>Poids</th><th>Nombre</th><th>Pourcentage</th></tr>
"""
    
    weight_dist = latest.get('distributions', {}).get('weight', {})
    for weight, count in weight_dist.items():
        percentage = (count / total) * 100
        html += f"            <tr><td>{weight}</td><td>{count}</td><td>{percentage:.1f}%</td></tr>\n"
    
    html += """        </table>
        
        <h3>Répartition par score</h3>
        <table>
            <tr><th>Score</th><th>Nombre</th><th>Pourcentage</th></tr>
"""
    
    score_dist = latest.get('distributions', {}).get('score', {})
    for score_range, count in score_dist.items():
        percentage = (count / total) * 100
        html += f"            <tr><td>{score_range}</td><td>{count}</td><td>{percentage:.1f}%</td></tr>\n"
    
    # Add comparison section if multiple results
    if len(results) > 1:
        html += """        </table>
        
        <h2>🔄 Comparaison des modèles</h2>
        <div class="model-comparison">
"""
        
        for result in results:
            kpis = result.get('kpis', {})
            html += f"""            <div class="comparison-card">
                <h3>{result.get('model_name', 'Unknown')}</h3>
                <p><strong>Date:</strong> {result.get('timestamp', 'N/A')}</p>
                <p><strong>Q&A:</strong> {result.get('total_qa_pairs', 0)}</p>
                <p><strong>Code valide:</strong> {kpis.get('code_valid_rate', 0):.1f}%</p>
                <p><strong>Couverture:</strong> {kpis.get('topic_coverage_rate', 0):.1f}%</p>
                <p><strong>Qualité:</strong> {kpis.get('quality_score', 0):.1f}/100</p>
"""
            if result == latest:
                html += '                <span class="best-badge">Dernier</span>'
            html += """            </div>
"""
        
        html += """        </div>
"""
    
    # Add JavaScript for charts
    html += """    </div>
    
    <script>
        // KPI Chart
        const kpiCtx = document.createElement('canvas');
        document.body.appendChild(kpiCtx);
        
        const kpiData = """
    
    # Prepare chart data
    kpi_names = ['Code valide', 'Couverture', 'Longueur', 'Unicité', 'Hallucination', 'Qualité']
    kpi_values = [
        latest.get('kpis', {}).get('code_valid_rate', 0),
        latest.get('kpis', {}).get('topic_coverage_rate', 0),
        latest.get('kpis', {}).get('avg_response_length', 0),
        latest.get('kpis', {}).get('uniqueness_rate', 0),
        latest.get('kpis', {}).get('hallucination_rate', 0),
        latest.get('kpis', {}).get('quality_score', 0),
    ]
    
    html += f"""[{{
            labels: {json.dumps(kpi_names)},
            datasets: [{{
                label: 'Valeurs KPI',
                data: {kpi_values},
                backgroundColor: [
                    'rgba(75, 192, 192, 0.6)',
                    'rgba(54, 162, 235, 0.6)',
                    'rgba(255, 206, 86, 0.6)',
                    'rgba(153, 102, 255, 0.6)',
                    'rgba(255, 99, 132, 0.6)',
                    'rgba(75, 192, 192, 0.6)'
                ],
                borderColor: [
                    'rgba(75, 192, 192, 1)',
                    'rgba(54, 162, 235, 1)',
                    'rgba(255, 206, 86, 1)',
                    'rgba(153, 102, 255, 1)',
                    'rgba(255, 99, 132, 1)',
                    'rgba(75, 192, 192, 1)'
                ],
                borderWidth: 1
            }}]
        }}];
        
        new Chart(kpiCtx, {{
            type: 'bar',
            data: kpiData,
            options: {{
                scales: {{
                    y: {{
                        beginAtZero: true
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>"""
    
    # Write HTML file
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html)
    
    return str(filepath)


def generate_comparison_report(results: list[dict], output_path: Optional[str] = None) -> str:
    """Generate comparison report for multiple models.
    
    Args:
        results: List of benchmark result dictionaries
        output_path: Output file path
        
    Returns:
        Path to generated HTML file
    """
    if len(results) < 2:
        raise ValueError("Need at least 2 results for comparison")
    
    output_dir = Path(output_path) if output_path else Path(__file__).parent.parent / "reports"
    output_dir.mkdir(exist_ok=True, parents=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"comparison_{timestamp}.html"
    filepath = output_dir / filename
    
    # Get all model names
    model_names = [r.get('model_name', 'Unknown') for r in results]
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Comparaison Modèles - Laravel LLM</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }}
        .comparison-table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        .comparison-table th, .comparison-table td {{ padding: 12px; text-align: left; border: 1px solid #ddd; }}
        .comparison-table th {{ background: #6366f1; color: white; }}
        .best {{ background: #d4edda; font-weight: bold; }}
        .chart-container {{ position: relative; height: 400px; margin: 30px 0; }}
    </style>
</head>
<body>
    <h1>🔄 Comparaison des Modèles LLM</h1>
    <p><strong>Modèles:</strong> {', '.join(model_names)}</p>
    
    <h2>📊 Tableau Comparatif</h2>
    <table class="comparison-table">
        <tr>
            <th>KPI</th>
            {' '.join(f'<th>{name}</th>' for name in model_names)}
            <th>Meilleur</th>
        </tr>
"""
    
    kpis = ['code_valid_rate', 'topic_coverage_rate', 'avg_response_length', 
            'uniqueness_rate', 'hallucination_rate', 'quality_score']
    kpi_display = {
        'code_valid_rate': 'Taux code valide (%)',
        'topic_coverage_rate': 'Couverture topics (%)',
        'avg_response_length': 'Longueur moyenne (tokens)',
        'uniqueness_rate': 'Unicité (%)',
        'hallucination_rate': 'Hallucination (%)',
        'quality_score': 'Score qualité (/100)',
    }
    
    # Find best for each KPI
    best_models = {}
    for kpi in kpis:
        values = {}
        for i, result in enumerate(results):
            values[model_names[i]] = result.get('kpis', {}).get(kpi, 0)
        best_models[kpi] = max(values, key=values.get)
    
    for kpi in kpis:
        html += f"<tr><td>{kpi_display.get(kpi, kpi)}</td>"
        for result in results:
            value = result.get('kpis', {}).get(kpi, 0)
            html += f"<td>{value:.2f}</td>"
        html += f"<td class='best'>{best_models[kpi]}</td></tr>\n"
    
    html += """    </table>
    
    <h2>📈 Graphiques</h2>
    <div class="chart-container">
        <canvas id="comparisonChart"></canvas>
    </div>
    
    <script>
        const ctx = document.getElementById('comparisonChart').getContext('2d');
        const labels = """ + json.dumps(kpi_display.values()) + """
        const datasets = ["""
    
    # Prepare datasets
    colors = ['#6366f1', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6', '#06b6d4']
    datasets_js = []
    for i, (result, model) in enumerate(zip(results, model_names)):
        kpi_values = [result.get('kpis', {}).get(kpi, 0) for kpi in kpis]
        datasets_js.append({
            'label': model,
            'data': kpi_values,
            'backgroundColor': colors[i % len(colors)],
            'borderColor': colors[i % len(colors)],
            'borderWidth': 1
        })
    
    html += json.dumps(datasets_js) + """
        ];
        
        new Chart(ctx, {
            type: 'radar',
            data: {
                labels: labels,
                datasets: datasets
            },
            options: {
                scales: {
                    r: {
                        beginAtZero: true,
                        max: 100
                    }
                }
            }
        });
    </script>
</body>
</html>"""
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html)
    
    return str(filepath)


def generate_json_report(result: dict, output_path: Optional[str] = None) -> str:
    """Save benchmark result as JSON.
    
    Args:
        result: Benchmark result dictionary
        output_path: Output file path
        
    Returns:
        Path to saved JSON file
    """
    output_dir = Path(output_path) if output_path else Path(__file__).parent.parent / "results"
    output_dir.mkdir(exist_ok=True, parents=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"benchmark_{result.get('model_name', 'unknown')}_{timestamp}.json"
    filepath = output_dir / filename
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    return str(filepath)

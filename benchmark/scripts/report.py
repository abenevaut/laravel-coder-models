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
    kpis = latest.get('kpis', {})
    
    output_dir = Path(output_path) if output_path else Path(__file__).parent.parent / "reports"
    output_dir.mkdir(exist_ok=True, parents=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"report_{timestamp}.html"
    filepath = output_dir / filename
    
    # Metric descriptions
    metric_descriptions = {
        'code_valid_rate': {
            'title': 'Taux de code valide',
            'description': 'Pourcentage de paires Q/R contenant du code PHP valide. Un taux élevé indique que le jeu de données est riche en exemples de code, essentiel pour l\'entraînement d\'un modèle spécialisé en développement Laravel.',
            'unit': '%',
            'target': '> 80%',
            'target_min': 80
        },
        'topic_coverage_rate': {
            'title': 'Couverture des topics',
            'description': 'Pourcentage des sujets Laravel définis dans la métadonnée qui sont couverts par les paires Q/R. Une couverture élevée garantit que le modèle sera formé sur tous les aspects du framework.',
            'unit': '%',
            'target': '> 95%',
            'target_min': 95
        },
        'avg_response_length': {
            'title': 'Longueur moyenne des réponses',
            'description': 'Nombre moyen de tokens par réponse. Des réponses trop courtes peuvent manquer de contexte, tandis que des réponses trop longues peuvent contenir du bruit.',
            'unit': 'tokens',
            'target': '50-200',
            'target_min': 50,
            'target_max': 200
        },
        'uniqueness_rate': {
            'title': 'Taux d\'unicité',
            'description': 'Pourcentage de questions uniques. Un taux élevé indique une bonne diversité dans le jeu de données, évitant la redondance.',
            'unit': '%',
            'target': '> 95%',
            'target_min': 95
        },
        'hallucination_rate': {
            'title': 'Taux d\'hallucination',
            'description': 'Pourcentage de réponses contenant des informations potentiellemenet incorrectes ou inexistantes. Un taux bas indique une bonne qualité des données.',
            'unit': '%',
            'target': '< 1%',
            'target_max': 1
        },
        'quality_score': {
            'title': 'Score de qualité',
            'description': 'Score composite basé sur les autres métriques (code valide 30%, longueur 20%, unicité 20%, base 30%). Reflète la qualité globale du jeu de données.',
            'unit': '/100',
            'target': '> 60%',
            'target_min': 60
        }
    }
    
    def get_status_class(kpi_key, value):
        """Get CSS class based on KPI value and target."""
        metric = metric_descriptions.get(kpi_key, {})
        target_min = metric.get('target_min')
        target_max = metric.get('target_max')
        
        if target_min is not None and value >= target_min:
            return 'status-good'
        elif target_max is not None and value <= target_max:
            return 'status-good'
        elif target_min is not None and target_max is not None and target_min <= value <= target_max:
            return 'status-good'
        else:
            return 'status-bad'
    
    def get_status_text(kpi_key, value):
        """Get status text based on KPI value and target."""
        metric = metric_descriptions.get(kpi_key, {})
        target_min = metric.get('target_min')
        target_max = metric.get('target_max')
        
        if target_min is not None and value >= target_min:
            return '✓ OK'
        elif target_max is not None and value <= target_max:
            return '✓ OK'
        elif target_min is not None and target_max is not None and target_min <= value <= target_max:
            return '✓ OK'
        else:
            return '✗ À améliorer'
    
    # Generate HTML content
    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Benchmark Laravel LLM - {latest.get('model_name', 'N/A')}</title>
    <style>
        :root {{
            --primary-color: #2563eb;
            --success-color: #10b981;
            --warning-color: #f59e0b;
            --danger-color: #ef4444;
            --bg-color: #f8fafc;
            --card-bg: #ffffff;
            --text-primary: #1e293b;
            --text-secondary: #64748b;
            --border-color: #e2e8f0;
        }}
        
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-primary);
            line-height: 1.6;
            padding: 20px;
        }}
        
        .report-container {{
            max-width: 1000px;
            margin: 0 auto;
        }}
        
        .header {{
            background: var(--card-bg);
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            margin-bottom: 24px;
            border: 1px solid var(--border-color);
        }}
        
        .header h1 {{
            color: var(--text-primary);
            font-size: 28px;
            margin-bottom: 10px;
            font-weight: 700;
        }}
        
        .header-meta {{
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
            color: var(--text-secondary);
            font-size: 14px;
            margin-top: 15px;
        }}
        
        .header-meta span {{
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        
        .section {{
            background: var(--card-bg);
            border-radius: 12px;
            padding: 28px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            margin-bottom: 20px;
            border: 1px solid var(--border-color);
        }}
        
        .section h2 {{
            font-size: 20px;
            color: var(--text-primary);
            margin-bottom: 20px;
            padding-bottom: 12px;
            border-bottom: 2px solid var(--primary-color);
            font-weight: 600;
        }}
        
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }}
        
        .kpi-card {{
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 20px;
            transition: box-shadow 0.2s;
        }}
        
        .kpi-card:hover {{
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }}
        
        .kpi-card h3 {{
            font-size: 14px;
            color: var(--text-secondary);
            margin-bottom: 8px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        .kpi-card .value {{
            font-size: 28px;
            font-weight: 700;
            color: var(--primary-color);
            margin-bottom: 8px;
        }}
        
        .kpi-card .description {{
            font-size: 13px;
            color: var(--text-secondary);
            line-height: 1.5;
            margin-bottom: 12px;
        }}
        
        .kpi-card .meta {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 12px;
        }}
        
        .kpi-card .target {{
            color: var(--text-secondary);
        }}
        
        .status {{
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
        }}
        
        .status-good {{
            background: #dcfce7;
            color: #166534;
        }}
        
        .status-bad {{
            background: #fee2e2;
            color: #991b1b;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 16px;
            font-size: 14px;
        }}
        
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid var(--border-color);
        }}
        
        th {{
            background: var(--bg-color);
            font-weight: 600;
            color: var(--text-secondary);
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        tr:last-child td {{
            border-bottom: none;
        }}
        
        tr:hover {{
            background: var(--bg-color);
        }}
        
        .distribution-section {{
            margin-top: 20px;
        }}
        
        .distribution-section h3 {{
            font-size: 16px;
            color: var(--text-primary);
            margin-bottom: 12px;
            font-weight: 600;
        }}
        
        .total-row {{
            font-weight: 600;
        }}
        
        .total-row td {{
            background: var(--bg-color);
        }}
        
        .comparison-section {{
            margin-top: 24px;
        }}
        
        .comparison-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 16px;
        }}
        
        .comparison-card {{
            background: var(--bg-color);
            border-radius: 8px;
            padding: 16px;
            border: 1px solid var(--border-color);
        }}
        
        .comparison-card h4 {{
            font-size: 14px;
            color: var(--text-primary);
            margin-bottom: 12px;
            font-weight: 600;
        }}
        
        .comparison-card .kpi-row {{
            display: flex;
            justify-content: space-between;
            padding: 6px 0;
            font-size: 13px;
            border-bottom: 1px solid var(--border-color);
        }}
        
        .comparison-card .kpi-row:last-child {{
            border-bottom: none;
        }}
        
        .best-badge {{
            background: var(--primary-color);
            color: white;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
            display: inline-block;
            margin-left: 8px;
        }}
        
        .latest-badge {{
            background: var(--success-color);
            color: white;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
            display: inline-block;
            margin-left: 8px;
        }}
        
        @media (max-width: 768px) {{
            .kpi-grid {{
                grid-template-columns: 1fr;
            }}
            
            .header-meta {{
                flex-direction: column;
                gap: 8px;
            }}
        }}
    </style>
</head>
<body>
    <div class="report-container">
        <div class="header">
            <h1>📊 Benchmark Laravel LLM</h1>
            <p style="color: var(--text-secondary); margin-top: 8px; font-size: 15px;">
                Évaluation des performances du modèle sur les données d'entraînement Laravel
            </p>
            <div class="header-meta">
                <span>🔖 <strong>Modèle:</strong> {latest.get('model_name', 'N/A')}</span>
                <span>📅 <strong>Date:</strong> {latest.get('timestamp', 'N/A')[:10] if latest.get('timestamp') else 'N/A'}</span>
                <span>🏷️ <strong>Version Laravel:</strong> {latest.get('version', 'N/A')}</span>
                <span>📊 <strong>Total Q&A:</strong> {latest.get('total_qa_pairs', 0):,}</span>
                <span>⏱️ <strong>Temps:</strong> {latest.get('execution_time', 0):.2f}s</span>
            </div>
        </div>
        
        <div class="section">
            <h2>🎯 Indicateurs Clés de Performance (KPI)</h2>
            <div class="kpi-grid">
"""
    
    # Add KPI cards with descriptions
    for kpi_key, metric in metric_descriptions.items():
        value = kpis.get(kpi_key, 0)
        status_class = get_status_class(kpi_key, value)
        status_text = get_status_text(kpi_key, value)
        
        html += f"""                <div class="kpi-card">
                    <h3>{metric['title']}</h3>
                    <div class="value">{value:.2f} {metric['unit']}</div>
                    <p class="description">{metric['description']}</p>
                    <div class="meta">
                        <span class="target">Cible: {metric['target']}</span>
                        <span class="status {status_class}">{status_text}</span>
                    </div>
                </div>
"""
    
    html += """            </div>
        </div>
        
        <div class="section">
            <h2>📊 Statistiques de Distribution</h2>
"""
    
    # Length distribution
    length_dist = latest.get('distributions', {}).get('length', {})
    total = latest.get('total_qa_pairs', 1)
    
    if length_dist:
        html += """            <div class="distribution-section">
                <h3>📏 Longueur des réponses</h3>
                <p style="color: var(--text-secondary); font-size: 13px; margin-bottom: 12px;">
                    Répartition des paires Q/R par nombre de tokens dans la réponse.
                </p>
                <table>
                    <tr><th>Catégorie</th><th>Nombre</th><th>Pourcentage</th></tr>
"""
        for category, count in length_dist.items():
            percentage = (count / total) * 100
            html += f"                    <tr><td>{category}</td><td>{count:,}</td><td>{percentage:.1f}%</td></tr>\n"
        html += """                    <tr class="total-row"><td><strong>Total</strong></td><td><strong>""" + f"{total:,}" + """</strong></td><td><strong>100%</strong></td></tr>
                </table>
            </div>
"""
    
    # Level distribution
    level_dist = latest.get('distributions', {}).get('level', {})
    if level_dist:
        html += """            <div class="distribution-section">
                <h3>🎓 Niveaux de difficulté</h3>
                <p style="color: var(--text-secondary); font-size: 13px; margin-bottom: 12px;">
                    Répartition des paires Q/R par niveau de complexité.
                </p>
                <table>
                    <tr><th>Niveau</th><th>Nombre</th><th>Pourcentage</th></tr>
"""
        for level, count in level_dist.items():
            percentage = (count / total) * 100
            html += f"                    <tr><td>{level}</td><td>{count:,}</td><td>{percentage:.1f}%</td></tr>\n"
        html += """                    <tr class="total-row"><td><strong>Total</strong></td><td><strong>""" + f"{total:,}" + """</strong></td><td><strong>100%</strong></td></tr>
                </table>
            </div>
"""
    
    # Tag distribution (top 15)
    tag_dist = latest.get('distributions', {}).get('tag', {})
    if tag_dist:
        top_tags = list(tag_dist.items())[:15]
        html += """            <div class="distribution-section">
                <h3>🏷️ Top 15 des tags</h3>
                <p style="color: var(--text-secondary); font-size: 13px; margin-bottom: 12px;">
                    Tags les plus fréquents dans les qualifications des paires Q/R.
                </p>
                <table>
                    <tr><th>Tag</th><th>Nombre</th><th>Pourcentage</th></tr>
"""
        for tag, count in top_tags:
            percentage = (count / total) * 100
            html += f"                    <tr><td>{tag}</td><td>{count:,}</td><td>{percentage:.1f}%</td></tr>\n"
        html += """                </table>
            </div>
"""
    
    # Weight distribution
    weight_dist = latest.get('distributions', {}).get('weight', {})
    if weight_dist:
        html += """            <div class="distribution-section">
                <h3>⚖️ Répartition par poids</h3>
                <p style="color: var(--text-secondary); font-size: 13px; margin-bottom: 12px;">
                    Poids attribués aux paires Q/R pour le fine-tuning (basé sur le niveau de difficulté).
                </p>
                <table>
                    <tr><th>Poids</th><th>Nombre</th><th>Pourcentage</th></tr>
"""
        for weight, count in sorted(weight_dist.items(), key=lambda x: float(x[0])):
            percentage = (count / total) * 100
            html += f"                    <tr><td>{weight}</td><td>{count:,}</td><td>{percentage:.1f}%</td></tr>\n"
        html += """                </table>
            </div>
"""
    
    # Score distribution
    score_dist = latest.get('distributions', {}).get('score', {})
    if score_dist:
        html += """            <div class="distribution-section">
                <h3>⭐ Répartition par score composite</h3>
                <p style="color: var(--text-secondary); font-size: 13px; margin-bottom: 12px;">
                    Scores composites calculés pour chaque paire Q/R (poids × bonus code × bonus utilité).
                </p>
                <table>
                    <tr><th>Plage de score</th><th>Nombre</th><th>Pourcentage</th></tr>
"""
        for score_range, count in score_dist.items():
            percentage = (count / total) * 100
            html += f"                    <tr><td>{score_range}</td><td>{count:,}</td><td>{percentage:.1f}%</td></tr>\n"
        html += """                </table>
            </div>
"""
    
    # Add comparison section if multiple results
    if len(results) > 1:
        html += """        </div>
        
        <div class="section">
            <h2>🔄 Comparaison Historique</h2>
            <p style="color: var(--text-secondary); font-size: 14px; margin-bottom: 20px;">
                Comparaison avec les résultats des exécutions précédentes du benchmark.
            </p>
            <div class="comparison-grid">
"""
        
        # Sort results by timestamp for comparison
        for result in results:
            result_kpis = result.get('kpis', {})
            is_latest = (result == latest)
            
            html += f"""                <div class="comparison-card">
                    <h4>{result.get('model_name', 'Unknown')}
                        <span class="{'latest-badge' if is_latest else ''}">{'Dernier' if is_latest else ''}</span>
                    </h4>
                    <p style="color: var(--text-secondary); font-size: 12px; margin-bottom: 12px;">
                        {result.get('timestamp', 'N/A')[:10] if result.get('timestamp') else 'N/A'}
                    </p>
"""
            
            # Show key metrics
            metrics_to_show = [
                ('code_valid_rate', 'Code valide', '%'),
                ('topic_coverage_rate', 'Couverture', '%'),
                ('avg_response_length', 'Longueur avg', 't'),
                ('uniqueness_rate', 'Unicité', '%'),
                ('quality_score', 'Qualité', '/100')
            ]
            
            for kpi_key, short_name, unit in metrics_to_show:
                value = result_kpis.get(kpi_key, 0)
                html += f'                    <div class="kpi-row"><span>{short_name}:</span><strong>{value:.1f}{unit}</strong></div>\n'
            
            html += """                </div>
"""
        
        html += """            </div>
        </div>
"""
    
    else:
        html += """        </div>
"""
    
    html += """    </div>
    
    <div style="text-align: center; margin-top: 30px; color: var(--text-secondary); font-size: 12px;">
        Généré par Laravel LLM Benchmark | """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """
    </div>
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
    
    # KPI configuration
    kpis = ['code_valid_rate', 'topic_coverage_rate', 'avg_response_length', 
            'uniqueness_rate', 'hallucination_rate', 'quality_score']
    kpi_display = {
        'code_valid_rate': 'Taux code valide',
        'topic_coverage_rate': 'Couverture topics',
        'avg_response_length': 'Longueur moyenne',
        'uniqueness_rate': 'Taux unicité',
        'hallucination_rate': 'Taux hallucination',
        'quality_score': 'Score qualité',
    }
    kpi_descriptions = {
        'code_valid_rate': 'Pourcentage de Q/R avec code PHP valide',
        'topic_coverage_rate': 'Pourcentage des topics Laravel couverts',
        'avg_response_length': 'Nombre moyen de tokens par réponse',
        'uniqueness_rate': 'Pourcentage de questions uniques',
        'hallucination_rate': 'Pourcentage de réponses avec erreurs factuelles',
        'quality_score': 'Score composite (0-100) basé sur tous les KPI',
    }
    kpi_units = {
        'code_valid_rate': '%',
        'topic_coverage_rate': '%',
        'avg_response_length': 'tokens',
        'uniqueness_rate': '%',
        'hallucination_rate': '%',
        'quality_score': '/100',
    }
    
    # Find best for each KPI
    best_models = {}
    for kpi in kpis:
        values = {}
        for i, result in enumerate(results):
            values[model_names[i]] = result.get('kpis', {}).get(kpi, 0)
        best_models[kpi] = max(values, key=values.get)
    
    # Build KPI table rows
    kpi_table_rows = ''
    for kpi in kpis:
        display_name = kpi_display.get(kpi, kpi)
        description = kpi_descriptions.get(kpi, '')
        unit = kpi_units.get(kpi, '')
        
        kpi_table_rows += f'<tr><td><strong>{display_name}</strong></td><td style="font-size: 13px; color: var(--text-secondary);">{description}</td>'
        
        for result in results:
            value = result.get('kpis', {}).get(kpi, 0)
            if kpi == 'hallucination_rate':
                score_class = 'score-good' if value < 1 else ('score-warning' if value < 5 else 'score-bad')
            else:
                score_class = 'score-good' if value > 90 else ('score-warning' if value > 70 else 'score-bad')
            kpi_table_rows += f'<td class="{score_class}">{value:.1f}{unit}</td>'
        
        kpi_table_rows += f'<td class="best">{best_models[kpi]}</td></tr>\n'
    
    # Build model summary rows
    model_rows = ''
    for result in results:
        kpis_data = result.get('kpis', {})
        quality = kpis_data.get('quality_score', 0)
        is_latest = (result == results[0])
        
        if quality >= 90:
            status_html = '<span style="color: var(--success-color); font-weight: 600;">✓ Excellente qualité</span>'
        elif quality >= 70:
            status_html = '<span style="color: #f59e0b; font-weight: 600;">⚠ Bonne qualité</span>'
        else:
            status_html = '<span style="color: #ef4444; font-weight: 600;">✗ Qualité à améliorer</span>'
        
        timestamp = result.get('timestamp', 'N/A')
        date_str = timestamp[:10] if timestamp else 'N/A'
        model_name = result.get('model_name', 'Unknown')
        total_qa = result.get('total_qa_pairs', 0)
        version = result.get('version', 'N/A')
        latest_badge = '🏆 Dernier' if is_latest else ''
        
        model_rows += f'<tr>\n'
        model_rows += f'    <td><strong>{model_name}</strong> {latest_badge}</td>\n'
        model_rows += f'    <td>{date_str}</td>\n'
        model_rows += f'    <td>{total_qa:,}</td>\n'
        model_rows += f'    <td>{version}</td>\n'
        model_rows += f'    <td><strong>{quality:.1f}/100</strong></td>\n'
        model_rows += f'    <td>{status_html}</td>\n'
        model_rows += f'</tr>\n'
    
    # Generate HTML
    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Comparaison Modèles - Laravel LLM</title>
    <style>
        :root {{
            --primary-color: #2563eb;
            --success-color: #10b981;
            --bg-color: #f8fafc;
            --card-bg: #ffffff;
            --text-primary: #1e293b;
            --text-secondary: #64748b;
            --border-color: #e2e8f0;
        }}
        
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-primary);
            line-height: 1.6;
            padding: 20px;
        }}
        
        .report-container {{ max-width: 1000px; margin: 0 auto; }}
        
        .header {{
            background: var(--card-bg);
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            margin-bottom: 24px;
            border: 1px solid var(--border-color);
        }}
        
        .header h1 {{ font-size: 28px; margin-bottom: 10px; font-weight: 700; }}
        .header p {{ color: var(--text-secondary); margin-top: 8px; font-size: 15px; }}
        
        .section {{
            background: var(--card-bg);
            border-radius: 12px;
            padding: 28px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            margin-bottom: 20px;
            border: 1px solid var(--border-color);
        }}
        
        .section h2 {{ font-size: 20px; margin-bottom: 20px; padding-bottom: 12px; border-bottom: 2px solid var(--primary-color); font-weight: 600; }}
        
        .comparison-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 16px 0;
            font-size: 14px;
        }}
        
        .comparison-table th, .comparison-table td {{ padding: 12px; text-align: left; border-bottom: 1px solid var(--border-color); }}
        
        .comparison-table th {{
            background: var(--bg-color);
            font-weight: 600;
            color: var(--text-secondary);
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        .comparison-table tr:last-child td {{ border-bottom: none; }}
        .comparison-table tr:hover {{ background: var(--bg-color); }}
        
        .best {{ background: #dcfce7; color: #166534; font-weight: 600; }}
        
        .score-good {{ color: var(--success-color); font-weight: 600; }}
        .score-warning {{ color: #f59e0b; font-weight: 600; }}
        .score-bad {{ color: #ef4444; font-weight: 600; }}
        
        @media (max-width: 768px) {{
            .comparison-table {{ font-size: 12px; }}
            .comparison-table th, .comparison-table td {{ padding: 8px; }}
        }}
    </style>
</head>
<body>
    <div class="report-container">
        <div class="header">
            <h1>🔄 Comparaison des Modèles LLM</h1>
            <p>Comparaison des performances entre différents modèles ou versions</p>
        </div>
        
        <div class="section">
            <h2>📊 Tableau Comparatif des KPI</h2>
            <p style="color: var(--text-secondary); font-size: 14px; margin-bottom: 16px;">
                Comparaison détaillée des indicateurs de performance entre les modèles.
            </p>
            <table class="comparison-table">
                <thead>
                    <tr>
                        <th>Indicateur</th>
                        <th>Description</th>
                        {' '.join(f'<th>{name}</th>' for name in model_names)}
                        <th>Meilleur</th>
                    </tr>
                </thead>
                <tbody>
                    {kpi_table_rows}
                </tbody>
            </table>
        </div>
        
        <div class="section">
            <h2>📋 Résumé par Modèle</h2>
            <p style="color: var(--text-secondary); font-size: 14px; margin-bottom: 16px;">
                Vue d'ensemble des métriques pour chaque modèle.
            </p>
            <table class="comparison-table">
                <thead>
                    <tr>
                        <th>Modèle</th>
                        <th>Date</th>
                        <th>Total Q&A</th>
                        <th>Version Laravel</th>
                        <th>Score Qualité</th>
                        <th>Statut</th>
                    </tr>
                </thead>
                <tbody>
                    {model_rows}
                </tbody>
            </table>
        </div>
        
        <div style="text-align: center; margin-top: 30px; color: var(--text-secondary); font-size: 12px;">
            Généré par Laravel LLM Benchmark | {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        </div>
    </div>
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

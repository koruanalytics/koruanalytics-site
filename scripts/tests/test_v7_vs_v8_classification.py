# scripts/tests/test_v7_vs_v8_classification.py
# Last updated: 2026-01-17
# Description: Compare LLM classification between v1 (v7) and v2 (v8 ACLED) prompts

import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List
import duckdb
from loguru import logger
import json

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import both prompt versions
from src.llm_providers import prompts as prompts_v2
from src.llm_providers.factory import get_llm_provider


# Old prompt (v1) for comparison
ENRICHMENT_PROMPT_V1 = """Eres un analista de seguridad especializado en Perú. Analiza esta noticia y extrae información estructurada.

CATEGORÍAS DE EVENTOS (usa exactamente estos valores):
- violencia_armada: Enfrentamientos, tiroteos, balaceras, ataques con armas
- crimen_violento: Asesinatos, homicidios, sicariato, agresiones graves
- violencia_sexual: Violaciones, abuso sexual, acoso sexual grave
- secuestro: Secuestros, desapariciones forzadas, raptos
- feminicidio: Asesinato de mujeres por razón de género
- extorsion: Extorsión, cobro de cupos, amenazas por dinero
- accidente_grave: Accidentes de tránsito/laborales con víctimas
- desastre_natural: Sismos, inundaciones, huaycos, deslizamientos
- protesta: Marchas, manifestaciones, paros, huelgas
- disturbio: Disturbios, vandalismo, saqueos
- terrorismo: Ataques terroristas, Sendero Luminoso, VRAEM
- crimen_organizado: Narcotráfico, bandas criminales organizadas
- violencia_politica: Ataques/amenazas a candidatos, violencia electoral
- operativo_seguridad: Detenciones, capturas, incautaciones importantes
- no_relevante: Deportes, farándula, economía, política sin violencia

CRITERIOS NO RELEVANTE:
- Noticias de entretenimiento, farándula, celebridades
- Deportes (excepto violencia en estadios)
- Economía/negocios general (sin crimen)
- Política internacional sin impacto directo en Perú
- Horóscopo, tecnología general, ciencia

DEPARTAMENTOS DE PERÚ:
Amazonas, Áncash, Apurímac, Arequipa, Ayacucho, Cajamarca, Callao, Cusco,
Huancavelica, Huánuco, Ica, Junín, La Libertad, Lambayeque, Lima, Loreto,
Madre de Dios, Moquegua, Pasco, Piura, Puno, San Martín, Tacna, Tumbes, Ucayali

NOTICIA:
Título: {title}
Cuerpo: {body}
Fuente: {source}

Responde ÚNICAMENTE con JSON válido (sin markdown):
{{
    "es_relevante": true/false,
    "es_internacional": true/false,
    "es_resumen": true/false,
    "tipo_evento": "categoria_exacta",
    "subtipo": "descripción breve específica",
    "muertos": número o null,
    "heridos": número o null,
    "departamento": "nombre exacto" o null,
    "provincia": "nombre" o null,
    "distrito": "nombre" o null,
    "ubicacion_especifica": "lugar/dirección" o null,
    "pais_evento": "Perú" o nombre del país donde ocurrió,
    "actores": ["persona1", "persona2"] o [],
    "organizaciones": ["org1", "org2"] o [],
    "resumen_es": "resumen de 3-4 oraciones en español",
    "resumen_en": "summary in 3-4 sentences in English",
    "sentiment": "POS" o "NEG" o "NEU",
    "confianza": 0.0-1.0
}}"""


class ClassificationComparator:
    """Compare LLM classification between v1 and v2 prompts."""
    
    def __init__(self, db_path: str = "data/database.duckdb", limit: int = 50):
        """
        Initialize comparator.
        
        Args:
            db_path: Path to DuckDB database
            limit: Number of articles to test
        """
        self.db_path = Path(db_path)
        self.con = duckdb.connect(str(self.db_path))
        self.limit = limit
        self.llm = get_llm_provider()
    
    
    def get_test_articles(self) -> List[Dict]:
        """Get sample articles from bronze for testing."""
        logger.info(f"Fetching {self.limit} recent articles from bronze_news...")
        
        result = self.con.execute(f"""
            SELECT 
                uri, titulo, cuerpo, fuente, 
                fecha_publicacion, categoria_ingestion
            FROM bronze_news
            WHERE LENGTH(cuerpo) > 200  -- Ensure substantial content
            ORDER BY fecha_publicacion DESC
            LIMIT {self.limit}
        """).fetchall()
        
        articles = []
        for row in result:
            articles.append({
                'uri': row[0],
                'title': row[1],
                'body': row[2],
                'source': row[3],
                'date': row[4],
                'category': row[5]
            })
        
        logger.info(f"✅ Retrieved {len(articles)} articles")
        return articles
    
    
    def classify_with_prompt(self, article: Dict, prompt_template: str, version: str) -> Dict:
        """
        Classify article using specified prompt.
        
        Args:
            article: Article dictionary
            prompt_template: Prompt template to use
            version: "v1" or "v2" for logging
            
        Returns:
            Classification result dictionary
        """
        # Format prompt
        prompt = prompt_template.format(
            title=article['title'],
            body=article['body'][:2000],  # Limit body length
            source=article['source']
        )
        
        try:
            # Get LLM response
            response = self.llm.generate(prompt)
            
            # Parse JSON
            result = json.loads(response)
            result['classification_version'] = version
            result['uri'] = article['uri']
            
            return result
            
        except Exception as e:
            logger.error(f"Error classifying with {version}: {e}")
            return {
                'uri': article['uri'],
                'classification_version': version,
                'error': str(e),
                'es_relevante': False
            }
    
    
    def compare_classifications(
        self,
        articles: List[Dict]
    ) -> Dict:
        """
        Classify all articles with both prompts and compare.
        
        Args:
            articles: List of articles to classify
            
        Returns:
            Comparison analysis dictionary
        """
        logger.info(f"\n{'='*70}")
        logger.info("CLASSIFYING ARTICLES")
        logger.info(f"{'='*70}\n")
        
        results_v1 = []
        results_v2 = []
        
        for i, article in enumerate(articles, 1):
            logger.info(f"Processing article {i}/{len(articles)}: {article['uri'][:50]}...")
            
            # Classify with v1
            result_v1 = self.classify_with_prompt(article, ENRICHMENT_PROMPT_V1, "v1")
            results_v1.append(result_v1)
            
            # Classify with v2 (ACLED)
            result_v2 = self.classify_with_prompt(article, prompts_v2.ENRICHMENT_PROMPT, "v2")
            results_v2.append(result_v2)
        
        logger.info(f"\n✅ Classification complete")
        
        # Analyze differences
        return self.analyze_classification_differences(results_v1, results_v2)
    
    
    def analyze_classification_differences(
        self,
        results_v1: List[Dict],
        results_v2: List[Dict]
    ) -> Dict:
        """Analyze differences between v1 and v2 classifications."""
        logger.info(f"\n{'='*70}")
        logger.info("ANALYSIS: v1 vs v2 CLASSIFICATION")
        logger.info(f"{'='*70}\n")
        
        analysis = {
            'total_articles': len(results_v1),
            'v1': {},
            'v2': {},
            'comparison': {}
        }
        
        # Event type distribution
        logger.info("📊 Event Type Distribution:")
        
        for version, results in [('v1', results_v1), ('v2', results_v2)]:
            tipo_counts = {}
            for r in results:
                tipo = r.get('tipo_evento', 'unknown')
                tipo_counts[tipo] = tipo_counts.get(tipo, 0) + 1
            
            analysis[version]['tipo_evento_distribution'] = tipo_counts
            
            logger.info(f"\n  {version.upper()}:")
            for tipo, count in sorted(tipo_counts.items(), key=lambda x: x[1], reverse=True):
                logger.info(f"    {tipo}: {count}")
        
        # Check for corrupcion type (new in v2)
        corrupcion_count_v2 = analysis['v2']['tipo_evento_distribution'].get('corrupcion', 0)
        logger.info(f"\n🆕 New 'corrupcion' type in v2: {corrupcion_count_v2} cases")
        
        # Relevance comparison
        v1_relevant = sum(1 for r in results_v1 if r.get('es_relevante'))
        v2_relevant = sum(1 for r in results_v2 if r.get('es_relevante'))
        
        analysis['v1']['relevant_count'] = v1_relevant
        analysis['v2']['relevant_count'] = v2_relevant
        
        logger.info(f"\n✅ Relevant Articles:")
        logger.info(f"  v1: {v1_relevant}/{len(results_v1)} ({v1_relevant/len(results_v1)*100:.1f}%)")
        logger.info(f"  v2: {v2_relevant}/{len(results_v2)} ({v2_relevant/len(results_v2)*100:.1f}%)")
        
        # Agreement analysis
        agreements = 0
        disagreements = []
        
        for r1, r2 in zip(results_v1, results_v2):
            if r1.get('tipo_evento') == r2.get('tipo_evento'):
                agreements += 1
            else:
                disagreements.append({
                    'uri': r1['uri'],
                    'v1_tipo': r1.get('tipo_evento'),
                    'v2_tipo': r2.get('tipo_evento')
                })
        
        agreement_rate = (agreements / len(results_v1)) * 100
        analysis['comparison']['agreement_rate'] = agreement_rate
        analysis['comparison']['disagreements'] = disagreements
        
        logger.info(f"\n🤝 Classification Agreement:")
        logger.info(f"  Agreement: {agreements}/{len(results_v1)} ({agreement_rate:.1f}%)")
        logger.info(f"  Disagreement: {len(disagreements)}")
        
        if disagreements and len(disagreements) <= 10:
            logger.info(f"\n  Sample Disagreements:")
            for d in disagreements[:5]:
                logger.info(f"    {d['uri'][:50]}:")
                logger.info(f"      v1: {d['v1_tipo']} → v2: {d['v2_tipo']}")
        
        return analysis
    
    
    def generate_recommendation(self, analysis: Dict) -> str:
        """Generate recommendation based on classification analysis."""
        logger.info(f"\n{'='*70}")
        logger.info("RECOMMENDATION")
        logger.info(f"{'='*70}\n")
        
        agreement_rate = analysis['comparison']['agreement_rate']
        corrupcion_count = analysis['v2']['tipo_evento_distribution'].get('corrupcion', 0)
        
        # Decision criteria
        if agreement_rate >= 85:
            if corrupcion_count > 0:
                recommendation = "✅ EXCELLENT - Deploy v2 (ACLED) prompt"
                logger.info(recommendation)
                logger.info("Reasons:")
                logger.info(f"  • High agreement rate: {agreement_rate:.1f}%")
                logger.info(f"  • New 'corrupcion' type working: {corrupcion_count} cases detected")
                logger.info(f"  • ACLED taxonomy applied successfully")
            else:
                recommendation = "✅ GOOD - Deploy v2, but check corruption detection"
                logger.info(recommendation)
                logger.info("Reasons:")
                logger.info(f"  • High agreement rate: {agreement_rate:.1f}%")
                logger.info(f"  ⚠️  No 'corrupcion' cases detected (might be sample)")
        
        elif agreement_rate >= 70:
            recommendation = "⚠️  ACCEPTABLE - Review disagreements before deploying"
            logger.warning(recommendation)
            logger.warning("Reasons:")
            logger.warning(f"  • Moderate agreement: {agreement_rate:.1f}%")
            logger.warning(f"  • Review disagreement patterns")
            logger.warning(f"  • Consider if changes are improvements (ACLED precision)")
        
        else:
            recommendation = "❌ NOT RECOMMENDED - Significant classification changes"
            logger.error(recommendation)
            logger.error("Reasons:")
            logger.error(f"  • Low agreement: {agreement_rate:.1f}%")
            logger.error(f"  • Too many classification changes")
            logger.error(f"  • Review prompt differences and test more")
        
        return recommendation
    
    
    def run_comparison(self) -> Dict:
        """Run full classification comparison."""
        # Get test articles
        articles = self.get_test_articles()
        
        if not articles:
            logger.error("No articles found in database")
            return {}
        
        # Compare classifications
        analysis = self.compare_classifications(articles)
        
        # Generate recommendation
        recommendation = self.generate_recommendation(analysis)
        analysis['recommendation'] = recommendation
        
        return analysis


def main():
    """Main test execution."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Compare v1 vs v2 (ACLED) LLM classification"
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=50,
        help='Number of articles to test (default: 50)'
    )
    parser.add_argument(
        '--db-path',
        type=str,
        default='data/database.duckdb',
        help='Path to DuckDB database'
    )
    
    args = parser.parse_args()
    
    # Configure logger
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )
    
    # Run comparison
    logger.info(f"{'='*70}")
    logger.info("v1 vs v2 LLM CLASSIFICATION COMPARISON")
    logger.info(f"{'='*70}")
    logger.info(f"Articles to test: {args.limit}")
    logger.info(f"Database: {args.db_path}")
    logger.info(f"{'='*70}\n")
    
    comparator = ClassificationComparator(
        db_path=args.db_path,
        limit=args.limit
    )
    
    analysis = comparator.run_comparison()
    
    # Final summary
    if analysis:
        logger.info(f"\n{'='*70}")
        logger.info("TEST COMPLETE")
        logger.info(f"{'='*70}")
        logger.info(f"Recommendation: {analysis['recommendation']}")


if __name__ == "__main__":
    main()

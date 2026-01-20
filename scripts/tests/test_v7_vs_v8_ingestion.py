# scripts/tests/test_v7_vs_v8_ingestion.py
# Last updated: 2026-01-17
# Description: Compare v7 vs v8 ingestion for same date

import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import yaml
import duckdb
from loguru import logger

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.ingestion.newsapi_ai_ingest import MultiQueryIngestor, IngestParams
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()


class VersionComparator:
    """Compare news ingestion between v7 and v8 configurations."""
    
    def __init__(self, test_date: str, db_path: str = "data/database.duckdb"):
        """
        Initialize comparator.
        
        Args:
            test_date: Date to test (YYYY-MM-DD)
            db_path: Path to DuckDB database
        """
        self.test_date = test_date
        self.db_path = Path(db_path)
        self.con = duckdb.connect(str(self.db_path))
        
        # Config paths
        self.v7_config = project_root / "config" / "newsapi_scope_peru_v7.yaml"
        self.v8_config = project_root / "config" / "newsapi_scope_peru_v8.yaml"
        
        # Verify configs exist
        if not self.v7_config.exists():
            raise FileNotFoundError(f"v7 config not found: {self.v7_config}")
        if not self.v8_config.exists():
            raise FileNotFoundError(f"v8 config not found: {self.v8_config}")
        
        # Get API key
        self.api_key = os.getenv('NEWSAPI_AI_KEY')
        if not self.api_key:
            raise ValueError("NEWSAPI_AI_KEY not found in environment variables")
    
    
    def load_config(self, version: str) -> Dict:
        """Load configuration file."""
        config_path = self.v7_config if version == "v7" else self.v8_config
        
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    
    def create_test_tables(self):
        """Create temporary tables for test results."""
        logger.info("Creating test tables...")
        
        # Drop existing test tables
        self.con.execute("DROP TABLE IF EXISTS test_bronze_v7")
        self.con.execute("DROP TABLE IF EXISTS test_bronze_v8")
        
        # Create test tables with explicit schema matching bronze_news
        create_table_sql = """
        CREATE TABLE test_bronze_{version} (
            uri VARCHAR PRIMARY KEY,
            url VARCHAR,
            titulo VARCHAR,
            cuerpo VARCHAR,
            fuente VARCHAR,
            fecha_publicacion TIMESTAMP,
            fecha_ingestion TIMESTAMP,
            categoria_ingestion VARCHAR,
            keywords_ingestion VARCHAR,
            lang VARCHAR,
            imagen_url VARCHAR
        )
        """
        
        self.con.execute(create_table_sql.format(version="v7"))
        self.con.execute(create_table_sql.format(version="v8"))
        
        logger.info("✅ Test tables created")
    
    
    def fetch_articles_for_version(self, version: str) -> List[Dict]:
        """
        Fetch articles using specified config version.
        
        Args:
            version: "v7" or "v8"
            
        Returns:
            List of article dictionaries
        """
        logger.info(f"{'='*70}")
        logger.info(f"FETCHING ARTICLES - {version.upper()}")
        logger.info(f"{'='*70}")
        
        config = self.load_config(version)
        
        # Create ingest params
        params = IngestParams(
            date_str=self.test_date,
            config_file=str(self.v7_config if version == "v7" else self.v8_config),
            max_per_group=80,  # Same as config
            run_id=f"test_{version}_{self.test_date}"
        )
        
        # Initialize ingestor
        ingestor = MultiQueryIngestor(
            api_key=self.api_key,
            config=config,
            params=params
        )
        
        # Fetch articles for test date
        logger.info(f"Fetching for date: {self.test_date}")
        result = ingestor.ingest_single_date(self.test_date)
        
        articles = result.articles if result.articles else []
        
        logger.info(f"✅ {version}: Fetched {len(articles)} articles")
        
        return articles
    
    
    def insert_articles_to_test_table(self, articles: List[Dict], version: str):
        """Insert articles into test table."""
        if not articles:
            logger.warning(f"No articles to insert for {version}")
            return
        
        table_name = f"test_bronze_{version}"
        
        # Prepare insert values
        for article in articles:
            # MultiQueryIngestor returns articles with these fields
            self.con.execute(f"""
                INSERT INTO {table_name} (
                    uri, url, titulo, cuerpo, fuente, fecha_publicacion,
                    fecha_ingestion, categoria_ingestion, keywords_ingestion,
                    lang, imagen_url
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                article.get('uri'),
                article.get('url'),
                article.get('title'),
                article.get('body'),
                article.get('source', {}).get('title') if isinstance(article.get('source'), dict) else article.get('source'),
                article.get('dateTime', article.get('date')),  # Try both field names
                datetime.utcnow().isoformat(),
                article.get('group_id', 'unknown'),  # category from keyword group
                article.get('keywords', ''),
                article.get('lang'),
                article.get('image')
            ])
        
        logger.info(f"✅ {version}: Inserted {len(articles)} articles into {table_name}")
    
    
    def analyze_results(self) -> Dict:
        """Analyze and compare results between v7 and v8."""
        logger.info(f"\n{'='*70}")
        logger.info("ANALYSIS: v7 vs v8")
        logger.info(f"{'='*70}\n")
        
        analysis = {
            'test_date': self.test_date,
            'timestamp': datetime.utcnow().isoformat(),
            'v7': {},
            'v8': {},
            'comparison': {}
        }
        
        # Get counts
        v7_count = self.con.execute("SELECT COUNT(*) FROM test_bronze_v7").fetchone()[0]
        v8_count = self.con.execute("SELECT COUNT(*) FROM test_bronze_v8").fetchone()[0]
        
        analysis['v7']['total_articles'] = v7_count
        analysis['v8']['total_articles'] = v8_count
        
        logger.info(f"📊 Article Counts:")
        logger.info(f"  v7: {v7_count} articles")
        logger.info(f"  v8: {v8_count} articles")
        
        if v7_count > 0:
            diff_pct = ((v8_count - v7_count) / v7_count) * 100
            analysis['comparison']['difference_pct'] = diff_pct
            logger.info(f"  Difference: {diff_pct:+.1f}%")
        else:
            logger.warning("  v7 has 0 articles - cannot calculate percentage")
        
        # Category distribution
        logger.info(f"\n📂 Category Distribution:")
        
        for version in ['v7', 'v8']:
            table = f"test_bronze_{version}"
            try:
                result = self.con.execute(f"""
                    SELECT categoria_ingestion, COUNT(*) as count
                    FROM {table}
                    GROUP BY categoria_ingestion
                    ORDER BY count DESC
                """).fetchall()
                
                logger.info(f"\n  {version.upper()}:")
                category_dist = {}
                if result:
                    for row in result:
                        category = row[0] or 'Unknown'
                        count = row[1]
                        category_dist[category] = count
                        logger.info(f"    {category}: {count}")
                else:
                    logger.info(f"    No categories (0 articles)")
                
                analysis[version]['category_distribution'] = category_dist
            except Exception as e:
                logger.warning(f"  Could not get category distribution for {version}: {e}")
                analysis[version]['category_distribution'] = {}
        
        # Keyword group analysis (v8 only)
        if v8_count > 0:
            logger.info(f"\n🔑 Keyword Group Distribution (v8):")
            try:
                result = self.con.execute("""
                    SELECT keywords_ingestion, COUNT(*) as count
                    FROM test_bronze_v8
                    WHERE keywords_ingestion IS NOT NULL
                    GROUP BY keywords_ingestion
                    ORDER BY count DESC
                """).fetchall()
                
                keyword_dist = {}
                if result:
                    for row in result:
                        keywords = row[0] or 'Unknown'
                        count = row[1]
                        keyword_dist[keywords] = count
                        logger.info(f"    {keywords}: {count}")
                else:
                    logger.info(f"    No keyword data available")
                
                analysis['v8']['keyword_distribution'] = keyword_dist
            except Exception as e:
                logger.warning(f"    Could not get keyword distribution: {e}")
                analysis['v8']['keyword_distribution'] = {}
        
        # Source distribution
        logger.info(f"\n📰 Source Distribution:")
        
        for version in ['v7', 'v8']:
            table = f"test_bronze_{version}"
            try:
                result = self.con.execute(f"""
                    SELECT fuente, COUNT(*) as count
                    FROM {table}
                    WHERE fuente IS NOT NULL
                    GROUP BY fuente
                    ORDER BY count DESC
                """).fetchall()
                
                logger.info(f"\n  {version.upper()}:")
                source_dist = {}
                if result:
                    for row in result:
                        source = row[0] or 'Unknown'
                        count = row[1]
                        source_dist[source] = count
                        logger.info(f"    {source}: {count}")
                else:
                    logger.info(f"    No sources (0 articles)")
                
                analysis[version]['source_distribution'] = source_dist
            except Exception as e:
                logger.warning(f"  Could not get source distribution for {version}: {e}")
                analysis[version]['source_distribution'] = {}
        
        # Check for unique articles (in v8 but not v7)
        logger.info(f"\n🆕 Articles Unique to v8:")
        unique_v8 = self.con.execute("""
            SELECT COUNT(*)
            FROM test_bronze_v8 v8
            WHERE NOT EXISTS (
                SELECT 1 FROM test_bronze_v7 v7
                WHERE v7.uri = v8.uri
            )
        """).fetchone()[0]
        
        analysis['comparison']['unique_to_v8'] = unique_v8
        logger.info(f"  {unique_v8} articles only in v8")
        
        # Check for articles lost (in v7 but not v8)
        logger.info(f"\n⚠️  Articles Lost in v8:")
        lost_in_v8 = self.con.execute("""
            SELECT COUNT(*)
            FROM test_bronze_v7 v7
            WHERE NOT EXISTS (
                SELECT 1 FROM test_bronze_v8 v8
                WHERE v8.uri = v7.uri
            )
        """).fetchone()[0]
        
        analysis['comparison']['lost_in_v8'] = lost_in_v8
        logger.info(f"  {lost_in_v8} articles lost in v8")
        
        # Common articles
        common = self.con.execute("""
            SELECT COUNT(*)
            FROM test_bronze_v7 v7
            INNER JOIN test_bronze_v8 v8 ON v7.uri = v8.uri
        """).fetchone()[0]
        
        analysis['comparison']['common_articles'] = common
        logger.info(f"\n🔵 Common Articles: {common}")
        
        return analysis
    
    
    def generate_recommendation(self, analysis: Dict) -> str:
        """Generate deployment recommendation based on analysis."""
        logger.info(f"\n{'='*70}")
        logger.info("RECOMMENDATION")
        logger.info(f"{'='*70}\n")
        
        v7_count = analysis['v7']['total_articles']
        v8_count = analysis['v8']['total_articles']
        
        if v7_count == 0:
            recommendation = "⚠️  CANNOT RECOMMEND - v7 returned 0 articles. Check API or date."
            logger.warning(recommendation)
            return recommendation
        
        diff_pct = analysis['comparison']['difference_pct']
        unique_v8 = analysis['comparison']['unique_to_v8']
        lost_v8 = analysis['comparison']['lost_in_v8']
        
        # Decision criteria
        if abs(diff_pct) <= 10:
            if lost_v8 <= v7_count * 0.05:  # Less than 5% loss
                recommendation = "✅ RECOMMEND DEPLOYMENT"
                logger.info(recommendation)
                logger.info("Reasons:")
                logger.info(f"  • Article count within ±10% ({diff_pct:+.1f}%)")
                logger.info(f"  • Minimal article loss ({lost_v8} articles, {lost_v8/v7_count*100:.1f}%)")
                logger.info(f"  • v8 adds {unique_v8} new articles")
            else:
                recommendation = "⚠️  REVIEW REQUIRED"
                logger.warning(recommendation)
                logger.warning("Reasons:")
                logger.warning(f"  • Article count acceptable ({diff_pct:+.1f}%)")
                logger.warning(f"  • But significant loss: {lost_v8} articles ({lost_v8/v7_count*100:.1f}%)")
                logger.warning(f"  • Review which articles were lost")
        
        elif diff_pct > 10 and diff_pct <= 25:
            recommendation = "✅ RECOMMEND DEPLOYMENT (with monitoring)"
            logger.info(recommendation)
            logger.info("Reasons:")
            logger.info(f"  • Article count increased {diff_pct:.1f}% (expected from 3 new groups)")
            logger.info(f"  • v8 adds {unique_v8} new articles")
            logger.info(f"  • Monitor first week for quality")
        
        elif diff_pct < -10 and diff_pct >= -20:
            recommendation = "⚠️  INVESTIGATE BEFORE DEPLOYMENT"
            logger.warning(recommendation)
            logger.warning("Reasons:")
            logger.warning(f"  • Article count dropped {diff_pct:.1f}%")
            logger.warning(f"  • Lost {lost_v8} articles")
            logger.warning(f"  • Review keyword changes and API responses")
        
        else:  # >25% increase or >20% decrease
            recommendation = "❌ DO NOT DEPLOY - INVESTIGATE ISSUES"
            logger.error(recommendation)
            logger.error("Reasons:")
            logger.error(f"  • Extreme article count change: {diff_pct:+.1f}%")
            logger.error(f"  • This suggests configuration or API issues")
            logger.error(f"  • Review logs and fix before testing again")
        
        return recommendation
    
    
    def cleanup_test_tables(self):
        """Drop test tables after analysis."""
        logger.info(f"\n🧹 Cleaning up test tables...")
        self.con.execute("DROP TABLE IF EXISTS test_bronze_v7")
        self.con.execute("DROP TABLE IF EXISTS test_bronze_v8")
        logger.info("✅ Cleanup complete")
    
    
    def run_comparison(self, cleanup: bool = True) -> Dict:
        """
        Run full comparison test.
        
        Args:
            cleanup: Whether to cleanup test tables after analysis
            
        Returns:
            Analysis results dictionary
        """
        try:
            # Create test tables
            self.create_test_tables()
            
            # Fetch articles for both versions
            v7_articles = self.fetch_articles_for_version("v7")
            v8_articles = self.fetch_articles_for_version("v8")
            
            # Insert into test tables
            self.insert_articles_to_test_table(v7_articles, "v7")
            self.insert_articles_to_test_table(v8_articles, "v8")
            
            # Analyze results
            analysis = self.analyze_results()
            
            # Generate recommendation
            recommendation = self.generate_recommendation(analysis)
            analysis['recommendation'] = recommendation
            
            return analysis
            
        finally:
            # Cleanup
            if cleanup:
                self.cleanup_test_tables()
            else:
                logger.info("\n⚠️  Test tables preserved for manual inspection")
                logger.info("  - test_bronze_v7")
                logger.info("  - test_bronze_v8")


def main():
    """Main test execution."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Compare v7 vs v8 ingestion")
    parser.add_argument(
        '--date',
        type=str,
        default=(datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'),
        help='Test date (YYYY-MM-DD), default: yesterday'
    )
    parser.add_argument(
        '--keep-tables',
        action='store_true',
        help='Keep test tables after analysis for manual inspection'
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
    logger.info("v7 vs v8 INGESTION COMPARISON TEST")
    logger.info(f"{'='*70}")
    logger.info(f"Test date: {args.date}")
    logger.info(f"Database: {args.db_path}")
    logger.info(f"{'='*70}\n")
    
    comparator = VersionComparator(
        test_date=args.date,
        db_path=args.db_path
    )
    
    analysis = comparator.run_comparison(cleanup=not args.keep_tables)
    
    # Final summary
    logger.info(f"\n{'='*70}")
    logger.info("TEST COMPLETE")
    logger.info(f"{'='*70}")
    logger.info(f"Recommendation: {analysis['recommendation']}")
    logger.info(f"\nNext steps:")
    
    if "RECOMMEND DEPLOYMENT" in analysis['recommendation']:
        logger.info("1. Review detailed results above")
        logger.info("2. Run LLM classification test (Phase 2)")
        logger.info("3. If classification OK, deploy v8")
    elif "REVIEW REQUIRED" in analysis['recommendation']:
        logger.info("1. Review which articles were lost")
        logger.info("2. Check if lost articles are low-value")
        logger.info("3. If acceptable, proceed to Phase 2")
        logger.info("4. Otherwise, adjust v8 keywords")
    else:
        logger.info("1. Review logs above for issues")
        logger.info("2. Check API responses and errors")
        logger.info("3. Adjust v8 configuration")
        logger.info("4. Re-run this test")


if __name__ == "__main__":
    main()

"""
src/ingestion/newsapi_ai_ingest.py - Multi-query ingestion strategy

IMPROVEMENTS over v1:
- Runs one query PER GROUP to maximize coverage
- Uses keywords as fallback when concepts unavailable
- Deduplicates articles across queries
- Respects priority levels for quota management
- Better error handling and logging

Reference: https://github.com/EventRegistry/event-registry-python
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone, date
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import yaml
from dotenv import load_dotenv
from loguru import logger

from eventregistry import (
    EventRegistry,
    QueryArticlesIter,
    QueryItems,
    ReturnInfo,
    ArticleInfoFlags,
)


# =============================================================================
# UTILITIES
# =============================================================================

def utc_now_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")


def utc_now_iso_z() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def load_scope_yaml(scope_path: Path) -> Dict[str, Any]:
    data = yaml.safe_load(scope_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("El scope YAML no es un dict válido.")
    return data


def get_api_key() -> str:
    load_dotenv()
    key = (
        os.getenv("NEWSAPI_KEY")
        or os.getenv("NEWSAPI_AI_KEY")
        or os.getenv("EVENTREGISTRY_API_KEY")
    )
    if not key:
        raise RuntimeError("Falta NEWSAPI_KEY en tu .env")
    return key


def safe_article_info_flags(body_len: int = 8000) -> ArticleInfoFlags:
    """Best-effort para pedir más detalle."""
    try:
        return ArticleInfoFlags(
            concepts=True,
            categories=True,
            location=True,
            image=True,
            links=True,
            videos=True,
            duplicateList=True,
            originalArticle=True,
            extractedDates=True,
            bodyLen=body_len,
        )
    except TypeError:
        pass
    try:
        return ArticleInfoFlags(
            concepts=True,
            categories=True,
            location=True,
            image=True,
            bodyLen=body_len,
        )
    except TypeError:
        pass
    return ArticleInfoFlags()


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class GroupQueryResult:
    """Result of querying a single concept group."""
    group_id: str
    articles_found: int
    articles_new: int  # After deduplication
    concepts_used: List[str]
    keywords_used: List[str]
    error: Optional[str] = None


@dataclass
class IngestParams:
    """Parameters for ingestion run."""
    scope_yaml: Path
    out_dir: Path
    date_start: date
    date_end: date
    max_per_group: int = 50
    max_total: int = 200
    sort_by: str = "date"
    allow_archive: bool = True
    langs: Optional[List[str]] = None
    priority_filter: Optional[List[int]] = None  # e.g., [1, 2] for priority 1 and 2 only


@dataclass
class IngestResult:
    """Result of complete ingestion run."""
    run_id: str
    output_path: Path
    total_articles: int
    unique_articles: int
    groups_queried: int
    group_results: List[GroupQueryResult]
    errors: List[str] = field(default_factory=list)


# =============================================================================
# MULTI-QUERY INGESTION
# =============================================================================

class MultiQueryIngestor:
    """
    Ingestion strategy that queries each concept group separately
    to maximize coverage.
    """
    
    def __init__(self, params: IngestParams):
        self.params = params
        self.api_key = get_api_key()
        self.scope = load_scope_yaml(params.scope_yaml)
        self.er = EventRegistry(
            apiKey=self.api_key,
            allowUseOfArchive=params.allow_archive
        )
        self.ret_info = ReturnInfo(articleInfo=safe_article_info_flags())
        
        # For deduplication
        self.seen_uris: Set[str] = set()
        
        # Results
        self.all_articles: List[Dict[str, Any]] = []
        self.group_results: List[GroupQueryResult] = []
        self.errors: List[str] = []
    
    def _get_location_uri(self) -> str:
        return self.scope["scope"]["location_uri"]
    
    def _get_langs(self) -> List[str]:
        if self.params.langs:
            return self.params.langs
        return self.scope.get("langs", ["spa", "eng"])
    
    def _get_groups(self) -> List[Dict[str, Any]]:
        """Get concept groups filtered by priority if specified."""
        groups = self.scope["scope"]["concept_groups"]
        
        if self.params.priority_filter:
            groups = [
                g for g in groups
                if g.get("priority", 2) in self.params.priority_filter
            ]
        
        # Sort by priority
        return sorted(groups, key=lambda g: g.get("priority", 99))
    
    def _query_group(self, group: Dict[str, Any]) -> GroupQueryResult:
        """
        Query a single concept group.
        
        Strategy:
        1. Try with concept URIs first (more precise)
        2. If no concepts, use keywords
        3. Combine location + concepts/keywords + date range
        """
        group_id = group["group_id"]
        concepts = group.get("concept_uris", [])
        keywords_spa = group.get("keywords_spa", [])
        keywords_eng = group.get("keywords_eng", [])
        all_keywords = keywords_spa + keywords_eng
        
        logger.info(f"[{group_id}] Querying: {len(concepts)} concepts, {len(all_keywords)} keywords")
        
        # Build query
        location_uri = self._get_location_uri()
        langs = self._get_langs()
        
        try:
            # Prefer concepts if available
            if concepts:
                q = QueryArticlesIter(
                    locationUri=location_uri,
                    conceptUri=QueryItems.OR(concepts),
                    lang=QueryItems.OR(langs),
                    dateStart=self.params.date_start.isoformat(),
                    dateEnd=self.params.date_end.isoformat(),
                )
                concepts_used = concepts
                keywords_used = []
            elif all_keywords:
                # Fallback to keywords
                q = QueryArticlesIter(
                    locationUri=location_uri,
                    keywords=QueryItems.OR(all_keywords),
                    lang=QueryItems.OR(langs),
                    dateStart=self.params.date_start.isoformat(),
                    dateEnd=self.params.date_end.isoformat(),
                )
                concepts_used = []
                keywords_used = all_keywords
            else:
                logger.warning(f"[{group_id}] No concepts or keywords defined, skipping")
                return GroupQueryResult(
                    group_id=group_id,
                    articles_found=0,
                    articles_new=0,
                    concepts_used=[],
                    keywords_used=[],
                    error="No concepts or keywords defined"
                )
            
            # Execute query
            articles_found = 0
            articles_new = 0
            
            for art in q.execQuery(
                self.er,
                sortBy=self.params.sort_by,
                returnInfo=self.ret_info,
                maxItems=self.params.max_per_group,
            ):
                articles_found += 1
                
                # Deduplicate by URI
                uri = art.get("uri", "")
                if uri and uri not in self.seen_uris:
                    self.seen_uris.add(uri)
                    
                    # Add group info to article
                    art["_source_group"] = group_id
                    self.all_articles.append(art)
                    articles_new += 1
                
                # Check total limit
                if len(self.all_articles) >= self.params.max_total:
                    logger.info(f"[{group_id}] Reached max_total ({self.params.max_total}), stopping")
                    break
            
            logger.success(
                f"[{group_id}] Found {articles_found} articles, "
                f"{articles_new} new (after dedup)"
            )
            
            return GroupQueryResult(
                group_id=group_id,
                articles_found=articles_found,
                articles_new=articles_new,
                concepts_used=concepts_used,
                keywords_used=keywords_used,
            )
            
        except Exception as ex:
            error_msg = f"[{group_id}] Query failed: {ex}"
            logger.error(error_msg)
            self.errors.append(error_msg)
            
            return GroupQueryResult(
                group_id=group_id,
                articles_found=0,
                articles_new=0,
                concepts_used=concepts if concepts else [],
                keywords_used=all_keywords if not concepts else [],
                error=str(ex),
            )
    
    def run(self) -> IngestResult:
        """
        Execute multi-query ingestion.
        
        Queries each group separately and deduplicates results.
        """
        run_id = utc_now_compact()
        
        groups = self._get_groups()
        logger.info(
            f"Starting multi-query ingestion: {len(groups)} groups, "
            f"max_per_group={self.params.max_per_group}, "
            f"max_total={self.params.max_total}"
        )
        
        # Query each group
        for group in groups:
            if len(self.all_articles) >= self.params.max_total:
                logger.info("Reached max_total, stopping queries")
                break
            
            result = self._query_group(group)
            self.group_results.append(result)
        
        # Save results
        ensure_dir(self.params.out_dir)
        
        payload: Dict[str, Any] = {
            "meta": {
                "provider": "newsapi.ai (EventRegistry)",
                "version": "2.0-multi-query",
                "run_id": run_id,
                "generated_at_utc": utc_now_iso_z(),
                "scope_yaml": str(self.params.scope_yaml).replace("\\", "/"),
                "date_start": self.params.date_start.isoformat(),
                "date_end": self.params.date_end.isoformat(),
                "langs": self._get_langs(),
                "location_uri": self._get_location_uri(),
                "max_per_group": self.params.max_per_group,
                "max_total": self.params.max_total,
                "sort_by": self.params.sort_by,
                "allow_archive": self.params.allow_archive,
                # Query statistics
                "groups_queried": len(self.group_results),
                "total_articles_found": sum(r.articles_found for r in self.group_results),
                "unique_articles": len(self.all_articles),
                "group_results": [
                    {
                        "group_id": r.group_id,
                        "articles_found": r.articles_found,
                        "articles_new": r.articles_new,
                        "concepts_used": len(r.concepts_used),
                        "keywords_used": len(r.keywords_used),
                        "error": r.error,
                    }
                    for r in self.group_results
                ],
                "errors": self.errors if self.errors else None,
            },
            "articles": self.all_articles,
        }
        
        out_path = self.params.out_dir / f"{run_id}.json"
        out_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        logger.success(
            f"[RAW] Fichero generado: {out_path.as_posix()} "
            f"(articles={len(self.all_articles)})"
        )
        
        return IngestResult(
            run_id=run_id,
            output_path=out_path,
            total_articles=sum(r.articles_found for r in self.group_results),
            unique_articles=len(self.all_articles),
            groups_queried=len(self.group_results),
            group_results=self.group_results,
            errors=self.errors,
        )


# =============================================================================
# CONVENIENCE FUNCTION (backward compatible)
# =============================================================================

def run_newsapi_ai_ingestion(params: IngestParams) -> Path:
    """
    Run multi-query ingestion and return output path.
    
    Backward compatible interface.
    """
    ingestor = MultiQueryIngestor(params)
    result = ingestor.run()
    return result.output_path


# =============================================================================
# CLI ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    import argparse
    from datetime import timedelta
    
    parser = argparse.ArgumentParser(description="NewsAPI.ai Multi-Query Ingestion")
    parser.add_argument("--scope", required=True, help="Path to scope YAML")
    parser.add_argument("--date-start", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--date-end", help="End date (YYYY-MM-DD)")
    parser.add_argument("--max-per-group", type=int, default=50)
    parser.add_argument("--max-total", type=int, default=200)
    parser.add_argument("--priority", type=int, nargs="+", help="Priority filter (e.g., 1 2)")
    parser.add_argument("--out-dir", default="data/raw/newsapi_ai")
    
    args = parser.parse_args()
    
    # Default dates: yesterday to today
    if args.date_end:
        end_date = date.fromisoformat(args.date_end)
    else:
        end_date = date.today()
    
    if args.date_start:
        start_date = date.fromisoformat(args.date_start)
    else:
        start_date = end_date - timedelta(days=1)
    
    params = IngestParams(
        scope_yaml=Path(args.scope),
        out_dir=Path(args.out_dir),
        date_start=start_date,
        date_end=end_date,
        max_per_group=args.max_per_group,
        max_total=args.max_total,
        priority_filter=args.priority,
    )
    
    result_path = run_newsapi_ai_ingestion(params)
    print(f"Output: {result_path}")

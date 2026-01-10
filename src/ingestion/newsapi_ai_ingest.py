"""
src/ingestion/newsapi_ai_ingest.py
Last updated: 2026-01-09
Description: Multi-strategy ingestion for NewsAPI.ai with keyword group support

STRATEGIES:
1. location_based (v3): Uses locationUri + conceptUri per group
2. source_based (v4): Uses sourceUri only (all articles from sources)
3. source_keywords (v5): Uses sourceUri + ALL keywords (BROKEN - exceeds 15 keyword limit)
4. source_keywords_by_group (v6): Uses sourceUri + keywords PER GROUP (≤15 each)

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
    """Return current UTC time as compact string for run IDs."""
    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")


def utc_now_iso_z() -> str:
    """Return current UTC time in ISO format with Z suffix."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def ensure_dir(p: Path) -> None:
    """Create directory if it doesn't exist."""
    p.mkdir(parents=True, exist_ok=True)


def load_scope_yaml(scope_path: Path) -> Dict[str, Any]:
    """Load and validate scope YAML configuration."""
    data = yaml.safe_load(scope_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Scope YAML is not a valid dict.")
    return data


def get_api_key() -> str:
    """Get NewsAPI.ai API key from environment variables."""
    load_dotenv()
    key = (
        os.getenv("NEWSAPI_KEY")
        or os.getenv("NEWSAPI_AI_KEY")
        or os.getenv("EVENTREGISTRY_API_KEY")
    )
    if not key:
        raise RuntimeError("Missing NEWSAPI_KEY in .env file")
    return key


def safe_article_info_flags(body_len: int = 8000) -> ArticleInfoFlags:
    """Create ArticleInfoFlags with best-effort for detailed article info."""
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
    """Result of querying a single concept/keyword group."""
    group_id: str
    articles_found: int
    articles_new: int  # After deduplication
    concepts_used: List[str]
    keywords_used: List[str]
    sources_used: List[str] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class IngestParams:
    """Parameters for ingestion run."""
    scope_yaml: Path
    out_dir: Path
    date_start: date
    date_end: date
    max_per_group: int = 100
    max_total: int = 500
    sort_by: str = "date"
    allow_archive: bool = True
    langs: Optional[List[str]] = None
    priority_filter: Optional[List[int]] = None


@dataclass
class IngestResult:
    """Result of complete ingestion run."""
    run_id: str
    output_path: Path
    total_articles: int
    unique_articles: int
    groups_queried: int
    group_results: List[GroupQueryResult]
    strategy: str = "location_based"
    errors: List[str] = field(default_factory=list)


# =============================================================================
# MULTI-QUERY INGESTION
# =============================================================================

class MultiQueryIngestor:
    """
    Ingestion strategy that queries articles from NewsAPI.ai.
    
    Supports four strategies:
    1. location_based (v3): Uses locationUri + conceptUri per group
    2. source_based (v4): Uses sourceUri only (gets ALL from sources)
    3. source_keywords (v5): Uses sourceUri + ALL keywords (BROKEN)
    4. source_keywords_by_group (v6): Uses sourceUri + keywords PER GROUP
    """

    # Maximum keywords per query (NewsAPI.ai limit)
    MAX_KEYWORDS_PER_QUERY = 15

    def __init__(self, params: IngestParams):
        self.params = params
        self.scope = load_scope_yaml(params.scope_yaml)
        self.er = EventRegistry(apiKey=get_api_key())
        self.ret_info = ReturnInfo(articleInfo=safe_article_info_flags())
        
        # Track articles across queries for deduplication
        self.seen_uris: Set[str] = set()
        self.all_articles: List[Dict] = []
        self.group_results: List[GroupQueryResult] = []
        self.errors: List[str] = []
        
        # Detect strategy from scope
        self.strategy = self.scope.get("strategy", "location_based")
        logger.info(f"Using ingestion strategy: {self.strategy}")

    def _get_source_uris(self) -> List[str]:
        """Get source URIs for source-based strategies."""
        return self.scope.get("source_uris", [])

    def _get_keywords(self) -> List[str]:
        """Get ALL keywords for source_keywords strategy (v5 - legacy)."""
        return self.scope.get("all_keywords", [])

    def _get_keyword_groups(self) -> List[Dict[str, Any]]:
        """Get keyword groups for source_keywords_by_group strategy (v6)."""
        groups = self.scope.get("keyword_groups", [])
        
        # Filter by priority if specified
        if self.params.priority_filter:
            groups = [
                g for g in groups
                if g.get("priority", 2) in self.params.priority_filter
            ]
        
        return sorted(groups, key=lambda g: g.get("priority", 99))

    def _get_location_uri(self) -> Optional[str]:
        """Get location URI for location_based strategy."""
        return self.scope.get("scope", {}).get("location_uri")

    def _get_langs(self) -> List[str]:
        """Get languages from scope configuration."""
        langs = self.scope.get("langs")
        if not langs:
            langs = self.scope.get("query_config", {}).get("langs")
        if not langs:
            langs = self.params.langs
        return langs or ["spa", "eng"]

    def _get_max_per_group(self) -> int:
        """Get max articles per group from config or params."""
        config_max = self.scope.get("query_config", {}).get("max_per_group")
        return config_max or self.params.max_per_group

    def _get_groups(self) -> List[Dict[str, Any]]:
        """Get concept groups for location_based strategy (v3)."""
        if self.strategy in ["source_based", "source_keywords", "source_keywords_by_group"]:
            return []
        
        groups = self.scope.get("scope", {}).get("concept_groups", [])

        if self.params.priority_filter:
            groups = [
                g for g in groups
                if g.get("priority", 2) in self.params.priority_filter
            ]

        return sorted(groups, key=lambda g: g.get("priority", 99))

    # -------------------------------------------------------------------------
    # STRATEGY: source_keywords_by_group (v6) - NEW
    # -------------------------------------------------------------------------
    
    def _query_source_keywords_by_group(self) -> List[GroupQueryResult]:
        """
        Query articles from sources filtered by keyword groups (v6 strategy).
        
        Each group generates one query with:
        - sourceUri: all configured sources (OR)
        - keywords: group-specific keywords (OR, max 15)
        
        Returns list of results, one per group.
        """
        source_uris = self._get_source_uris()
        keyword_groups = self._get_keyword_groups()
        
        if not source_uris:
            error_msg = "No source_uris defined in scope"
            logger.error(f"[source_keywords_by_group] {error_msg}")
            return [GroupQueryResult(
                group_id="source_keywords_by_group",
                articles_found=0,
                articles_new=0,
                concepts_used=[],
                keywords_used=[],
                sources_used=[],
                error=error_msg
            )]
        
        if not keyword_groups:
            logger.warning("[source_keywords_by_group] No keyword_groups defined, falling back to source_based")
            return [self._query_sources()]
        
        logger.info(
            f"[source_keywords_by_group] Starting: {len(keyword_groups)} groups, "
            f"{len(source_uris)} sources, max_per_group={self._get_max_per_group()}"
        )
        
        results: List[GroupQueryResult] = []
        
        for group in keyword_groups:
            # Check if we've hit max_total
            if len(self.all_articles) >= self.params.max_total:
                logger.info(f"[source_keywords_by_group] Reached max_total ({self.params.max_total}), stopping")
                break
            
            result = self._query_single_keyword_group(group, source_uris)
            results.append(result)
        
        return results

    def _query_single_keyword_group(
        self, 
        group: Dict[str, Any], 
        source_uris: List[str]
    ) -> GroupQueryResult:
        """
        Execute query for a single keyword group.
        
        Args:
            group: Dict with group_id, label, keywords, priority
            source_uris: List of source URIs to filter by
            
        Returns:
            GroupQueryResult with query statistics
        """
        group_id = group.get("group_id", "unknown")
        keywords = group.get("keywords", [])
        
        # Validate keyword count
        if len(keywords) > self.MAX_KEYWORDS_PER_QUERY:
            logger.warning(
                f"[{group_id}] Group has {len(keywords)} keywords, "
                f"truncating to {self.MAX_KEYWORDS_PER_QUERY}"
            )
            keywords = keywords[:self.MAX_KEYWORDS_PER_QUERY]
        
        if not keywords:
            logger.warning(f"[{group_id}] No keywords defined, skipping group")
            return GroupQueryResult(
                group_id=group_id,
                articles_found=0,
                articles_new=0,
                concepts_used=[],
                keywords_used=[],
                sources_used=source_uris,
                error="No keywords defined for group"
            )
        
        logger.info(f"[{group_id}] Querying with {len(keywords)} keywords...")
        
        try:
            # Build query with sources + keywords
            q = QueryArticlesIter(
                sourceUri=QueryItems.OR(source_uris),
                keywords=QueryItems.OR(keywords),
                lang=QueryItems.OR(self._get_langs()),
                dateStart=self.params.date_start.isoformat(),
                dateEnd=self.params.date_end.isoformat(),
            )
            
            articles_found = 0
            articles_new = 0
            max_for_group = self._get_max_per_group()
            
            for art in q.execQuery(
                self.er,
                sortBy=self.params.sort_by,
                returnInfo=self.ret_info,
                maxItems=max_for_group,
            ):
                articles_found += 1
                
                # Deduplicate by URI across all groups
                uri = art.get("uri", "")
                if uri and uri not in self.seen_uris:
                    self.seen_uris.add(uri)
                    art["_source_group"] = group_id
                    art["_strategy"] = "source_keywords_by_group"
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
                concepts_used=[],
                keywords_used=keywords,
                sources_used=source_uris,
            )
            
        except Exception as ex:
            error_msg = f"[{group_id}] Query failed: {ex}"
            logger.error(error_msg)
            self.errors.append(error_msg)
            
            return GroupQueryResult(
                group_id=group_id,
                articles_found=0,
                articles_new=0,
                concepts_used=[],
                keywords_used=keywords,
                sources_used=source_uris,
                error=str(ex),
            )

    # -------------------------------------------------------------------------
    # STRATEGY: source_keywords (v5) - LEGACY/BROKEN
    # -------------------------------------------------------------------------
    
    def _query_source_keywords(self) -> GroupQueryResult:
        """
        Query articles from sources filtered by ALL keywords (v5 strategy).
        
        WARNING: This strategy is BROKEN if all_keywords > 15.
        Kept for backward compatibility but will log a warning.
        """
        source_uris = self._get_source_uris()
        keywords = self._get_keywords()
        
        if not source_uris:
            return GroupQueryResult(
                group_id="source_keywords",
                articles_found=0,
                articles_new=0,
                concepts_used=[],
                keywords_used=[],
                sources_used=[],
                error="No source_uris defined in scope"
            )
        
        if not keywords:
            logger.warning("[source_keywords] No keywords defined, falling back to source_based")
            return self._query_sources()
        
        # CRITICAL: Check keyword limit
        if len(keywords) > self.MAX_KEYWORDS_PER_QUERY:
            error_msg = (
                f"[source_keywords] ERROR: {len(keywords)} keywords exceeds API limit of "
                f"{self.MAX_KEYWORDS_PER_QUERY}. Use strategy 'source_keywords_by_group' instead."
            )
            logger.error(error_msg)
            self.errors.append(error_msg)
            
            return GroupQueryResult(
                group_id="source_keywords",
                articles_found=0,
                articles_new=0,
                concepts_used=[],
                keywords_used=keywords,
                sources_used=source_uris,
                error=error_msg
            )
        
        logger.info(f"[source_keywords] Querying {len(source_uris)} sources with {len(keywords)} keywords")
        
        try:
            q = QueryArticlesIter(
                sourceUri=QueryItems.OR(source_uris),
                keywords=QueryItems.OR(keywords),
                lang=QueryItems.OR(self._get_langs()),
                dateStart=self.params.date_start.isoformat(),
                dateEnd=self.params.date_end.isoformat(),
            )
            
            articles_found = 0
            articles_new = 0
            
            for art in q.execQuery(
                self.er,
                sortBy=self.params.sort_by,
                returnInfo=self.ret_info,
                maxItems=self.params.max_total,
            ):
                articles_found += 1
                
                uri = art.get("uri", "")
                if uri and uri not in self.seen_uris:
                    self.seen_uris.add(uri)
                    art["_source_group"] = "source_keywords"
                    art["_strategy"] = "source_keywords"
                    self.all_articles.append(art)
                    articles_new += 1
                
                if len(self.all_articles) >= self.params.max_total:
                    logger.info(f"[source_keywords] Reached max_total ({self.params.max_total}), stopping")
                    break
            
            logger.success(
                f"[source_keywords] Found {articles_found} articles, "
                f"{articles_new} new (after dedup)"
            )
            
            return GroupQueryResult(
                group_id="source_keywords",
                articles_found=articles_found,
                articles_new=articles_new,
                concepts_used=[],
                keywords_used=keywords,
                sources_used=source_uris,
            )
            
        except Exception as ex:
            error_msg = f"[source_keywords] Query failed: {ex}"
            logger.error(error_msg)
            self.errors.append(error_msg)
            
            return GroupQueryResult(
                group_id="source_keywords",
                articles_found=0,
                articles_new=0,
                concepts_used=[],
                keywords_used=keywords,
                sources_used=source_uris,
                error=str(ex),
            )

    # -------------------------------------------------------------------------
    # STRATEGY: source_based (v4)
    # -------------------------------------------------------------------------
    
    def _query_sources(self) -> GroupQueryResult:
        """
        Query all articles from configured sources (source_based strategy v4).
        
        No keyword filtering - gets everything from the sources.
        """
        source_uris = self._get_source_uris()
        
        if not source_uris:
            return GroupQueryResult(
                group_id="source_based",
                articles_found=0,
                articles_new=0,
                concepts_used=[],
                keywords_used=[],
                sources_used=[],
                error="No source_uris defined in scope"
            )
        
        logger.info(f"[source_based] Querying {len(source_uris)} sources (no keyword filter)")
        
        try:
            q = QueryArticlesIter(
                sourceUri=QueryItems.OR(source_uris),
                lang=QueryItems.OR(self._get_langs()),
                dateStart=self.params.date_start.isoformat(),
                dateEnd=self.params.date_end.isoformat(),
            )
            
            articles_found = 0
            articles_new = 0
            
            for art in q.execQuery(
                self.er,
                sortBy=self.params.sort_by,
                returnInfo=self.ret_info,
                maxItems=self.params.max_total,
            ):
                articles_found += 1
                
                uri = art.get("uri", "")
                if uri and uri not in self.seen_uris:
                    self.seen_uris.add(uri)
                    art["_source_group"] = "source_based"
                    art["_strategy"] = "source_based"
                    self.all_articles.append(art)
                    articles_new += 1
                
                if len(self.all_articles) >= self.params.max_total:
                    logger.info(f"[source_based] Reached max_total ({self.params.max_total}), stopping")
                    break
            
            logger.success(
                f"[source_based] Found {articles_found} articles, "
                f"{articles_new} new (after dedup)"
            )
            
            return GroupQueryResult(
                group_id="source_based",
                articles_found=articles_found,
                articles_new=articles_new,
                concepts_used=[],
                keywords_used=[],
                sources_used=source_uris,
            )
            
        except Exception as ex:
            error_msg = f"[source_based] Query failed: {ex}"
            logger.error(error_msg)
            self.errors.append(error_msg)
            
            return GroupQueryResult(
                group_id="source_based",
                articles_found=0,
                articles_new=0,
                concepts_used=[],
                keywords_used=[],
                sources_used=source_uris,
                error=str(ex),
            )

    # -------------------------------------------------------------------------
    # STRATEGY: location_based (v3)
    # -------------------------------------------------------------------------
    
    def _query_group(self, group: Dict[str, Any]) -> GroupQueryResult:
        """
        Query articles for a single concept group (location_based strategy v3).
        
        Uses locationUri + conceptUri/keywords.
        """
        group_id = group.get("group_id", "unknown")
        label = group.get("label", group_id)
        concepts = group.get("concept_uris", [])
        keywords_spa = group.get("keywords_spa", [])
        keywords_eng = group.get("keywords_eng", [])
        all_keywords = keywords_spa + keywords_eng
        location_uri = self._get_location_uri()
        langs = self._get_langs()

        logger.info(
            f"[{group_id}] Starting query: {len(concepts)} concepts, "
            f"{len(all_keywords)} keywords"
        )

        try:
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
                # Respect keyword limit
                if len(all_keywords) > self.MAX_KEYWORDS_PER_QUERY:
                    logger.warning(
                        f"[{group_id}] Truncating keywords from {len(all_keywords)} "
                        f"to {self.MAX_KEYWORDS_PER_QUERY}"
                    )
                    all_keywords = all_keywords[:self.MAX_KEYWORDS_PER_QUERY]
                
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

            articles_found = 0
            articles_new = 0

            for art in q.execQuery(
                self.er,
                sortBy=self.params.sort_by,
                returnInfo=self.ret_info,
                maxItems=self.params.max_per_group,
            ):
                articles_found += 1

                uri = art.get("uri", "")
                if uri and uri not in self.seen_uris:
                    self.seen_uris.add(uri)
                    art["_source_group"] = group_id
                    art["_strategy"] = "location_based"
                    self.all_articles.append(art)
                    articles_new += 1

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

    # -------------------------------------------------------------------------
    # MAIN RUN METHOD
    # -------------------------------------------------------------------------
    
    def run(self) -> IngestResult:
        """
        Execute multi-query ingestion based on configured strategy.
        """
        run_id = utc_now_compact()

        if self.strategy == "source_keywords_by_group":
            # V6 strategy: sources + keywords BY GROUP (RECOMMENDED)
            logger.info("Starting source+keywords by group ingestion (v6)")
            results = self._query_source_keywords_by_group()
            self.group_results.extend(results)
            
        elif self.strategy == "source_keywords":
            # V5 strategy: sources + ALL keywords (BROKEN if >15 keywords)
            logger.warning("Using source_keywords strategy (v5) - may fail if >15 keywords")
            result = self._query_source_keywords()
            self.group_results.append(result)
            
        elif self.strategy == "source_based":
            # V4 strategy: query all from sources (no keyword filter)
            logger.info("Starting source-based ingestion (v4)")
            result = self._query_sources()
            self.group_results.append(result)
            
        else:
            # V3 strategy: query each concept group with location
            groups = self._get_groups()
            logger.info(
                f"Starting location-based ingestion (v3): {len(groups)} groups, "
                f"max_per_group={self.params.max_per_group}, "
                f"max_total={self.params.max_total}"
            )

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
                "version": "3.0-multi-strategy",
                "strategy": self.strategy,
                "run_id": run_id,
                "generated_at_utc": utc_now_iso_z(),
                "scope_yaml": str(self.params.scope_yaml).replace("\\", "/"),
                "date_start": self.params.date_start.isoformat(),
                "date_end": self.params.date_end.isoformat(),
                "langs": self._get_langs(),
                "location_uri": self._get_location_uri() if self.strategy == "location_based" else None,
                "source_uris": self._get_source_uris() if self.strategy != "location_based" else None,
                "max_per_group": self._get_max_per_group(),
                "max_total": self.params.max_total,
                "sort_by": self.params.sort_by,
                "allow_archive": self.scope.get("allow_archive", True),
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
                        "sources_used": len(r.sources_used),
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
            f"[RAW] Output file generated: {out_path.as_posix()} "
            f"(articles={len(self.all_articles)})"
        )

        return IngestResult(
            run_id=run_id,
            output_path=out_path,
            total_articles=sum(r.articles_found for r in self.group_results),
            unique_articles=len(self.all_articles),
            groups_queried=len(self.group_results),
            group_results=self.group_results,
            strategy=self.strategy,
            errors=self.errors,
        )


# =============================================================================
# CONVENIENCE FUNCTION
# =============================================================================

def run_newsapi_ai_ingestion(params: IngestParams) -> Path:
    """Run multi-query ingestion and return output path."""
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
    parser.add_argument("--max-per-group", type=int, default=100)
    parser.add_argument("--max-total", type=int, default=500)
    parser.add_argument("--priority", type=int, nargs="+", help="Priority filter (e.g., 1 2)")
    parser.add_argument("--out-dir", default="data/raw/newsapi_ai")

    args = parser.parse_args()

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

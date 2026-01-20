"""
src/llm_providers/anthropic_provider.py

Anthropic Claude provider for LLM enrichment.
Used for local development and testing.

Environment variables required:
    ANTHROPIC_API_KEY: Your Anthropic API key
    
Optional:
    ANTHROPIC_MODEL: Model to use (default: claude-3-5-haiku-20241022)
"""
from __future__ import annotations

import os
from typing import Dict, Any

from loguru import logger

from .base import BaseLLMProvider
from .prompts import ENRICHMENT_PROMPT


class AnthropicProvider(BaseLLMProvider):
    """
    Anthropic Claude provider.
    
    Default model: claude-3-5-haiku-20241022 (fast and cost-effective)
    Alternative: claude-3-5-sonnet-20241022 (more capable, higher cost)
    """
    
    DEFAULT_MODEL = "claude-3-5-haiku-20241022"
    
    def __init__(self, model: str = None):
        super().__init__()
        self.model = model or os.getenv("ANTHROPIC_MODEL", self.DEFAULT_MODEL)
        self._init_client()
    
    def _init_client(self):
        """Initialize Anthropic client."""
        try:
            from anthropic import Anthropic
        except ImportError:
            raise ImportError(
                "anthropic package not installed. "
                "Install with: pip install anthropic"
            )
        
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY not found in environment. "
                "Set it in your .env file or environment variables."
            )
        
        self.client = Anthropic(api_key=api_key)
        logger.info(f"Anthropic client initialized with model: {self.model}")
    
    @property
    def provider_name(self) -> str:
        return "anthropic"
    
    @property
    def model_name(self) -> str:
        return self.model
    
    def enrich_article(self, title: str, body: str, source: str) -> Dict[str, Any]:
        """
        Enrich article using Claude.
        
        Args:
            title: Article title
            body: Article body (truncated to 3000 chars)
            source: Source name
            
        Returns:
            Classification dictionary with metadata
        """
        prompt = ENRICHMENT_PROMPT.format(
            title=title,
            body=(body or "")[:3000],
            source=source or "Desconocido"
        )
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=700,
                messages=[{"role": "user", "content": prompt}]
            )
            
            raw = response.content[0].text
            tokens_in = response.usage.input_tokens
            tokens_out = response.usage.output_tokens
            
            # Update stats
            self.total_tokens_in += tokens_in
            self.total_tokens_out += tokens_out
            self.total_requests += 1
            
            # Parse response
            result = self._parse_json_response(raw)
            
            # Add metadata
            result["_tokens_in"] = tokens_in
            result["_tokens_out"] = tokens_out
            result["_model"] = self.model
            result["_provider"] = self.provider_name
            
            return result
            
        except Exception as e:
            self.errors += 1
            logger.error(f"Anthropic API error: {e}")
            return {
                "error": str(e),
                "es_relevante": False,
                "_provider": self.provider_name,
                "_model": self.model
            }
    
    def _calculate_cost(self) -> float:
        """
        Calculate cost based on Claude Haiku pricing.
        
        Pricing (per 1M tokens):
        - Input: $0.25
        - Output: $1.25
        """
        return round(
            self.total_tokens_in / 1_000_000 * 0.25 + 
            self.total_tokens_out / 1_000_000 * 1.25,
            4
        )

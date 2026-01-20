"""
src/llm_providers/base.py

Abstract base class for LLM providers.
Enables switching between Anthropic (local/dev) and Azure OpenAI (prod).

Usage:
    from src.llm_providers import get_llm_client
    
    client = get_llm_client()  # Auto-selects based on LLM_PROVIDER env var
    result = client.enrich_article(title, body, source)
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, Any
from dataclasses import dataclass


@dataclass
class LLMResponse:
    """Standardized response from any LLM provider."""
    content: Dict[str, Any]  # Parsed JSON response
    tokens_in: int
    tokens_out: int
    model: str
    provider: str  # 'anthropic' or 'azure_openai'
    
    @property
    def cost_usd(self) -> float:
        """Calculate cost based on provider pricing."""
        if self.provider == 'anthropic':
            # Claude Haiku pricing (per 1M tokens)
            return (self.tokens_in / 1_000_000 * 0.25 + 
                    self.tokens_out / 1_000_000 * 1.25)
        elif self.provider == 'azure_openai':
            # GPT-4o-mini pricing (per 1M tokens) - Azure pricing
            return (self.tokens_in / 1_000_000 * 0.15 + 
                    self.tokens_out / 1_000_000 * 0.60)
        return 0.0


class BaseLLMProvider(ABC):
    """
    Abstract base class for LLM providers.
    
    All providers must implement:
    - enrich_article(): Main classification method
    - get_stats(): Return usage statistics
    """
    
    def __init__(self):
        self.total_tokens_in = 0
        self.total_tokens_out = 0
        self.total_requests = 0
        self.errors = 0
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return provider identifier (e.g., 'anthropic', 'azure_openai')."""
        pass
    
    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the model being used."""
        pass
    
    @abstractmethod
    def enrich_article(self, title: str, body: str, source: str) -> Dict[str, Any]:
        """
        Enrich an article with LLM classification.
        
        Args:
            title: Article title
            body: Article body text
            source: Source name
            
        Returns:
            Dict with classification results including:
            - es_relevante: bool
            - es_internacional: bool
            - es_resumen: bool
            - tipo_evento: str
            - subtipo: str
            - muertos: int or None
            - heridos: int or None
            - departamento: str or None
            - provincia: str or None
            - distrito: str or None
            - ubicacion_especifica: str or None
            - pais_evento: str
            - actores: list
            - organizaciones: list
            - resumen_es: str
            - resumen_en: str
            - sentiment: str
            - confianza: float
            - _tokens_in: int
            - _tokens_out: int
            - _model: str
        """
        pass
    
    def get_stats(self) -> Dict[str, Any]:
        """Return usage statistics."""
        return {
            "provider": self.provider_name,
            "model": self.model_name,
            "tokens_in": self.total_tokens_in,
            "tokens_out": self.total_tokens_out,
            "total_requests": self.total_requests,
            "errors": self.errors,
            "cost_usd": self._calculate_cost()
        }
    
    @abstractmethod
    def _calculate_cost(self) -> float:
        """Calculate total cost in USD based on token usage."""
        pass
    
    def _parse_json_response(self, raw: str) -> Dict[str, Any]:
        """
        Parse JSON from LLM response, handling markdown code blocks.
        
        Args:
            raw: Raw string response from LLM
            
        Returns:
            Parsed dictionary
        """
        import json
        
        raw = raw.strip()
        
        # Remove markdown code blocks if present
        if raw.startswith("```"):
            lines = raw.split("```")
            if len(lines) >= 2:
                raw = lines[1]
                if raw.startswith("json"):
                    raw = raw[4:]
        
        raw = raw.strip()
        
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\{[\s\S]*\}', raw)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass
            
            raise ValueError(f"Failed to parse JSON: {e}. Raw: {raw[:200]}")

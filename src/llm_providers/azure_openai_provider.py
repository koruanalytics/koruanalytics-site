"""
src/llm_providers/azure_openai_provider.py

Azure OpenAI provider for LLM enrichment.
Used for production deployment on Azure.

Environment variables required:
    AZURE_OPENAI_ENDPOINT: Your Azure OpenAI endpoint URL
    AZURE_OPENAI_API_KEY: Your Azure OpenAI API key
    AZURE_OPENAI_DEPLOYMENT: Deployment name (e.g., 'gpt-4o-mini')
    
Optional:
    AZURE_OPENAI_API_VERSION: API version (default: 2024-08-01-preview)
"""
from __future__ import annotations

import os
from typing import Dict, Any

from loguru import logger

from .base import BaseLLMProvider
from .prompts import ENRICHMENT_PROMPT


class AzureOpenAIProvider(BaseLLMProvider):
    """
    Azure OpenAI provider.
    
    Recommended deployment: gpt-4o-mini (cost-effective, fast)
    Alternative: gpt-4o (more capable, higher cost)
    """
    
    DEFAULT_API_VERSION = "2024-08-01-preview"
    
    def __init__(
        self, 
        endpoint: str = None,
        api_key: str = None,
        deployment: str = None,
        api_version: str = None
    ):
        super().__init__()
        
        self.endpoint = endpoint or os.getenv("AZURE_OPENAI_ENDPOINT")
        self.api_key = api_key or os.getenv("AZURE_OPENAI_API_KEY")
        self.deployment = deployment or os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")
        self.api_version = api_version or os.getenv("AZURE_OPENAI_API_VERSION", self.DEFAULT_API_VERSION)
        
        self._init_client()
    
    def _init_client(self):
        """Initialize Azure OpenAI client."""
        try:
            from openai import AzureOpenAI
        except ImportError:
            raise ImportError(
                "openai package not installed. "
                "Install with: pip install openai"
            )
        
        if not self.endpoint:
            raise ValueError(
                "AZURE_OPENAI_ENDPOINT not found. "
                "Set it in your .env file or environment variables."
            )
        
        if not self.api_key:
            raise ValueError(
                "AZURE_OPENAI_API_KEY not found. "
                "Set it in your .env file or environment variables."
            )
        
        self.client = AzureOpenAI(
            azure_endpoint=self.endpoint,
            api_key=self.api_key,
            api_version=self.api_version
        )
        
        logger.info(
            f"Azure OpenAI client initialized: "
            f"endpoint={self.endpoint}, deployment={self.deployment}"
        )
    
    @property
    def provider_name(self) -> str:
        return "azure_openai"
    
    @property
    def model_name(self) -> str:
        return self.deployment
    
    def enrich_article(self, title: str, body: str, source: str) -> Dict[str, Any]:
        """
        Enrich article using Azure OpenAI.
        
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
            response = self.client.chat.completions.create(
                model=self.deployment,
                max_tokens=700,
                messages=[
                    {
                        "role": "system",
                        "content": "Eres un analista de seguridad especializado en Perú. Responde únicamente en JSON válido."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                response_format={"type": "json_object"}  # Enforce JSON response
            )
            
            raw = response.choices[0].message.content
            tokens_in = response.usage.prompt_tokens
            tokens_out = response.usage.completion_tokens
            
            # Update stats
            self.total_tokens_in += tokens_in
            self.total_tokens_out += tokens_out
            self.total_requests += 1
            
            # Parse response
            result = self._parse_json_response(raw)
            
            # Add metadata
            result["_tokens_in"] = tokens_in
            result["_tokens_out"] = tokens_out
            result["_model"] = self.deployment
            result["_provider"] = self.provider_name
            
            return result
            
        except Exception as e:
            self.errors += 1
            logger.error(f"Azure OpenAI API error: {e}")
            return {
                "error": str(e),
                "es_relevante": False,
                "_provider": self.provider_name,
                "_model": self.deployment
            }
    
    def _calculate_cost(self) -> float:
        """
        Calculate cost based on Azure OpenAI GPT-4o-mini pricing.
        
        Pricing (per 1M tokens) - Azure pay-as-you-go:
        - Input: $0.15
        - Output: $0.60
        """
        return round(
            self.total_tokens_in / 1_000_000 * 0.15 + 
            self.total_tokens_out / 1_000_000 * 0.60,
            4
        )


class AzureOpenAIProviderWithManagedIdentity(AzureOpenAIProvider):
    """
    Azure OpenAI provider using Managed Identity authentication.
    
    Use this for production deployments where the code runs inside Azure
    (Azure Functions, Container Apps, VMs with Managed Identity).
    
    No API key required - uses DefaultAzureCredential.
    
    Environment variables required:
        AZURE_OPENAI_ENDPOINT: Your Azure OpenAI endpoint URL
        AZURE_OPENAI_DEPLOYMENT: Deployment name
    """
    
    def _init_client(self):
        """Initialize Azure OpenAI client with Managed Identity."""
        try:
            from openai import AzureOpenAI
            from azure.identity import DefaultAzureCredential, get_bearer_token_provider
        except ImportError:
            raise ImportError(
                "Required packages not installed. "
                "Install with: pip install openai azure-identity"
            )
        
        if not self.endpoint:
            raise ValueError(
                "AZURE_OPENAI_ENDPOINT not found. "
                "Set it in your .env file or environment variables."
            )
        
        # Use Managed Identity for authentication
        credential = DefaultAzureCredential()
        token_provider = get_bearer_token_provider(
            credential,
            "https://cognitiveservices.azure.com/.default"
        )
        
        self.client = AzureOpenAI(
            azure_endpoint=self.endpoint,
            azure_ad_token_provider=token_provider,
            api_version=self.api_version
        )
        
        logger.info(
            f"Azure OpenAI client initialized with Managed Identity: "
            f"endpoint={self.endpoint}, deployment={self.deployment}"
        )

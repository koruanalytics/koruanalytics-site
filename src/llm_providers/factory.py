"""
src/llm_providers/factory.py

Factory for creating LLM provider instances.
Auto-selects provider based on LLM_PROVIDER environment variable.

Usage:
    from src.llm_providers import get_llm_client
    
    # Auto-select based on LLM_PROVIDER env var
    client = get_llm_client()
    
    # Or explicitly specify
    client = get_llm_client(provider="anthropic")
    client = get_llm_client(provider="azure_openai")
    
Environment variables:
    LLM_PROVIDER: 'anthropic' or 'azure_openai' (default: 'anthropic')
    
    For Anthropic:
        ANTHROPIC_API_KEY: Required
        ANTHROPIC_MODEL: Optional (default: claude-3-5-haiku-20241022)
        
    For Azure OpenAI:
        AZURE_OPENAI_ENDPOINT: Required
        AZURE_OPENAI_API_KEY: Required (or use Managed Identity)
        AZURE_OPENAI_DEPLOYMENT: Required (e.g., 'gpt-4o-mini')
"""
from __future__ import annotations

import os
from typing import Optional, Literal

from loguru import logger

from .base import BaseLLMProvider


ProviderType = Literal["anthropic", "azure_openai", "azure_openai_managed"]


def get_llm_client(
    provider: Optional[ProviderType] = None,
    **kwargs
) -> BaseLLMProvider:
    """
    Factory function to get the appropriate LLM client.
    
    Args:
        provider: Explicit provider selection. If None, uses LLM_PROVIDER env var.
                  Options: 'anthropic', 'azure_openai', 'azure_openai_managed'
        **kwargs: Additional arguments passed to the provider constructor
        
    Returns:
        Configured LLM provider instance
        
    Raises:
        ValueError: If provider is unknown or misconfigured
    """
    # Determine provider
    if provider is None:
        provider = os.getenv("LLM_PROVIDER", "anthropic").lower()
    
    logger.info(f"Initializing LLM provider: {provider}")
    
    if provider == "anthropic":
        from .anthropic_provider import AnthropicProvider
        return AnthropicProvider(**kwargs)
    
    elif provider == "azure_openai":
        from .azure_openai_provider import AzureOpenAIProvider
        return AzureOpenAIProvider(**kwargs)
    
    elif provider == "azure_openai_managed":
        from .azure_openai_provider import AzureOpenAIProviderWithManagedIdentity
        return AzureOpenAIProviderWithManagedIdentity(**kwargs)
    
    else:
        raise ValueError(
            f"Unknown LLM provider: {provider}. "
            f"Valid options: 'anthropic', 'azure_openai', 'azure_openai_managed'"
        )


def get_provider_info() -> dict:
    """
    Get information about available providers and current configuration.
    
    Returns:
        Dictionary with provider info and which env vars are set
    """
    return {
        "current_provider": os.getenv("LLM_PROVIDER", "anthropic"),
        "available_providers": ["anthropic", "azure_openai", "azure_openai_managed"],
        "env_vars": {
            "LLM_PROVIDER": os.getenv("LLM_PROVIDER"),
            # Anthropic
            "ANTHROPIC_API_KEY": "***" if os.getenv("ANTHROPIC_API_KEY") else None,
            "ANTHROPIC_MODEL": os.getenv("ANTHROPIC_MODEL"),
            # Azure OpenAI
            "AZURE_OPENAI_ENDPOINT": os.getenv("AZURE_OPENAI_ENDPOINT"),
            "AZURE_OPENAI_API_KEY": "***" if os.getenv("AZURE_OPENAI_API_KEY") else None,
            "AZURE_OPENAI_DEPLOYMENT": os.getenv("AZURE_OPENAI_DEPLOYMENT"),
        }
    }

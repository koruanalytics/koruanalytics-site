"""
Example integration: How to modify llm_enrichment_pipeline.py

This shows the minimal changes needed to use the new multi-provider LLM module.

DIFF-STYLE CHANGES:
==================

1. At the top of the file, REMOVE the old LLMClient class (lines ~145-210)

2. REPLACE the import and class with:

```python
# OLD (remove this):
# class LLMClient:
#     def __init__(self, model: str = DEFAULT_MODEL):
#         self.model = model
#         ...
#         from anthropic import Anthropic
#         api_key = os.getenv("ANTHROPIC_API_KEY")
#         self.client = Anthropic(api_key=api_key)

# NEW (add this):
from src.llm_providers import get_llm_client
```

3. In EnrichmentPipeline.__init__, CHANGE:

```python
# OLD:
class EnrichmentPipeline:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.llm = LLMClient()  # <-- OLD

# NEW:
class EnrichmentPipeline:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.llm = get_llm_client()  # <-- NEW (auto-selects based on LLM_PROVIDER)
```

That's it! The interface is compatible, so all calls like:
    self.llm.enrich_article(title, body, source)
    self.llm.get_stats()
    
Will work exactly the same.
"""

# =============================================================================
# EXAMPLE: Standalone test of the new providers
# =============================================================================

def test_providers():
    """Test both providers with a sample article."""
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    # Sample article
    test_article = {
        "title": "Sicarios asesinan a empresario en Trujillo",
        "body": """Esta madrugada, un empresario del rubro de transportes fue 
        asesinado a balazos cuando salía de su domicilio en el distrito de 
        La Esperanza, provincia de Trujillo, región La Libertad. Los sicarios 
        huyeron en una mototaxi. La policía investiga el caso y no descarta 
        que se trate de un ajuste de cuentas vinculado a extorsiones.""",
        "source": "La República"
    }
    
    # Test Anthropic (if configured)
    if os.getenv("ANTHROPIC_API_KEY"):
        print("\n" + "="*60)
        print("TESTING ANTHROPIC (Claude Haiku)")
        print("="*60)
        
        from src.llm_providers import get_llm_client
        client = get_llm_client(provider="anthropic")
        
        result = client.enrich_article(**test_article)
        print(f"\nProvider: {result.get('_provider')}")
        print(f"Model: {result.get('_model')}")
        print(f"Relevante: {result.get('es_relevante')}")
        print(f"Tipo: {result.get('tipo_evento')}")
        print(f"Departamento: {result.get('departamento')}")
        print(f"Muertos: {result.get('muertos')}")
        print(f"Tokens: {result.get('_tokens_in')} in, {result.get('_tokens_out')} out")
        
        stats = client.get_stats()
        print(f"Cost: ${stats['cost_usd']:.4f}")
    
    # Test Azure OpenAI (if configured)
    if os.getenv("AZURE_OPENAI_ENDPOINT") and os.getenv("AZURE_OPENAI_API_KEY"):
        print("\n" + "="*60)
        print("TESTING AZURE OPENAI (GPT-4o-mini)")
        print("="*60)
        
        from src.llm_providers import get_llm_client
        client = get_llm_client(provider="azure_openai")
        
        result = client.enrich_article(**test_article)
        print(f"\nProvider: {result.get('_provider')}")
        print(f"Model: {result.get('_model')}")
        print(f"Relevante: {result.get('es_relevante')}")
        print(f"Tipo: {result.get('tipo_evento')}")
        print(f"Departamento: {result.get('departamento')}")
        print(f"Muertos: {result.get('muertos')}")
        print(f"Tokens: {result.get('_tokens_in')} in, {result.get('_tokens_out')} out")
        
        stats = client.get_stats()
        print(f"Cost: ${stats['cost_usd']:.4f}")


# =============================================================================
# EXAMPLE: Modified EnrichmentPipeline class
# =============================================================================

class EnrichmentPipelineMultiProvider:
    """
    Example of EnrichmentPipeline using the new multi-provider module.
    
    This is a simplified version showing the key integration points.
    """
    
    def __init__(self, db_path: str = "data/osint_dw.duckdb"):
        import duckdb
        from src.llm_providers import get_llm_client
        
        self.db_path = db_path
        self.llm = get_llm_client()  # Auto-selects based on LLM_PROVIDER env var
        
        print(f"Pipeline initialized with {self.llm.provider_name} ({self.llm.model_name})")
    
    def process_article(self, title: str, body: str, source: str):
        """Process a single article."""
        result = self.llm.enrich_article(title, body, source)
        
        if result.get("error"):
            print(f"Error: {result['error']}")
            return None
        
        return result
    
    def get_cost_summary(self):
        """Get cost summary."""
        stats = self.llm.get_stats()
        return {
            "provider": stats["provider"],
            "model": stats["model"],
            "requests": stats["total_requests"],
            "cost_usd": stats["cost_usd"]
        }


if __name__ == "__main__":
    test_providers()

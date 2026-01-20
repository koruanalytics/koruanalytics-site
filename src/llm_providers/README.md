# LLM Providers - Módulo de Abstracción

## Descripción

Este módulo proporciona una capa de abstracción para usar diferentes proveedores de LLM (Large Language Models) de forma intercambiable. Permite usar **Anthropic Claude** para desarrollo local y **Azure OpenAI** para producción en Azure.

## Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                    Pipeline de Enriquecimiento              │
│                                                             │
│         from llm_providers import get_llm_client            │
│         client = get_llm_client()                           │
│         result = client.enrich_article(title, body, src)    │
│                          │                                  │
│                          ▼                                  │
│              ┌─────────────────────┐                        │
│              │  BaseLLMProvider    │  ◄── Interfaz común    │
│              │  (Abstract Class)   │                        │
│              └──────────┬──────────┘                        │
│                         │                                   │
│           ┌─────────────┴─────────────┐                     │
│           ▼                           ▼                     │
│  ┌─────────────────┐        ┌─────────────────────┐         │
│  │ AnthropicProvider│       │ AzureOpenAIProvider │         │
│  │ Claude Haiku    │        │ GPT-4o-mini        │         │
│  │ (Dev/Local)     │        │ (Prod/Azure)       │         │
│  └─────────────────┘        └─────────────────────┘         │
└─────────────────────────────────────────────────────────────┘
```

## Instalación

### Para desarrollo local (Anthropic):
```bash
pip install anthropic
```

### Para producción Azure:
```bash
pip install openai azure-identity
```

## Configuración

### Variables de Entorno

```bash
# Selección de proveedor
LLM_PROVIDER=anthropic        # Para desarrollo
LLM_PROVIDER=azure_openai     # Para producción

# Anthropic (desarrollo)
ANTHROPIC_API_KEY=sk-ant-api03-...

# Azure OpenAI (producción)
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-key
AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini
```

## Uso

### Básico (auto-selección por env var)

```python
from llm_providers import get_llm_client

# Crea cliente según LLM_PROVIDER
client = get_llm_client()

# Clasificar artículo
result = client.enrich_article(
    title="Asalto en banco de Lima deja 2 heridos",
    body="Esta mañana, delincuentes armados...",
    source="El Comercio"
)

print(result)
# {
#     "es_relevante": True,
#     "es_internacional": False,
#     "tipo_evento": "crimen_violento",
#     "muertos": 0,
#     "heridos": 2,
#     "departamento": "Lima",
#     ...
# }

# Ver estadísticas
stats = client.get_stats()
print(f"Tokens: {stats['tokens_in']} in, {stats['tokens_out']} out")
print(f"Costo: ${stats['cost_usd']:.4f}")
```

### Selección explícita de proveedor

```python
from llm_providers import get_llm_client

# Forzar Anthropic
client = get_llm_client(provider="anthropic")

# Forzar Azure OpenAI
client = get_llm_client(provider="azure_openai")

# Azure con Managed Identity (sin API key)
client = get_llm_client(provider="azure_openai_managed")
```

### Verificar configuración

```python
from llm_providers import get_provider_info

info = get_provider_info()
print(info)
# {
#     "current_provider": "anthropic",
#     "available_providers": ["anthropic", "azure_openai", "azure_openai_managed"],
#     "env_vars": {
#         "LLM_PROVIDER": "anthropic",
#         "ANTHROPIC_API_KEY": "***",
#         ...
#     }
# }
```

## Integración con Pipeline Existente

### Antes (hardcoded Anthropic):

```python
# llm_enrichment_pipeline.py
class LLMClient:
    def __init__(self, model: str = DEFAULT_MODEL):
        from anthropic import Anthropic
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
```

### Después (multi-provider):

```python
# llm_enrichment_pipeline.py
from llm_providers import get_llm_client

class EnrichmentPipeline:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.llm = get_llm_client()  # Auto-selecciona según .env
```

## Costos Comparativos

| Proveedor | Modelo | Input (1M tok) | Output (1M tok) | ~Costo/artículo |
|-----------|--------|----------------|-----------------|-----------------|
| Anthropic | Claude Haiku | $0.25 | $1.25 | ~$0.0015 |
| Azure OpenAI | GPT-4o-mini | $0.15 | $0.60 | ~$0.0010 |

*Nota: GPT-4o-mini es ~33% más económico que Claude Haiku*

## Estructura de Archivos

```
src/llm_providers/
├── __init__.py           # Exports públicos
├── base.py               # Clase abstracta BaseLLMProvider
├── anthropic_provider.py # Implementación Anthropic
├── azure_openai_provider.py  # Implementación Azure OpenAI
├── factory.py            # Factory get_llm_client()
├── prompts.py            # Prompts compartidos
├── .env.example          # Variables de entorno ejemplo
└── README.md             # Esta documentación
```

## Migración de Pipeline Existente

Para migrar el pipeline actual a usar este módulo:

1. **Copiar el módulo** `llm_providers/` a `src/llm_providers/`

2. **Modificar** `llm_enrichment_pipeline.py`:

```python
# Remover:
# from anthropic import Anthropic
# class LLMClient: ...

# Agregar:
from src.llm_providers import get_llm_client

class EnrichmentPipeline:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.llm = get_llm_client()
```

3. **Actualizar** `.env`:
```bash
# Agregar línea para selección de proveedor
LLM_PROVIDER=anthropic
```

4. **Para Azure**, agregar:
```bash
LLM_PROVIDER=azure_openai
AZURE_OPENAI_ENDPOINT=https://...
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini
```

## Testing

```python
# test_providers.py
import pytest
from llm_providers import get_llm_client

def test_anthropic_provider():
    client = get_llm_client(provider="anthropic")
    assert client.provider_name == "anthropic"
    
def test_azure_provider():
    client = get_llm_client(provider="azure_openai")
    assert client.provider_name == "azure_openai"

def test_classification_consistency():
    """Verify both providers give similar results."""
    test_article = {
        "title": "Asalto en banco de Lima",
        "body": "Delincuentes armados...",
        "source": "El Comercio"
    }
    
    anthropic = get_llm_client(provider="anthropic")
    azure = get_llm_client(provider="azure_openai")
    
    r1 = anthropic.enrich_article(**test_article)
    r2 = azure.enrich_article(**test_article)
    
    # Both should identify as relevant crime
    assert r1["es_relevante"] == r2["es_relevante"]
    assert r1["tipo_evento"] == r2["tipo_evento"]
```

## Troubleshooting

### Error: "ANTHROPIC_API_KEY not found"
- Verificar que `.env` existe y tiene la variable
- Verificar que `python-dotenv` está instalado

### Error: "AZURE_OPENAI_ENDPOINT not found"
- Verificar variables de Azure en `.env`
- Verificar que el recurso Azure OpenAI existe

### Error: "Model deployment not found"
- Verificar que `AZURE_OPENAI_DEPLOYMENT` coincide con el nombre del deployment en Azure Portal

### Diferencias en clasificación entre proveedores
- Normal: los modelos pueden diferir en casos ambiguos
- El prompt está optimizado para minimizar diferencias
- Para casos críticos, considerar validación cruzada

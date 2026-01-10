"""
src/classification/llm_classifier.py - Clasificador de noticias con LLM

Usa Claude Haiku para:
1. Filtrar ruido (deportes, farándula, economía general)
2. Clasificar tipo de evento de seguridad
3. Extraer víctimas (muertos/heridos)
4. Geolocalizar (departamento, ubicación específica)
5. Identificar actores relevantes

Diseñado para integración con Azure OpenAI en producción.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any
from datetime import datetime

from dotenv import load_dotenv
from loguru import logger

load_dotenv()

# =============================================================================
# CONFIGURACIÓN
# =============================================================================

# Modelo a usar (cambiar a Azure OpenAI en producción)
DEFAULT_MODEL = "claude-3-5-haiku-20241022"

# Categorías válidas de eventos
VALID_EVENT_TYPES = [
    "violencia_armada",      # Enfrentamientos, tiroteos, ataques armados
    "crimen_violento",       # Asesinatos, homicidios, sicariato
    "violencia_sexual",      # Violaciones, abuso sexual
    "secuestro",             # Secuestros, desapariciones forzadas
    "feminicidio",           # Feminicidios
    "accidente_grave",       # Accidentes con muertos/heridos
    "desastre_natural",      # Sismos, inundaciones, huaycos
    "protesta",              # Protestas, marchas
    "disturbio",             # Disturbios, vandalismo, saqueos
    "terrorismo",            # Ataques terroristas, Sendero
    "crimen_organizado",     # Narcotráfico, extorsión organizada
    "violencia_politica",    # Ataques a candidatos, violencia electoral
    "operativo_seguridad",   # Detenciones, capturas, incautaciones
    "no_relevante",          # No relacionado con seguridad
]

# Departamentos de Perú para validación
DEPARTAMENTOS_PERU = [
    "Amazonas", "Áncash", "Apurímac", "Arequipa", "Ayacucho",
    "Cajamarca", "Callao", "Cusco", "Huancavelica", "Huánuco",
    "Ica", "Junín", "La Libertad", "Lambayeque", "Lima",
    "Loreto", "Madre de Dios", "Moquegua", "Pasco", "Piura",
    "Puno", "San Martín", "Tacna", "Tumbes", "Ucayali"
]

# =============================================================================
# PROMPT DE CLASIFICACIÓN
# =============================================================================

CLASSIFICATION_PROMPT = """Eres un analista de seguridad especializado en Perú. Tu tarea es clasificar noticias para un sistema de monitoreo de seguridad electoral.

INSTRUCCIONES:
1. Analiza el título y cuerpo de la noticia
2. Determina si es RELEVANTE para seguridad (violencia, crimen, accidentes graves, desastres, protestas)
3. Extrae información estructurada

CATEGORÍAS DE EVENTOS (usa exactamente estos valores):
- violencia_armada: Enfrentamientos, tiroteos, balaceras, ataques con armas
- crimen_violento: Asesinatos, homicidios, sicariato, agresiones graves
- violencia_sexual: Violaciones, abuso sexual, acoso sexual grave
- secuestro: Secuestros, desapariciones forzadas, raptos
- feminicidio: Asesinato de mujeres por razón de género
- accidente_grave: Accidentes de tránsito, laborales o industriales con víctimas
- desastre_natural: Sismos, terremotos, inundaciones, huaycos, deslizamientos
- protesta: Marchas, manifestaciones, paros, huelgas
- disturbio: Disturbios, vandalismo, saqueos, enfrentamientos con policía
- terrorismo: Ataques terroristas, Sendero Luminoso, VRAEM
- crimen_organizado: Narcotráfico, extorsión organizada, bandas criminales
- violencia_politica: Ataques a candidatos, amenazas políticas, violencia electoral
- operativo_seguridad: Detenciones importantes, capturas, incautaciones grandes
- no_relevante: Deportes, farándula, economía general, política sin violencia, internacional sin impacto en Perú

CRITERIOS DE RELEVANCIA:
- SÍ relevante: Cualquier evento que involucre violencia, víctimas, riesgo para la población, o impacto en seguridad
- NO relevante: Noticias de entretenimiento, deportes, economía general, política internacional sin impacto directo en Perú, horóscopo, tecnología general

UBICACIÓN:
- Si la noticia menciona un lugar específico en Perú, extrae departamento y ubicación
- Si es una noticia nacional sin lugar específico, usa departamento: null, ubicacion: "Perú (nacional)"
- Si es sobre otro país (Venezuela, EEUU, etc.) sin impacto en Perú, marca como no_relevante

NOTICIA A ANALIZAR:
Título: {title}
Cuerpo: {body}

Responde ÚNICAMENTE con un JSON válido (sin markdown, sin explicaciones):
{{
    "es_relevante": true/false,
    "tipo_evento": "categoria_del_listado",
    "subtipo": "descripción breve del evento específico",
    "muertos": número o null si no menciona,
    "heridos": número o null si no menciona,
    "departamento": "nombre del departamento" o null,
    "ubicacion_especifica": "ciudad/distrito/lugar" o null,
    "actores": ["lista de personas/organizaciones mencionadas relevantes"] o [],
    "resumen": "resumen de 1 línea del evento",
    "confianza": 0.0-1.0
}}"""


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ClassificationResult:
    """Resultado de clasificación de una noticia."""
    es_relevante: bool
    tipo_evento: str
    subtipo: Optional[str]
    muertos: Optional[int]
    heridos: Optional[int]
    departamento: Optional[str]
    ubicacion_especifica: Optional[str]
    actores: List[str]
    resumen: str
    confianza: float
    
    # Metadata
    modelo_usado: str = ""
    tokens_input: int = 0
    tokens_output: int = 0
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# =============================================================================
# CLASIFICADOR
# =============================================================================

class LLMClassifier:
    """Clasificador de noticias usando LLM."""
    
    def __init__(self, model: str = DEFAULT_MODEL, provider: str = "anthropic"):
        self.model = model
        self.provider = provider
        self.client = self._init_client()
        self.total_tokens_input = 0
        self.total_tokens_output = 0
        
    def _init_client(self):
        """Inicializa el cliente según el proveedor."""
        if self.provider == "anthropic":
            from anthropic import Anthropic
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY no encontrada en .env")
            return Anthropic(api_key=api_key)
        elif self.provider == "azure_openai":
            # Para migración futura a Azure
            raise NotImplementedError("Azure OpenAI no implementado aún")
        else:
            raise ValueError(f"Proveedor no soportado: {self.provider}")
    
    def classify_article(
        self, 
        title: str, 
        body: str = "",
        max_body_chars: int = 2000
    ) -> ClassificationResult:
        """
        Clasifica un artículo individual.
        
        Args:
            title: Título del artículo
            body: Cuerpo del artículo (truncado si muy largo)
            max_body_chars: Máximo de caracteres del body a enviar
            
        Returns:
            ClassificationResult con la clasificación
        """
        # Truncar body si es muy largo
        body_truncated = (body or "")[:max_body_chars]
        if len(body or "") > max_body_chars:
            body_truncated += "..."
        
        # Preparar prompt
        prompt = CLASSIFICATION_PROMPT.format(
            title=title,
            body=body_truncated if body_truncated else "(sin cuerpo disponible)"
        )
        
        try:
            if self.provider == "anthropic":
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=500,
                    messages=[{"role": "user", "content": prompt}]
                )
                
                raw_response = response.content[0].text
                tokens_in = response.usage.input_tokens
                tokens_out = response.usage.output_tokens
                
            # Parsear JSON
            result_dict = self._parse_json_response(raw_response)
            
            # Validar y normalizar
            result = self._normalize_result(result_dict)
            result.modelo_usado = self.model
            result.tokens_input = tokens_in
            result.tokens_output = tokens_out
            
            # Acumular tokens
            self.total_tokens_input += tokens_in
            self.total_tokens_output += tokens_out
            
            return result
            
        except Exception as e:
            logger.error(f"Error clasificando artículo: {e}")
            return ClassificationResult(
                es_relevante=False,
                tipo_evento="error",
                subtipo=None,
                muertos=None,
                heridos=None,
                departamento=None,
                ubicacion_especifica=None,
                actores=[],
                resumen="Error en clasificación",
                confianza=0.0,
                modelo_usado=self.model,
                error=str(e)
            )
    
    def _parse_json_response(self, raw: str) -> Dict[str, Any]:
        """Parsea la respuesta JSON del LLM."""
        # Limpiar posible markdown
        raw = raw.strip()
        if raw.startswith("```json"):
            raw = raw[7:]
        if raw.startswith("```"):
            raw = raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()
        
        return json.loads(raw)
    
    def _normalize_result(self, data: Dict[str, Any]) -> ClassificationResult:
        """Normaliza y valida el resultado."""
        # Validar tipo_evento
        tipo = data.get("tipo_evento", "no_relevante")
        if tipo not in VALID_EVENT_TYPES:
            tipo = "no_relevante"
        
        # Validar departamento
        depto = data.get("departamento")
        if depto and depto not in DEPARTAMENTOS_PERU:
            # Intentar normalizar
            depto_norm = self._normalize_departamento(depto)
            depto = depto_norm
        
        # Validar números
        muertos = data.get("muertos")
        if muertos is not None:
            try:
                muertos = int(muertos)
            except (ValueError, TypeError):
                muertos = None
                
        heridos = data.get("heridos")
        if heridos is not None:
            try:
                heridos = int(heridos)
            except (ValueError, TypeError):
                heridos = None
        
        return ClassificationResult(
            es_relevante=bool(data.get("es_relevante", False)),
            tipo_evento=tipo,
            subtipo=data.get("subtipo"),
            muertos=muertos,
            heridos=heridos,
            departamento=depto,
            ubicacion_especifica=data.get("ubicacion_especifica"),
            actores=data.get("actores", []) or [],
            resumen=data.get("resumen", ""),
            confianza=float(data.get("confianza", 0.5))
        )
    
    def _normalize_departamento(self, depto: str) -> Optional[str]:
        """Intenta normalizar nombre de departamento."""
        if not depto:
            return None
        
        depto_lower = depto.lower().strip()
        
        # Mapeo de variantes comunes
        mappings = {
            "ancash": "Áncash",
            "apurimac": "Apurímac",
            "cuzco": "Cusco",
            "lima metropolitana": "Lima",
            "lima provincias": "Lima",
        }
        
        if depto_lower in mappings:
            return mappings[depto_lower]
        
        # Buscar coincidencia parcial
        for d in DEPARTAMENTOS_PERU:
            if d.lower() == depto_lower:
                return d
        
        return depto  # Devolver original si no se encuentra
    
    def classify_batch(
        self, 
        articles: List[Dict[str, Any]],
        title_key: str = "title",
        body_key: str = "body",
        id_key: str = "incident_id",
        progress_every: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Clasifica un batch de artículos.
        
        Args:
            articles: Lista de dicts con los artículos
            title_key: Clave para el título
            body_key: Clave para el cuerpo
            id_key: Clave para el ID
            progress_every: Mostrar progreso cada N artículos
            
        Returns:
            Lista de dicts con ID y resultado de clasificación
        """
        results = []
        total = len(articles)
        
        for i, article in enumerate(articles):
            article_id = article.get(id_key, f"article_{i}")
            title = article.get(title_key, "")
            body = article.get(body_key, "")
            
            result = self.classify_article(title, body)
            
            results.append({
                "id": article_id,
                "classification": result.to_dict()
            })
            
            if (i + 1) % progress_every == 0:
                logger.info(f"Procesados {i+1}/{total} artículos...")
        
        logger.success(
            f"Clasificación completada: {total} artículos, "
            f"{self.total_tokens_input} tokens input, "
            f"{self.total_tokens_output} tokens output"
        )
        
        return results
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Retorna estadísticas de uso."""
        # Costos aproximados de Haiku
        cost_input = (self.total_tokens_input / 1_000_000) * 0.25
        cost_output = (self.total_tokens_output / 1_000_000) * 1.25
        
        return {
            "total_tokens_input": self.total_tokens_input,
            "total_tokens_output": self.total_tokens_output,
            "estimated_cost_usd": round(cost_input + cost_output, 4)
        }


# =============================================================================
# FUNCIONES DE CONVENIENCIA
# =============================================================================

def classify_single(title: str, body: str = "") -> ClassificationResult:
    """Clasifica un artículo individual (función de conveniencia)."""
    classifier = LLMClassifier()
    return classifier.classify_article(title, body)


def classify_from_db(
    limit: int = 100,
    where_clause: str = "",
    update_db: bool = False
) -> List[Dict[str, Any]]:
    """
    Clasifica artículos desde la base de datos.
    
    Args:
        limit: Número máximo de artículos a procesar
        where_clause: Cláusula WHERE adicional (sin "WHERE")
        update_db: Si True, actualiza la BD con los resultados
        
    Returns:
        Lista de resultados de clasificación
    """
    import duckdb
    from src.utils.config import load_config
    
    cfg = load_config()
    con = duckdb.connect(cfg["db"]["duckdb_path"])
    
    # Query base
    query = f"""
        SELECT incident_id, title, body
        FROM fct_daily_report
        {f'WHERE {where_clause}' if where_clause else ''}
        LIMIT {limit}
    """
    
    articles = con.execute(query).fetchdf().to_dict('records')
    
    if not articles:
        logger.warning("No se encontraron artículos para clasificar")
        return []
    
    logger.info(f"Clasificando {len(articles)} artículos...")
    
    classifier = LLMClassifier()
    results = classifier.classify_batch(
        articles,
        title_key="title",
        body_key="body",
        id_key="incident_id"
    )
    
    if update_db:
        _update_db_with_results(con, results)
    
    con.close()
    
    # Mostrar stats
    stats = classifier.get_usage_stats()
    logger.info(f"Uso de API: {stats}")
    
    return results


def _update_db_with_results(con, results: List[Dict[str, Any]]):
    """Actualiza la BD con los resultados de clasificación."""
    updated = 0
    
    for r in results:
        incident_id = r["id"]
        c = r["classification"]
        
        if c.get("error"):
            continue
        
        # Actualizar campos relevantes
        con.execute("""
            UPDATE fct_daily_report
            SET 
                event_type = ?,
                sub_event_type = ?,
                deaths = COALESCE(?, deaths),
                injuries = COALESCE(?, injuries),
                adm1 = COALESCE(?, adm1),
                location_display = COALESCE(?, location_display)
            WHERE incident_id = ?
        """, [
            c.get("tipo_evento"),
            c.get("subtipo"),
            c.get("muertos"),
            c.get("heridos"),
            c.get("departamento"),
            c.get("ubicacion_especifica"),
            incident_id
        ])
        updated += 1
    
    logger.success(f"Actualizados {updated} registros en la BD")


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Clasificador LLM de noticias")
    parser.add_argument("--test", action="store_true", help="Ejecutar test con ejemplos")
    parser.add_argument("--classify-db", type=int, help="Clasificar N artículos de la BD")
    parser.add_argument("--update", action="store_true", help="Actualizar BD con resultados")
    parser.add_argument("--where", type=str, default="", help="Filtro WHERE para query")
    
    args = parser.parse_args()
    
    if args.test:
        # Test con ejemplos
        test_cases = [
            ("Un muerto, 36 heridos tras choque de trenes rumbo a Machu Picchu", ""),
            ("Sicarios asesinan a comerciante en Trujillo", "El hombre recibió múltiples disparos."),
            ("Karla Tarazona enfurece con Christian Cueva por Pamela Franco", ""),
            ("Temblor de magnitud 6.0 sacude Chimbote", "El sismo se sintió en varias regiones."),
            ("Trump ordena ataques dentro de Venezuela", "Noticia internacional."),
            ("Candidato a alcaldía recibe amenazas de muerte en Arequipa", ""),
        ]
        
        classifier = LLMClassifier()
        
        print("=" * 70)
        print("TEST DE CLASIFICACIÓN LLM")
        print("=" * 70)
        
        for title, body in test_cases:
            result = classifier.classify_article(title, body)
            print(f"\n📰 {title[:60]}...")
            print(f"   Relevante: {result.es_relevante}")
            print(f"   Tipo: {result.tipo_evento}")
            print(f"   Muertos/Heridos: {result.muertos}/{result.heridos}")
            print(f"   Ubicación: {result.departamento} - {result.ubicacion_especifica}")
            print(f"   Confianza: {result.confianza}")
        
        print(f"\n📊 Uso API: {classifier.get_usage_stats()}")
    
    elif args.classify_db:
        results = classify_from_db(
            limit=args.classify_db,
            where_clause=args.where,
            update_db=args.update
        )
        
        # Mostrar resumen
        relevantes = sum(1 for r in results if r["classification"].get("es_relevante"))
        print(f"\n📊 Resumen: {relevantes}/{len(results)} artículos relevantes")

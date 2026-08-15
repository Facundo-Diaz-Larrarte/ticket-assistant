import math
from typing import Dict, Any, Optional
from app.storage.sqlite import IntelligenceDatabase

# Factores de demanda conocidos por artista y plaza (Priors de cuarteto/rock en Córdoba y Río Cuarto)
KNOWN_HIGH_DEMAND_ARTISTS = {
    "q' lokura": {"baseline_prob": 0.95, "avg_hours": 3.5, "speed": "ULTRA_FAST"},
    "q lokura": {"baseline_prob": 0.95, "avg_hours": 3.5, "speed": "ULTRA_FAST"},
    "desakta2": {"baseline_prob": 0.92, "avg_hours": 4.0, "speed": "ULTRA_FAST"},
    "la mona": {"baseline_prob": 0.98, "avg_hours": 1.5, "speed": "IMMEDIATE"},
    "duki": {"baseline_prob": 0.96, "avg_hours": 2.0, "speed": "ULTRA_FAST"},
    "cosquin rock": {"baseline_prob": 0.99, "avg_hours": 24.0, "speed": "HIGH"}
}

class TicketIntelligenceEngine:
    """Motor de análisis de demanda, cálculo de probabilidad de Sold-Out y tiempo estimado de agotamiento."""

    def __init__(self, db: IntelligenceDatabase):
        self.db = db

    async def calculate_sold_out_forecast(
        self,
        event_name: str,
        city: Optional[str] = None,
        venue: Optional[str] = None,
        price: Optional[float] = None
    ) -> Dict[str, Any]:
        """Calcula la probabilidad de agotamiento y el nivel de urgencia de compra."""
        name_lower = event_name.lower()
        city_lower = (city or "").lower()
        
        # 1. Consultar historial en base de datos
        db_stats = await self.db.get_artist_stats(event_name)
        
        # 2. Obtener prior de la banda si es conocida
        matched_prior = None
        for artist_key, prior_data in KNOWN_HIGH_DEMAND_ARTISTS.items():
            if artist_key in name_lower:
                matched_prior = prior_data
                break

        # 3. Calcular probabilidad combinada
        if matched_prior:
            base_prob = matched_prior["baseline_prob"]
            estimated_hours = matched_prior["avg_hours"]
            urgency = matched_prior["speed"]
        else:
            base_prob = 0.65
            estimated_hours = 48.0
            urgency = "MODERATE"

        # Ajuste por ciudad/lugar (Río Cuarto / Opus Costanera tiene capacidad limitada ~2500 personas)
        if "rio cuarto" in city_lower or "opus" in (venue or "").lower():
            base_prob = min(0.99, base_prob + 0.05) # Mayor presión de demanda por menor aforo
            estimated_hours = max(1.0, estimated_hours * 0.8)

        # Ajuste por historial empírico si hay suficientes muestras
        if db_stats["total_events"] >= 2 and db_stats["sold_out_rate"] is not None:
            # Ponderación Bayesiana entre el prior y las observaciones reales registradas
            observed_rate = db_stats["sold_out_rate"]
            base_prob = (base_prob * 0.4) + (observed_rate * 0.6)
            if db_stats["avg_hours_to_sold_out"]:
                estimated_hours = db_stats["avg_hours_to_sold_out"]

        prob_percentage = round(base_prob * 100, 1)

        # Categoría de riesgo
        if prob_percentage >= 90:
            risk_label = "🔴 RIESGO EXTREMO (Agotamiento Inminente)"
            recommendation = "Comprar en los primeros 5-15 minutos tras el lanzamiento."
        elif prob_percentage >= 75:
            risk_label = "🟠 ALTA DEMANDA (Probable Sold-Out)"
            recommendation = "Asegurar entradas dentro de las primeras horas."
        else:
            risk_label = "🟢 DEMANDA MODERADA"
            recommendation = "Disponibilidad estándar."

        return {
            "sold_out_probability_pct": prob_percentage,
            "expected_time_to_sold_out_hours": round(estimated_hours, 1),
            "urgency_level": urgency,
            "risk_label": risk_label,
            "recommendation": recommendation,
            "historical_observations_count": db_stats["total_events"]
        }

import math
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from app.storage.sqlite import IntelligenceDatabase

logger = logging.getLogger(__name__)

# Pesos del Plan Maestro V1
WEIGHT_ARTIST = 0.35
WEIGHT_LOCAL = 0.30
WEIGHT_VENUE = 0.15
WEIGHT_PRICE = 0.10
WEIGHT_DATE = 0.10

# Priors de arranque para artistas cuando hay pocas o cero observaciones
ARTIST_PRIORS = {
    "q' lokura": {"score": 92.0, "avg_hours": 3.5, "speed": "ULTRA_FAST"},
    "q lokura": {"score": 92.0, "avg_hours": 3.5, "speed": "ULTRA_FAST"},
    "desakta2": {"score": 90.0, "avg_hours": 4.5, "speed": "ULTRA_FAST"},
    "la mona": {"score": 98.0, "avg_hours": 1.5, "speed": "IMMEDIATE"},
    "la mona jimenez": {"score": 98.0, "avg_hours": 1.5, "speed": "IMMEDIATE"},
    "la konga": {"score": 88.0, "avg_hours": 8.0, "speed": "FAST"},
    "la k'onga": {"score": 88.0, "avg_hours": 8.0, "speed": "FAST"},
    "euge quevedo": {"score": 94.0, "avg_hours": 3.0, "speed": "ULTRA_FAST"},
    "lbc": {"score": 93.0, "avg_hours": 4.0, "speed": "ULTRA_FAST"},
    "ulises bueno": {"score": 88.0, "avg_hours": 6.0, "speed": "FAST"},
    "ulises": {"score": 88.0, "avg_hours": 6.0, "speed": "FAST"},
    "dale q' va": {"score": 82.0, "avg_hours": 12.0, "speed": "FAST"},
    "dale q va": {"score": 82.0, "avg_hours": 12.0, "speed": "FAST"},
    "simon aguirre": {"score": 80.0, "avg_hours": 14.0, "speed": "MODERATE"},
    "simón aguirre": {"score": 80.0, "avg_hours": 14.0, "speed": "MODERATE"},
    "loco amato": {"score": 87.0, "avg_hours": 8.0, "speed": "FAST"},
    "el loco amato": {"score": 87.0, "avg_hours": 8.0, "speed": "FAST"},
    "cristian amato": {"score": 87.0, "avg_hours": 8.0, "speed": "FAST"},
    "amato": {"score": 87.0, "avg_hours": 8.0, "speed": "FAST"},
    "luck ra": {"score": 89.0, "avg_hours": 5.0, "speed": "FAST"},
    "duki": {"score": 96.0, "avg_hours": 2.0, "speed": "ULTRA_FAST"},
    "cosquin rock": {"score": 98.0, "avg_hours": 24.0, "speed": "HIGH"}
}

# Referencia de precio mediano de mercado para cuarteto (ARS)
MEDIAN_MARKET_PRICE_ARS = 13000.0


class TicketIntelligenceEngine:
    """Motor determinístico de inteligencia de demanda (Ticket Intelligence V1).

    Calcula el Sold-Out Score (0-100), Data Confidence y desglose explicable por componentes.
    """

    def __init__(self, db: IntelligenceDatabase):
        self.db = db

    async def calculate_artist_score(self, event_name: str) -> Dict[str, Any]:
        """Calcula el Score de Historial del Artista (A) - 35%."""
        stats = await self.db.get_artist_stats(event_name)
        total = stats["total_events"]
        sold_out_rate = stats["sold_out_rate"]

        # Buscar prior por defecto
        name_lower = event_name.lower()
        matched_prior = None
        for key, prior_data in ARTIST_PRIORS.items():
            if key in name_lower:
                matched_prior = prior_data
                break

        prior_score = matched_prior["score"] if matched_prior else 70.0

        if total == 0 or sold_out_rate is None:
            score = prior_score
        else:
            # Ponderar observaciones históricas con el prior (suavizado)
            # Más observaciones -> más peso a la tasa observada
            weight_observed = min(0.85, total / (total + 3.0))
            score = (sold_out_rate * 100.0 * weight_observed) + (prior_score * (1.0 - weight_observed))

        return {
            "score": round(max(10.0, min(100.0, score)), 1),
            "observations": total,
            "sold_out_events": stats["sold_out_events"],
            "avg_hours": stats["avg_hours_to_sold_out"] or (matched_prior["avg_hours"] if matched_prior else 24.0),
            "speed": matched_prior["speed"] if matched_prior else "MODERATE"
        }

    async def calculate_local_score(self, event_name: str, city: Optional[str], artist_baseline: float) -> Dict[str, Any]:
        """Calcula el Score de Rendimiento Local (L) con Suavizado Bayesiano - 30%.

        Fórmula: L = 100 * (s + alpha * p) / (n + alpha)
        """
        if not city:
            # Si no hay ciudad especificada, usar el score general del artista
            return {"score": artist_baseline, "observations": 0, "bayesian_smoothed": False}

        local_stats = await self.db.get_local_artist_stats(event_name, city)
        s = local_stats["sold_out_events"]
        n = local_stats["total_events"]

        # Parámetros bayesianos
        p = artist_baseline / 100.0  # Tasa base esperada
        alpha = 3.0  # Fuerza del prior (equivale a 3 eventos de amortiguación)

        smoothed_rate = (s + (alpha * p)) / (n + alpha)
        score = smoothed_rate * 100.0

        return {
            "score": round(max(10.0, min(100.0, score)), 1),
            "observations": n,
            "local_sold_outs": s,
            "bayesian_smoothed": True
        }

    async def calculate_venue_score(self, venue: Optional[str], city: Optional[str]) -> Dict[str, Any]:
        """Calcula el Score de Escasez por Aforo (V) - 15%.

        Lugares chicos/medianos generan mayor velocidad de agotamiento.
        """
        capacity = None
        venue_name = venue or ""

        if venue:
            venue_info = await self.db.get_venue_info(venue)
            if venue_info and venue_info.get("capacity_estimate"):
                capacity = venue_info["capacity_estimate"]

        # Si no se encontró en DB, estimar por palabras clave conocidas
        v_lower = venue_name.lower()
        if capacity is None:
            if "opus" in v_lower or "costanera" in v_lower:
                capacity = 3500
            elif "plaza de la musica" in v_lower or "plaza de la música" in v_lower:
                capacity = 6000
            elif "forja" in v_lower:
                capacity = 15000
            elif "atenas" in v_lower or "belgrano" in v_lower:
                capacity = 4000
            elif "anfiteatro" in v_lower:
                capacity = 12000
            elif "kempes" in v_lower:
                capacity = 45000

        # Mapeo de capacidad a score de escasez
        if capacity is None:
            score = 75.0  # Neutral
            label = "UNKNOWN_CAPACITY"
        elif capacity <= 3500:
            score = 95.0  # Escasez extrema (ej: Opus Río Cuarto, Atenas)
            label = "VERY_HIGH_SCARCITY (<=3.5k)"
        elif capacity <= 6500:
            score = 85.0  # Alta escasez (Plaza de la Música)
            label = "HIGH_SCARCITY (3.5k - 6.5k)"
        elif capacity <= 15000:
            score = 70.0  # Escasez moderada (Forja, Anfiteatro VM)
            label = "MODERATE_SCARCITY (6.5k - 15k)"
        else:
            score = 45.0  # Capacidad masiva (Kempes)
            label = "LOW_SCARCITY (>15k)"

        return {
            "score": score,
            "estimated_capacity": capacity,
            "scarcity_label": label
        }

    def calculate_price_score(self, price: Optional[float]) -> Dict[str, Any]:
        """Calcula el Score de Atractivo de Precio (P) - 10%.

        Ratio contra la mediana histórica de mercado.
        """
        if not price or price <= 0:
            return {"score": 75.0, "ratio": 1.0, "label": "NORMAL_ESTIMATED"}

        ratio = price / MEDIAN_MARKET_PRICE_ARS
        if ratio <= 0.80:
            score = 95.0
            label = "VERY_ATTRACTIVE (<= 80% mediana)"
        elif ratio <= 0.95:
            score = 85.0
            label = "ATTRACTIVE (80-95% mediana)"
        elif ratio <= 1.05:
            score = 75.0
            label = "MARKET_STANDARD (95-105% mediana)"
        elif ratio <= 1.20:
            score = 60.0
            label = "ABOVE_AVERAGE (105-120% mediana)"
        else:
            score = 45.0
            label = "EXPENSIVE (>120% mediana)"

        return {
            "score": score,
            "ratio": round(ratio, 2),
            "nominal_price": price,
            "label": label
        }

    def calculate_date_score(self, event_date_str: Optional[str]) -> Dict[str, Any]:
        """Calcula el Score de Calidad de Fecha (D) - 10%.

        Fines de semana y vísperas tienen mayor tracción en cuarteto.
        """
        if not event_date_str:
            return {"score": 85.0, "day_name": "WEEKEND_ASSUMED"}

        try:
            # Soportar formatos YYYY-MM-DD o ISO
            dt_str = event_date_str.split("T")[0]
            dt = datetime.strptime(dt_str, "%Y-%m-%d")
            weekday = dt.weekday()  # 0: Lunes, 4: Viernes, 5: Sábado, 6: Domingo

            day_names = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
            day_name = day_names[weekday]

            if weekday == 5:  # Sábado
                score = 100.0
            elif weekday == 4:  # Viernes
                score = 95.0
            elif weekday == 6:  # Domingo (especial vísperas / matiné)
                score = 85.0
            elif weekday == 3:  # Jueves
                score = 75.0
            else:  # Lunes a Miércoles
                score = 55.0

            return {"score": score, "day_name": day_name, "date": dt_str}
        except Exception:
            return {"score": 80.0, "day_name": "UNKNOWN"}

    def calculate_data_confidence(self, total_observations: int) -> Dict[str, Any]:
        """Calcula la Confianza de Datos: Confidence = 1 - e^(-n/10) - Escala 0-100."""
        n = max(0, total_observations)
        raw_confidence = 1.0 - math.exp(-n / 10.0)
        confidence_pct = round(raw_confidence * 100.0, 1)

        if n >= 10:
            level = "HIGH"
        elif n >= 4:
            level = "MEDIUM"
        else:
            level = "LOW"

        return {
            "score": confidence_pct,
            "level": level,
            "sample_size": n
        }

    async def calculate_sold_out_forecast(
        self,
        event_name: str,
        city: Optional[str] = None,
        venue: Optional[str] = None,
        price: Optional[float] = None,
        event_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Calcula el pronóstico completo de Sold-Out Score y Data Confidence (Ticket Intelligence V1)."""
        # 1. Calcular los 5 factores
        artist_res = await self.calculate_artist_score(event_name)
        A = artist_res["score"]

        local_res = await self.calculate_local_score(event_name, city, artist_baseline=A)
        L = local_res["score"]

        venue_res = await self.calculate_venue_score(venue, city)
        V = venue_res["score"]

        price_res = self.calculate_price_score(price)
        P = price_res["score"]

        date_res = self.calculate_date_score(event_date)
        D = date_res["score"]

        # 2. Fórmula Ponderada del Plan Maestro
        total_score = (
            (WEIGHT_ARTIST * A) +
            (WEIGHT_LOCAL * L) +
            (WEIGHT_VENUE * V) +
            (WEIGHT_PRICE * P) +
            (WEIGHT_DATE * D)
        )
        total_score = round(max(0.0, min(100.0, total_score)), 1)

        # 3. Confianza
        total_obs = artist_res["observations"] + local_res["observations"]
        confidence_res = self.calculate_data_confidence(total_obs)

        # 4. Clasificación y Recomendación
        if total_score >= 85.0:
            classification = "HIGH PRIORITY"
            risk_label = "[RIESGO EXTREMO] Agotamiento Inminente"
            recommendation = "Prioridad máxima. Pre-configurar navegador y comprar en los primeros minutos tras apertura."
        elif total_score >= 70.0:
            classification = "PRIORITY"
            risk_label = "[ALTA DEMANDA] Probable Sold-Out"
            recommendation = "Alta prioridad. Monitorear apertura y asegurar compra en las primeras horas."
        elif total_score >= 55.0:
            classification = "WATCH"
            risk_label = "[MONITOREO ESTANDAR] Demanda Sostenida"
            recommendation = "Demanda sostenida. Monitorear disponibilidad regular."
        else:
            classification = "IGNORE"
            risk_label = "[DEMANDA MODERADA] Disponibilidad Regular"
            recommendation = "Disponibilidad estándar garantizada sin urgencia operativa."

        # Tiempo estimado hasta sold-out
        avg_hours = artist_res.get("avg_hours", 24.0)
        if V >= 90.0:  # Venue chico acelera
            avg_hours = max(1.0, avg_hours * 0.75)

        return {
            "event_name": event_name,
            "sold_out_score": total_score,
            "confidence": confidence_res["level"],
            "confidence_score": confidence_res["score"],
            "classification": classification,
            "risk_label": risk_label,
            "recommendation": recommendation,
            "expected_time_to_sold_out_hours": round(avg_hours, 1),
            "urgency_level": artist_res.get("speed", "MODERATE"),
            "factors": {
                "artist_history_score": A,
                "local_performance_score": L,
                "venue_scarcity_score": V,
                "price_attractiveness_score": P,
                "date_quality_score": D,
            },
            "weights": {
                "artist": WEIGHT_ARTIST,
                "local": WEIGHT_LOCAL,
                "venue": WEIGHT_VENUE,
                "price": WEIGHT_PRICE,
                "date": WEIGHT_DATE,
            },
            "sample_size": total_obs,
            # Compatibilidad retroactiva
            "sold_out_probability_pct": total_score,
            "historical_observations_count": total_obs
        }

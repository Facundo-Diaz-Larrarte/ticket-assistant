import pytest
from pathlib import Path
from app.storage.sqlite import IntelligenceDatabase
from app.analytics.intelligence import TicketIntelligenceEngine

@pytest.mark.asyncio
async def test_intelligence_forecast_high_demand():
    db_path = Path("data/test_intel.db")
    if db_path.exists():
        db_path.unlink()

    db = IntelligenceDatabase(db_path)
    await db.init_db()
    
    engine = TicketIntelligenceEngine(db)
    
    # 1. Probar predicción para Desakta2 en Río Cuarto
    forecast = await engine.calculate_sold_out_forecast(
        event_name="Desakta2 - Rio Cuarto",
        city="Rio Cuarto",
        venue="Opus Costanera"
    )

    assert forecast["sold_out_probability_pct"] >= 90.0
    assert "RIESGO EXTREMO" in forecast["risk_label"]
    assert forecast["expected_time_to_sold_out_hours"] <= 5.0

    # 2. Registrar evento como Sold-out y verificar actualización
    await db.record_snapshot(
        event_id="test_desakta2_1",
        provider="eden",
        name="Desakta2 - Rio Cuarto",
        city="Rio Cuarto",
        venue="Opus Costanera",
        status="SOLD_OUT",
        available_shows=0
    )

    stats = await db.get_artist_stats("Desakta2")
    assert stats["total_events"] == 1
    assert stats["sold_out_events"] == 1

    if db_path.exists():
        db_path.unlink()

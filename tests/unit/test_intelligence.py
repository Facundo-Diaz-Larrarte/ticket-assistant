import pytest
from pathlib import Path
from app.storage.sqlite import IntelligenceDatabase
from app.analytics.intelligence import TicketIntelligenceEngine

@pytest.mark.asyncio
async def test_intelligence_forecast_v1():
    db_path = Path("data/test_intel.db")
    if db_path.exists():
        try:
            db_path.unlink()
        except Exception:
            pass

    db = IntelligenceDatabase(db_path)
    await db.init_db()
    
    engine = TicketIntelligenceEngine(db)
    
    # 1. Probar predicción para DesaKTa2 en Río Cuarto (Opus Costanera)
    forecast = await engine.calculate_sold_out_forecast(
        event_name="DesaKTa2 - Rio Cuarto",
        city="Rio Cuarto",
        venue="Opus Costanera",
        price=11000.0,
        event_date="2026-08-15"
    )

    assert forecast["sold_out_score"] >= 85.0
    assert forecast["classification"] == "HIGH PRIORITY"
    assert "RIESGO EXTREMO" in forecast["risk_label"]
    assert forecast["expected_time_to_sold_out_hours"] <= 5.0
    assert "factors" in forecast
    assert forecast["factors"]["artist_history_score"] >= 85.0
    assert forecast["factors"]["venue_scarcity_score"] >= 90.0

    # 2. Registrar evento como Sold-out y verificar actualización de estadísticas
    await db.record_snapshot(
        event_id="test_desakta2_1",
        provider="eden",
        name="DesaKTa2 - Rio Cuarto",
        city="Rio Cuarto",
        venue="Opus Costanera",
        status="SOLD_OUT",
        available_shows=0
    )

    stats = await db.get_artist_stats("DesaKTa2")
    assert stats["total_events"] == 1
    assert stats["sold_out_events"] == 1

    if db_path.exists():
        try:
            db_path.unlink()
        except Exception:
            pass

import sys
import yaml
import asyncio
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Asegurar root en sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich.console import Console
from app.storage.sqlite import IntelligenceDatabase

console = Console()

async def seed_history():
    yaml_path = Path("config/historical_events.yaml")
    if not yaml_path.exists():
        console.print("[red]No se encontró el archivo config/historical_events.yaml[/red]")
        return

    with open(yaml_path, "r", encoding="utf-8") as f:
        events = yaml.safe_load(f) or []

    db = IntelligenceDatabase()
    await db.init_db()

    console.print(f"[cyan]Precargando {len(events)} eventos históricos en la base de datos de Ticket Intelligence...[/cyan]")

    for ev in events:
        artist = ev.get("artist")
        event_name = ev.get("event_name", artist)
        city = ev.get("city", "Rio Cuarto")
        venue = ev.get("venue", "Opus Costanera")
        sold_out = ev.get("sold_out", True)
        hours = float(ev.get("hours_to_sold_out", 12.0))
        show_date_str = ev.get("show_date", "2026-01-01")

        event_id = f"seed_{artist.lower().replace(' ', '_')}_{show_date_str}"
        now = datetime.now(timezone.utc)
        first_seen = now - timedelta(days=30)
        sold_out_at = first_seen + timedelta(hours=hours) if sold_out else None
        time_to_sold_out = hours * 3600.0 if sold_out else None
        status = "SOLD_OUT" if sold_out else "AVAILABLE"

        import aiosqlite
        async with aiosqlite.connect(db.db_path) as conn:
            await conn.execute("""
                INSERT OR REPLACE INTO events_history (
                    id, provider, external_id, name, artist, city, venue, 
                    first_seen_at, sold_out_at, time_to_sold_out_seconds, 
                    total_snapshots, final_status
                )
                VALUES (?, 'eden_seed', ?, ?, ?, ?, ?, ?, ?, ?, 10, ?)
            """, (
                event_id, event_id, event_name, artist, city, venue,
                first_seen.isoformat(),
                sold_out_at.isoformat() if sold_out_at else None,
                time_to_sold_out,
                status
            ))
            await conn.commit()

        console.print(f"  [green][OK][/green] [bold]{artist}[/bold] ({city} - {venue}): {'SOLD_OUT en ' + str(hours) + 'hs' if sold_out else 'Disponible'}")

    console.print("\n[bold green]Historial precargado exitosamente! El bot ya tiene memoria estadistica.[/bold green]")

if __name__ == "__main__":
    asyncio.run(seed_history())

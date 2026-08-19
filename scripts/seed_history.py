import sys
import yaml
import asyncio
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Asegurar root en sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich.console import Console
from rich.table import Table
from app.storage.sqlite import IntelligenceDatabase

console = Console()

async def seed_history(yaml_file: str = "historical_events_curated_2025_2026.yaml"):
    yaml_path = Path(yaml_file)
    if not yaml_path.exists():
        # Fallback a config/historical_events.yaml
        yaml_path = Path("config/historical_events.yaml")
        if not yaml_path.exists():
            console.print(f"[red]No se encontró {yaml_file} ni config/historical_events.yaml[/red]")
            return

    console.print(f"[bold cyan]Cargando dataset desde: {yaml_path.name}...[/bold cyan]\n")

    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    db = IntelligenceDatabase()
    await db.init_db()

    venues = data.get("venues", [])
    artists = data.get("artists", [])
    events = data.get("events", [])

    # 1. Cargar Venues
    for v in venues:
        await db.upsert_venue(
            venue_id=v["id"],
            name=v["name"],
            city=v.get("city", "Cordoba"),
            province=v.get("province", "Cordoba"),
            capacity_estimate=v.get("capacity_estimate"),
            venue_type=v.get("venue_type", "BOLICHE")
        )
    console.print(f"  [green][OK][/green] {len(venues)} Venues registrados.")

    # 2. Cargar Artistas
    for a in artists:
        await db.upsert_artist(
            artist_id=a["id"],
            name=a["name"],
            genre=a.get("genre", "CUARTETO"),
            default_sold_out_rate=a.get("default_sold_out_rate") or 0.85
        )
    console.print(f"  [green][OK][/green] {len(artists)} Artistas registrados.")

    # 3. Cargar Eventos y Resultados Reales
    table = Table(title="Eventos Curados Registrados en DB", show_header=True, header_style="bold magenta")
    table.add_column("Artista / Show", style="white")
    table.add_column("Lugar / Ciudad", style="cyan")
    table.add_column("Fecha", style="yellow")
    table.add_column("Precio", justify="right", style="green")
    table.add_column("Sold Out", justify="center", style="bold red")
    table.add_column("Backtest", justify="center", style="blue")

    for ev in events:
        artist_id = ev.get("artist_id")
        venue_id = ev.get("venue_id")
        event_name = ev.get("event_name", artist_id)
        event_date = str(ev.get("event_date") or "")
        sale_start_at = ev.get("sale_start_at")
        sold_out = ev.get("sold_out")
        hours = ev.get("hours_to_sold_out")
        price = ev.get("nominal_price")
        exclude_backtest = ev.get("exclude_from_backtest", False)
        event_quality = ev.get("event_quality", "CONFIRMED")
        source_event_url = ev.get("source_event_url")
        sold_out_quality = ev.get("sold_out_quality", "CONFIRMED")

        date_clean = event_date.replace("-", "") if event_date else "nodate"
        event_id = f"seed_{artist_id}_{venue_id}_{date_clean}"

        # Timestamps
        if sale_start_at:
            sale_start_str = str(sale_start_at)
        elif event_date:
            try:
                dt = datetime.strptime(event_date, "%Y-%m-%d")
                sale_start_str = (dt - timedelta(days=15)).isoformat()
            except Exception:
                sale_start_str = None
        else:
            sale_start_str = None

        sold_out_at = str(ev.get("sold_out_at")) if ev.get("sold_out_at") else None
        time_to_sold_out_sec = (float(hours) * 3600.0) if hours is not None else None
        final_status = "SOLD_OUT" if sold_out is True else "AVAILABLE" if sold_out is False else "HELD"

        # Registrar en la tabla relacional de Eventos
        await db.upsert_event(
            event_id=event_id,
            provider="eden_seed",
            name=event_name,
            artist_id=artist_id,
            venue_id=venue_id,
            external_id=event_id,
            sale_start_at=sale_start_str,
            first_seen_at=sale_start_str,
            sold_out_at=sold_out_at,
            event_date=event_date,
            nominal_price=price,
            final_status=final_status,
            exclude_from_backtest=exclude_backtest,
            event_quality=event_quality,
            source_event_url=source_event_url
        )

        # Registrar resultado real (Outcome)
        await db.record_outcome(
            event_id=event_id,
            sold_out=sold_out,
            sold_out_at=sold_out_at,
            time_to_sold_out_seconds=time_to_sold_out_sec,
            final_status=final_status,
            quality=sold_out_quality
        )

        # Compatibilidad con snapshots y events_history
        await db.record_snapshot(
            event_id=event_id,
            provider="eden_seed",
            name=event_name,
            city="Rio Cuarto" if "opus" in (venue_id or "") else "Villa Maria" if "villa_maria" in (venue_id or "") else "Cordoba",
            venue=venue_id,
            status=final_status,
            available_shows=0 if sold_out is True else 1,
            min_price=price,
            max_price=price
        )

        sold_str = "[green]SI[/green]" if sold_out is True else "[red]NO[/red]" if sold_out is False else "[yellow]N/D[/yellow]"
        backtest_str = "[red]EXCLUIDO[/red]" if exclude_backtest else "[green]APTO[/green]"

        table.add_row(
            event_name,
            venue_id,
            event_date or "N/D",
            f"${price:,.0f}" if price else "N/D",
            sold_str,
            backtest_str
        )

    console.print(table)
    console.print(f"\n[bold green][OK] Base de datos actualizada con {len(events)} observaciones históricas del archivo curado.[/bold green]")

if __name__ == "__main__":
    yaml_file = sys.argv[1] if len(sys.argv) > 1 else "historical_events_curated_2025_2026.yaml"
    asyncio.run(seed_history(yaml_file))

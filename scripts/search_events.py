import sys
import asyncio
from pathlib import Path

# Asegurar que el root del proyecto esté en sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich.console import Console
from rich.table import Table
from app.providers.eden.provider import EdenProvider

console = Console()

async def search(query: str):
    eden = EdenProvider()
    try:
        console.print(f"[cyan]Buscando en catálogo de Eden Entradas por:[/cyan] [bold]'{query}'[/bold]...")
        events = await eden.search_events(query)
        
        if not events:
            console.print("[yellow]No se encontraron eventos coincidentes.[/yellow]")
            return

        table = Table(title=f"Resultados para '{query}'")
        table.add_column("Nombre", style="bold white")
        table.add_column("Estado", justify="center")
        table.add_column("Lugar / Ciudad")
        table.add_column("URL")

        for ev in events:
            color = "green" if ev.status == "AVAILABLE" else "red" if ev.status == "SOLD_OUT" else "yellow"
            table.add_row(
                ev.name,
                f"[{color}]{ev.status.value}[/{color}]",
                f"{ev.venue or ''} ({ev.city or ''})",
                ev.url
            )

        console.print(table)
    finally:
        await eden.close()

if __name__ == "__main__":
    q = sys.argv[1] if len(sys.argv) > 1 else ""
    asyncio.run(search(q))

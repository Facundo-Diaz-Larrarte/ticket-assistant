import sys
import asyncio
from pathlib import Path

# Asegurar que el root del proyecto esté en sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich.console import Console
from rich.panel import Panel
from app.providers.eden.provider import EdenProvider

console = Console()

async def inspect(url: str):
    eden = EdenProvider()
    try:
        console.print(f"[cyan]Inspeccionando evento en:[/cyan] {url}")
        event = await eden.get_event(url)
        
        status_color = "green" if event.status == "AVAILABLE" else "red" if event.status == "SOLD_OUT" else "yellow"
        info = (
            f"[bold white]Nombre:[/bold white] {event.name}\n"
            f"[bold white]ID Externo:[/bold white] {event.external_id}\n"
            f"[bold white]Estado:[/bold white] [{status_color}]{event.status.value}[/{status_color}]\n"
            f"[bold white]Lugar:[/bold white] {event.venue or 'N/A'}\n"
            f"[bold white]Ciudad:[/bold white] {event.city or 'N/A'}\n"
            f"[bold white]Dirección:[/bold white] {event.address or 'N/A'}\n"
            f"[bold white]Funciones (Shows):[/bold white] {len(event.shows)}\n"
        )
        if event.shows:
            for s in event.shows:
                info += f"  • Show: {s.name or s.id} (Disponible: {s.available})\n"
                for sec in s.sectors:
                    info += f"    - Sector: {sec.name} | Precio: ${sec.price or 0} (Disponible: {sec.available})\n"

        console.print(Panel(info, title="[bold green]Detalles del Evento[/bold green]", expand=False))

    except Exception as e:
        console.print(f"[bold red]Error durante la inspección:[/bold red] {e}")
    finally:
        await eden.close()

if __name__ == "__main__":
    target_url = sys.argv[1] if len(sys.argv) > 1 else "https://www.edenentradas.ar/event/desakta2-150826"
    asyncio.run(inspect(target_url))

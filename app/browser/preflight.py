import asyncio
import httpx
from rich.console import Console
from rich.table import Table
from app.core.config import load_settings, load_events_config, load_buyer_profiles
from app.providers.eden.provider import EdenProvider
from app.notifications.sound import play_alert_sound

console = Console()

async def run_preflight_checks() -> bool:
    """Ejecuta un diagnóstico completo del sistema antes de iniciar operaciones."""
    table = Table(title="[bold cyan]Ticket Assistant — Preflight Check[/bold cyan]")
    table.add_column("Componente", style="bold white")
    table.add_column("Estado", justify="center")
    table.add_column("Detalle", style="dim")

    all_passed = True
    settings = load_settings()
    events_cfg = load_events_config()
    buyer_profiles = load_buyer_profiles()

    # 1. Internet & Conectividad
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get("https://www.google.com")
            if resp.status_code == 200:
                table.add_row("Conectividad a Internet", "[green]OK[/green]", "Conexión activa")
            else:
                table.add_row("Conectividad a Internet", "[yellow]WARN[/yellow]", f"Status {resp.status_code}")
    except Exception as e:
        table.add_row("Conectividad a Internet", "[red]FAIL[/red]", str(e))
        all_passed = False

    # 2. Acceso a Eden Entradas
    eden = EdenProvider()
    try:
        catalog = await eden.search_events()
        table.add_row("Eden Entradas API", "[green]OK[/green]", f"{len(catalog)} eventos públicos encontrados")
    except Exception as e:
        table.add_row("Eden Entradas API", "[red]FAIL[/red]", str(e))
        all_passed = False
    finally:
        await eden.close()

    # 3. Configuración de Eventos & Watchlist
    watchlist_count = len(events_cfg.watchlist)
    monitored_count = len(events_cfg.monitored_events)
    if watchlist_count > 0 or monitored_count > 0:
        table.add_row("Configuración de Eventos", "[green]OK[/green]", f"{watchlist_count} en watchlist, {monitored_count} URLs directas")
    else:
        table.add_row("Configuración de Eventos", "[yellow]VACÍO[/yellow]", "No hay eventos ni artistas en config/events.yaml")

    # 4. Perfil de Comprador
    if buyer_profiles:
        profile_names = list(buyer_profiles.keys())
        table.add_row("Perfiles de Comprador", "[green]OK[/green]", f"Cargados: {', '.join(profile_names)}")
    else:
        table.add_row("Perfiles de Comprador", "[yellow]OPCIONAL[/yellow]", "Sin buyer_profiles.yaml (se usará carga manual)")

    # 5. Notificaciones de Telegram
    if settings.telegram.enabled:
        table.add_row("Telegram Bot", "[green]HABILITADO[/green]", f"Chat ID: {settings.telegram.chat_id}")
    else:
        table.add_row("Telegram Bot", "[dim]DESHABILITADO[/dim]", "Configurar bot_token y chat_id en settings.yaml si deseas alertas móviles")

    # 6. Alerta Sonora
    if settings.sound.enabled:
        table.add_row("Alerta Sonora PC", "[green]OK[/green]", f"{settings.sound.beep_frequency_hz} Hz")
    else:
        table.add_row("Alerta Sonora PC", "[dim]DESHABILITADO[/dim]", "Desactivado en settings")

    console.print(table)
    return all_passed

if __name__ == "__main__":
    asyncio.run(run_preflight_checks())

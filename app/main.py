import sys
import asyncio
import logging
from rich.logging import RichHandler
from rich.console import Console
from app.core.config import load_settings, load_events_config
from app.monitoring.monitor import UnifiedMonitor
from app.browser.preflight import run_preflight_checks
from app.browser.session import BrowserManager
from app.providers.eden.provider import EdenProvider

# Configurar logging legible
logging.basicConfig(
    level="INFO",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True, show_path=False)]
)
logger = logging.getLogger("ticket_assistant")
console = Console()

async def main():
    if len(sys.argv) < 2:
        console.print("[bold cyan]Ticket Assistant CLI[/bold cyan]")
        console.print("Uso:")
        console.print("  python -m app.main monitor    # Inicia el monitor continuo con la watchlist")
        console.print("  python -m app.main preflight  # Diagnóstico del sistema")
        console.print("  python -m app.main login      # Abre el navegador para iniciar sesión en Eden")
        console.print("  python -m app.main search <artista> # Busca eventos en el catálogo de Eden")
        return

    cmd = sys.argv[1].lower()

    if cmd == "preflight":
        await run_preflight_checks()

    elif cmd == "login":
        profile_name = "facu"
        for i, arg in enumerate(sys.argv):
            if arg in ("--profile", "-p") and i + 1 < len(sys.argv):
                profile_name = sys.argv[i + 1]

        console.print(f"[bold yellow]Abriendo navegador para iniciar sesión en la cuenta: '{profile_name}'...[/bold yellow]")
        console.print("Inicia sesión en Eden Entradas con esta cuenta y luego presiona Enter aquí para guardar la sesión.")
        
        settings = load_settings()
        from app.browser.pool import ParallelWorkerPool
        pool = ParallelWorkerPool(settings.browser)
        manager = pool._get_manager_for_profile(profile_name)
        page = await manager.get_page()
        await page.goto("https://www.edenentradas.ar/")
        
        console.input(f"[bold green]Presiona ENTER aquí cuando hayas terminado de loguear la cuenta '{profile_name}'...[/bold green]")
        await manager.close()
        console.print(f"[bold green]¡Sesión de '{profile_name}' guardada exitosamente en data/profiles/eden_{profile_name}![/bold green]")

    elif cmd == "buy":
        if len(sys.argv) < 3:
            console.print("[red]Uso: python -m app.main buy <URL_EVENTO> [--profiles facu,cuenta2] [--quantity 4][/red]")
            return

        event_url = sys.argv[2]
        profiles = ["facu"]
        quantity = 4

        for i, arg in enumerate(sys.argv):
            if arg in ("--profiles", "-p") and i + 1 < len(sys.argv):
                profiles = [p.strip() for p in sys.argv[i + 1].split(",")]
            elif arg in ("--quantity", "-q") and i + 1 < len(sys.argv):
                quantity = int(sys.argv[i + 1])

        console.print(f"[bold cyan]Disparando compra paralela para {len(profiles)} cuentas en:[/bold cyan] {event_url}")
        settings = load_settings()
        from app.browser.pool import ParallelWorkerPool
        from app.notifications.telegram import TelegramNotifier
        
        notifier = TelegramNotifier(
            bot_token=settings.telegram.bot_token,
            chat_id=settings.telegram.chat_id,
            enabled=settings.telegram.enabled
        )
        pool = ParallelWorkerPool(settings.browser)
        try:
            results = await pool.execute_parallel_purchase(
                event_url=event_url,
                target_profiles=profiles,
                quantity_per_account=quantity,
                dry_run=settings.app.dry_run,
                telegram_notifier=notifier
            )
            console.print("[bold green]Resultados de la compra:[/bold green]")
            for p, state in results.items():
                console.print(f"• Cuenta '{p}': {state.value}")
        finally:
            console.input("\n[bold yellow]Presiona Enter cuando hayas finalizado tus pagos para cerrar los navegadores...[/bold yellow]")
            await pool.close_all()

    elif cmd == "search":
        query = sys.argv[2] if len(sys.argv) > 2 else ""
        eden = EdenProvider()
        try:
            console.print(f"[cyan]Buscando eventos con el término: '{query}'...[/cyan]")
            events = await eden.search_events(query)
            if not events:
                console.print("[yellow]No se encontraron eventos.[/yellow]")
            for ev in events:
                status_color = "green" if ev.status == "AVAILABLE" else "red" if ev.status == "SOLD_OUT" else "yellow"
                console.print(f"• [bold]{ev.name}[/bold] | [{status_color}]{ev.status.value}[/{status_color}] | 📍 {ev.venue or ''} ({ev.city or ''})")
                console.print(f"  🔗 {ev.url}")
        finally:
            await eden.close()

    elif cmd == "monitor":
        settings = load_settings()
        events_cfg = load_events_config()
        console.print("[bold green]Iniciando Ticket Assistant Monitor...[/bold green] (Presiona CTRL+C para detener)")
        monitor = UnifiedMonitor(settings, events_cfg)
        try:
            await monitor.start()
        except KeyboardInterrupt:
            console.print("\n[yellow]Deteniendo monitor...[/yellow]")
        finally:
            await monitor.stop()

    else:
        console.print(f"[red]Comando desconocido: {cmd}[/red]")

if __name__ == "__main__":
    asyncio.run(main())

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
        console.print("  python -m app.main forecast <artista/evento> [--city <ciudad>] [--venue <lugar>] # Diagnóstico de demanda")
        console.print("  python -m app.main backtest   # Evalúa la precisión del modelo contra el historial")
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

    elif cmd == "forecast":
        if len(sys.argv) < 3:
            console.print("[red]Uso: python -m app.main forecast <artista/evento> [--city <ciudad>] [--venue <lugar>] [--price <precio>] [--date <YYYY-MM-DD>][/red]")
            return

        event_query = sys.argv[2]
        city = None
        venue = None
        price = None
        event_date = None

        for i, arg in enumerate(sys.argv):
            if arg in ("--city", "-c") and i + 1 < len(sys.argv):
                city = sys.argv[i + 1]
            elif arg in ("--venue", "-v") and i + 1 < len(sys.argv):
                venue = sys.argv[i + 1]
            elif arg in ("--price", "-p") and i + 1 < len(sys.argv):
                try:
                    price = float(sys.argv[i + 1])
                except ValueError:
                    pass
            elif arg in ("--date", "-d") and i + 1 < len(sys.argv):
                event_date = sys.argv[i + 1]

        from app.storage.sqlite import IntelligenceDatabase
        from app.analytics.intelligence import TicketIntelligenceEngine
        from rich.panel import Panel
        from rich.table import Table

        db = IntelligenceDatabase()
        await db.init_db()
        engine = TicketIntelligenceEngine(db)

        forecast = await engine.calculate_sold_out_forecast(
            event_name=event_query,
            city=city,
            venue=venue,
            price=price,
            event_date=event_date
        )

        factors = forecast["factors"]
        weights = forecast["weights"]

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Factor", style="white")
        table.add_column("Peso", justify="center", style="cyan")
        table.add_column("Score (0-100)", justify="right", style="bold yellow")

        table.add_row("Artist History (A)", f"{int(weights['artist']*100)}%", f"{factors['artist_history_score']:.1f}")
        table.add_row("Local Performance (L)", f"{int(weights['local']*100)}%", f"{factors['local_performance_score']:.1f}")
        table.add_row("Venue Scarcity (V)", f"{int(weights['venue']*100)}%", f"{factors['venue_scarcity_score']:.1f}")
        table.add_row("Price Ratio (P)", f"{int(weights['price']*100)}%", f"{factors['price_attractiveness_score']:.1f}")
        table.add_row("Date Quality (D)", f"{int(weights['date']*100)}%", f"{factors['date_quality_score']:.1f}")

        score_color = "red" if forecast["sold_out_score"] >= 85 else "yellow" if forecast["sold_out_score"] >= 70 else "green"

        summary_text = (
            f"[bold]Evento:[/bold] {event_query}\n"
            f"[bold]Ubicacion:[/bold] {venue or 'No especificado'} ({city or 'General'})\n"
            f"[bold]Sold-Out Score:[/bold] [{score_color} bold]{forecast['sold_out_score']} / 100[/{score_color} bold]\n"
            f"[bold]Data Confidence:[/bold] {forecast['confidence']} (Score: {forecast['confidence_score']}%, Muestra: {forecast['sample_size']} eventos)\n"
            f"[bold]Clasificacion:[/bold] [{score_color}]{forecast['classification']}[/{score_color}]\n"
            f"[bold]Tiempo Estimado de Agotamiento:[/bold] {forecast['expected_time_to_sold_out_hours']} horas\n"
            f"[bold]Recomendacion:[/bold] {forecast['recommendation']}"
        )

        console.print(Panel(summary_text, title="Ticket Intelligence Forecast V1", border_style="cyan"))
        console.print(table)

    elif cmd == "backtest":
        from scripts.backtest import run_backtest
        await run_backtest()

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

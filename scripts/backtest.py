import sys
import asyncio
from pathlib import Path
from typing import Dict, Any, List

# Asegurar root en sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from app.storage.sqlite import IntelligenceDatabase
from app.analytics.intelligence import TicketIntelligenceEngine

console = Console()

async def run_backtest(threshold_high_priority: float = 85.0, threshold_priority: float = 70.0):
    db = IntelligenceDatabase()
    await db.init_db()
    engine = TicketIntelligenceEngine(db)

    events = await db.get_backtest_events()
    if not events:
        console.print("[yellow]No hay eventos válidos con outcomes demostrados para evaluar en backtest.[/yellow]")
        return

    console.print(f"[bold cyan]Iniciando Backtesting de Ticket Intelligence V1 contra {len(events)} eventos históricos confirmados...[/bold cyan]\n")

    results: List[Dict[str, Any]] = []

    tp = 0  # True Positive (Predicho Sold Out y fue Sold Out)
    fp = 0  # False Positive (Predicho Sold Out y NO fue Sold Out)
    tn = 0  # True Negative (Predicho No Sold Out y NO fue Sold Out)
    fn = 0  # False Negative (Predicho No Sold Out y fue Sold Out)

    high_priority_total = 0
    high_priority_correct = 0

    table = Table(title="Resultados del Backtesting (Predicción vs Realidad)", show_header=True, header_style="bold magenta")
    table.add_column("Evento / Show", style="white")
    table.add_column("Lugar / Ciudad", style="cyan")
    table.add_column("Fecha", style="yellow")
    table.add_column("Score V1", justify="right", style="bold yellow")
    table.add_column("Conf.", justify="center", style="dim")
    table.add_column("Predicción", justify="center")
    table.add_column("Realidad", justify="center")
    table.add_column("Diagnóstico", justify="center", style="bold")

    for ev in events:
        event_name = ev["event_name"]
        city = ev["city"]
        venue = ev["venue_name"] or ev["venue_id"]
        price = ev["nominal_price"]
        event_date = ev["event_date"]
        actual_sold_out = bool(ev["sold_out"])

        forecast = await engine.calculate_sold_out_forecast(
            event_name=event_name,
            city=city,
            venue=venue,
            price=price,
            event_date=event_date
        )

        score = forecast["sold_out_score"]
        conf = forecast["confidence"]
        classification = forecast["classification"]

        # Consideramos predicción positiva si el score entra en categoría PRIORITY (>= 70) o HIGH PRIORITY (>= 85)
        predicted_sold_out = score >= threshold_priority

        if classification == "HIGH PRIORITY":
            high_priority_total += 1
            if actual_sold_out:
                high_priority_correct += 1

        if predicted_sold_out and actual_sold_out:
            tp += 1
            diag = "[green]ACIERTO (TP)[/green]"
        elif not predicted_sold_out and not actual_sold_out:
            tn += 1
            diag = "[green]ACIERTO (TN)[/green]"
        elif predicted_sold_out and not actual_sold_out:
            fp += 1
            diag = "[red]FALSO POSITIVO[/red]"
        else:
            fn += 1
            diag = "[red]FALSO NEGATIVO[/red]"

        score_color = "red" if score >= 85 else "yellow" if score >= 70 else "green"
        pred_color = "red" if score >= 85 else "yellow" if score >= 70 else "green"
        real_str = "[green]SOLD OUT[/green]" if actual_sold_out else "[blue]DISPONIBLE[/blue]"

        table.add_row(
            event_name,
            f"{ev['venue_id']} ({city or 'Cba'})",
            event_date or "N/D",
            f"[{score_color}]{score:.1f}[/{score_color}]",
            conf,
            f"[{pred_color}]{classification}[/{pred_color}]",
            real_str,
            diag
        )

    console.print(table)

    # Métricas Globales
    total = len(events)
    accuracy = ((tp + tn) / total) * 100.0 if total > 0 else 0.0
    precision = (tp / (tp + fp)) * 100.0 if (tp + fp) > 0 else 0.0
    recall = (tp / (tp + fn)) * 100.0 if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    hp_precision = (high_priority_correct / high_priority_total) * 100.0 if high_priority_total > 0 else 0.0

    summary_text = (
        f"[bold]Total Eventos Auditados:[/bold] {total}\n"
        f"[bold]Accuracy Global:[/bold] [green bold]{accuracy:.1f}%[/green bold]\n"
        f"[bold]Precision (Priority >= 70):[/bold] [cyan bold]{precision:.1f}%[/cyan bold] ({tp}/{tp+fp})\n"
        f"[bold]Recall (Detección de Sold-outs):[/bold] [cyan bold]{recall:.1f}%[/cyan bold] ({tp}/{tp+fn})\n"
        f"[bold]F1-Score:[/bold] [yellow bold]{f1:.1f}%[/yellow bold]\n"
        f"[bold]Precision HIGH PRIORITY (>= 85):[/bold] [magenta bold]{hp_precision:.1f}%[/magenta bold] ({high_priority_correct}/{high_priority_total} eventos agotados)"
    )

    console.print("\n", Panel(summary_text, title="Métricas de Desempeño - Ticket Intelligence V1", border_style="green"))

if __name__ == "__main__":
    asyncio.run(run_backtest())

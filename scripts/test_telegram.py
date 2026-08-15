import sys
import asyncio
from pathlib import Path

# Asegurar que el root del proyecto esté en sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich.console import Console
from app.core.config import load_settings
from app.notifications.telegram import TelegramNotifier

console = Console()

async def send_test_message():
    settings = load_settings()
    console.print("[cyan]Probando conexión con el Bot de Telegram...[/cyan]")
    
    notifier = TelegramNotifier(
        bot_token=settings.telegram.bot_token,
        chat_id=settings.telegram.chat_id,
        enabled=True
    )
    
    success = await notifier.notify_event_available(
        event_name="Desakta2 en Río Cuarto (PRUEBA DE CONEXIÓN)",
        event_url="https://www.edenentradas.ar/event/desakta2-150826",
        venue="Opus Costanera",
        city="Rio Cuarto",
        is_restock=False,
        buyer_dni="43475555",
        buyer_phone="3585145764",
        buyer_email="facu150102@gmail.com"
    )
    
    if success:
        console.print("[bold green]¡Mensaje de prueba enviado exitosamente a tu Telegram![/bold green]")
    else:
        console.print("[bold red]Fallo al enviar mensaje a Telegram. Verifica que hayas iniciado el chat con el bot (/start).[/bold red]")

if __name__ == "__main__":
    asyncio.run(send_test_message())

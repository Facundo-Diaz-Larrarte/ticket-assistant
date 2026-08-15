import httpx
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class TelegramNotifier:
    """Envía notificaciones push instantáneas a Telegram."""
    
    def __init__(self, bot_token: str, chat_id: str, enabled: bool = True):
        # Limpiar espacios accidentales o comillas
        self.bot_token = str(bot_token or "").strip().strip('"').strip("'")
        self.chat_id = str(chat_id or "").strip().strip('"').strip("'")
        self.enabled = enabled and bool(self.bot_token and self.chat_id)
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

    async def send_message(self, text: str, parse_mode: str = "HTML", link_preview: bool = True) -> bool:
        """Envía un mensaje de texto formateado."""
        if not self.enabled:
            logger.debug(f"[TELEGRAM DISABLED] Mensaje omitido: {text[:50]}...")
            return False

        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(self.api_url, json=payload)
                if resp.status_code == 200:
                    logger.info("Notificación de Telegram enviada exitosamente")
                    return True
                else:
                    logger.error(f"Error enviando a Telegram ({resp.status_code}): {resp.text}")
                    return False
        except Exception as e:
            logger.error(f"Fallo de conexión al enviar mensaje de Telegram: {e}")
            return False

    async def notify_event_available(
        self,
        event_name: str,
        event_url: str,
        venue: Optional[str] = None,
        city: Optional[str] = None,
        is_restock: bool = False,
        buyer_dni: Optional[str] = None,
        buyer_phone: Optional[str] = None,
        buyer_email: Optional[str] = None
    ):
        """Plantilla preformateada para apertura de entradas o remanente con Tap-to-Copy."""
        title = "🚨 <b>¡REMANENTE DISPONIBLE!</b>" if is_restock else "🎟️ <b>¡NUEVAS ENTRADAS HABILITADAS!</b>"
        location = f"\n📍 <b>Lugar:</b> {venue}" if venue else ""
        if city:
            location += f" ({city})"

        quick_data = ""
        if buyer_dni or buyer_phone or buyer_email:
            quick_data = "\n\n📋 <b>Tus datos (toca para copiar rápido):</b>"
            if buyer_dni:
                quick_data += f"\n• DNI: <code>{buyer_dni}</code>"
            if buyer_phone:
                quick_data += f"\n• Teléfono: <code>{buyer_phone}</code>"
            if buyer_email:
                quick_data += f"\n• Email: <code>{buyer_email}</code>"

        msg = (
            f"{title}\n\n"
            f"🎤 <b>Evento:</b> {event_name}{location}\n\n"
            f"⚡ <b>¡Ingresá ahora para comprar!:</b>\n"
            f"{event_url}"
            f"{quick_data}"
        )
        return await self.send_message(msg)

    async def notify_human_checkpoint(self, event_name: str) -> bool:
        """Notificación de que el bot llegó a la pasarela de pago."""
        msg = (
            f"⚠️ <b>ACCIÓN REQUERIDA EN TU PC</b>\n\n"
            f"El bot seleccionó las entradas para <b>{event_name}</b> y está en la pantalla de pago.\n"
            f"Tenés pocos minutos para ingresar tu CVV y autorizar la compra."
        )
        return await self.send_message(msg)

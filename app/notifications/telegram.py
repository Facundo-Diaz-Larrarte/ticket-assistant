import httpx
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Envía notificaciones push instantáneas y enlaces de pago interactivos a Telegram."""

    def __init__(self, bot_token: str, chat_id: str, enabled: bool = True):
        self.bot_token = str(bot_token or "").strip().strip('"').strip("'")
        self.chat_id = str(chat_id or "").strip().strip('"').strip("'")
        self.enabled = enabled and bool(self.bot_token and self.chat_id)
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

    async def send_message(
        self,
        text: str,
        parse_mode: str = "HTML",
        link_preview: bool = True,
        buttons: Optional[List[List[Dict[str, str]]]] = None
    ) -> bool:
        """Envía un mensaje de texto formateado con soporte para botones inline interactivos."""
        if not self.enabled:
            logger.debug(f"[TELEGRAM DISABLED] Mensaje omitido: {text[:50]}...")
            return False

        payload: Dict[str, Any] = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode
        }

        if buttons:
            payload["reply_markup"] = {
                "inline_keyboard": buttons
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
        buyer_email: Optional[str] = None,
        forecast: Optional[dict] = None
    ):
        """Plantilla preformateada para apertura de entradas o remanente con Ticket Intelligence."""
        title = "🚨 <b>¡REMANENTE DISPONIBLE!</b>" if is_restock else "🎟️ <b>¡NUEVAS ENTRADAS HABILITADAS!</b>"
        location = f"\n📍 <b>Lugar:</b> {venue}" if venue else ""
        if city:
            location += f" ({city})"

        intel_section = ""
        if forecast:
            score = forecast.get("sold_out_score", 0)
            risk = forecast.get("risk_label", "")
            est_hours = forecast.get("expected_time_to_sold_out_hours", 0)
            recom = forecast.get("recommendation", "")
            intel_section = (
                f"\n\n📊 <b>Ticket Intelligence™:</b>\n"
                f"• <b>Sold-Out Score:</b> {score}/100 ({risk})\n"
                f"• <b>Tiempo estimado hasta agotarse:</b> ~{est_hours} hs\n"
                f"• 💡 <b>Consejo:</b> {recom}"
            )

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
            f"{intel_section}"
            f"{quick_data}"
        )

        buttons = [
            [{"text": "🎟️ Abrir en Eden / Ticketera", "url": event_url}]
        ]

        return await self.send_message(msg, buttons=buttons)

    async def notify_parallel_carts_ready(
        self,
        event_name: str,
        reserved_accounts: List[Dict[str, Any]]
    ) -> bool:
        """Notifica cuando múltiples carritos en paralelo han bloqueado las entradas y envía botones de pago directo."""
        total_tickets = sum(acc.get("quantity", 4) for acc in reserved_accounts)
        msg = (
            f"🎉 <b>¡CARRITOS RESERVADOS EN PARALELO!</b>\n\n"
            f"🎤 <b>Evento:</b> {event_name}\n"
            f"🎟️ <b>Total de entradas bloqueadas:</b> {total_tickets}\n"
            f"⏳ <b>Tiempo de gracia:</b> Tenés entre 5 y 10 minutos para autorizar los pagos antes de que venza la reserva.\n\n"
            f"👇 <b>Cuentas listas para pagar:</b>\n"
        )

        buttons = []
        for i, acc in enumerate(reserved_accounts, 1):
            p_name = acc.get("profile_name", f"Cuenta {i}")
            dni = acc.get("dni", "N/D")
            qty = acc.get("quantity", 4)
            pay_url = acc.get("payment_url")

            msg += f"• 👤 <b>{p_name.upper()}</b> (DNI: <code>{dni}</code>) - {qty} entradas\n"

            if pay_url:
                buttons.append([{"text": f"💳 Pagar {p_name.upper()} ({qty} tickets)", "url": pay_url}])

        return await self.send_message(msg, buttons=buttons if buttons else None)

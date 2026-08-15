import sys
import logging
import asyncio

logger = logging.getLogger(__name__)

def play_alert_sound(frequency: int = 1000, duration_ms: int = 800):
    """Reproduce un pitido de alerta en la computadora."""
    try:
        if sys.platform == "win32":
            import winsound
            winsound.Beep(frequency, duration_ms)
        else:
            print("\a", end="", flush=True)
    except Exception as e:
        logger.debug(f"No se pudo reproducir sonido: {e}")

async def play_alert_sound_async(frequency: int = 1000, duration_ms: int = 800):
    """Ejecuta la alerta sonora en un hilo separado sin bloquear el loop asíncrono."""
    await asyncio.to_thread(play_alert_sound, frequency, duration_ms)

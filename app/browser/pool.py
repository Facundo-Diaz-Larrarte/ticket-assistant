import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from app.core.config import BrowserSettings, load_buyer_profiles, load_settings
from app.core.models import BuyerProfile
from app.core.enums import BrowserState
from app.browser.session import BrowserManager
from app.browser.automation import EdenCheckoutAssistant
from app.notifications.telegram import TelegramNotifier
from app.notifications.sound import play_alert_sound_async

logger = logging.getLogger(__name__)


class ParallelWorkerPool:
    """Gestiona la ejecución paralela y concurrente de compras en múltiples cuentas de Eden u otras ticketeras."""

    def __init__(self, settings: BrowserSettings):
        self.settings = settings
        self.managers: Dict[str, BrowserManager] = {}

    def _get_manager_for_profile(self, profile_name: str) -> BrowserManager:
        if profile_name not in self.managers:
            profile_dir = Path("data/profiles") / f"eden_{profile_name}"
            custom_settings = self.settings.model_copy()
            custom_settings.user_data_dir = str(profile_dir)
            self.managers[profile_name] = BrowserManager(custom_settings)
        return self.managers[profile_name]

    async def execute_parallel_purchase(
        self,
        event_url: str,
        target_profiles: List[str],
        quantity_per_account: int = 4,
        preferred_sectors: Optional[List[str]] = None,
        dry_run: bool = True,
        telegram_notifier: Optional[TelegramNotifier] = None
    ) -> Dict[str, BrowserState]:
        """Lanza navegadores en paralelo para reservar entradas en múltiples cuentas simultáneamente."""
        all_profiles = load_buyer_profiles()
        sectors = preferred_sectors or []

        tasks = []
        for p_name in target_profiles:
            profile_data = all_profiles.get(p_name)
            if not profile_data:
                logger.warning(f"Perfil '{p_name}' no encontrado en buyer_profiles.yaml. Omitiendo...")
                continue

            tasks.append(self._run_single_worker(
                profile_name=p_name,
                profile_data=profile_data,
                event_url=event_url,
                quantity=quantity_per_account,
                sectors=sectors,
                dry_run=dry_run
            ))

        if not tasks:
            logger.error("No hay perfiles válidos para ejecutar compra en paralelo.")
            return {}

        logger.info(f"🚀 [WORKER POOL] Lanzando {len(tasks)} compras en paralelo en Eden Entradas...")
        results = await asyncio.gather(*tasks, return_exceptions=True)

        output_states: Dict[str, BrowserState] = {}
        reserved_accounts: List[Dict[str, Any]] = []

        for p_name, res in zip(target_profiles, results):
            if isinstance(res, Exception):
                logger.error(f"Worker para '{p_name}' falló con error: {res}")
                output_states[p_name] = BrowserState.FAILED
            else:
                state, pay_url = res
                output_states[p_name] = state
                if state == BrowserState.USER_ACTION_REQUIRED:
                    p_data = all_profiles.get(p_name)
                    reserved_accounts.append({
                        "profile_name": p_name,
                        "dni": p_data.dni if p_data else "N/D",
                        "quantity": quantity_per_account,
                        "payment_url": pay_url
                    })

        # Notificación consolidada a Telegram con enlaces interactivos de pago
        if telegram_notifier and reserved_accounts:
            await telegram_notifier.notify_parallel_carts_ready(
                event_name=event_url,
                reserved_accounts=reserved_accounts
            )

        return output_states

    async def _run_single_worker(
        self,
        profile_name: str,
        profile_data: BuyerProfile,
        event_url: str,
        quantity: int,
        sectors: List[str],
        dry_run: bool
    ) -> tuple:
        """Ejecuta el flujo de compra para una cuenta específica."""
        manager = self._get_manager_for_profile(profile_name)
        page = await manager.get_page()

        assistant = EdenCheckoutAssistant(page=page, dry_run=dry_run)
        logger.info(f"[{profile_name.upper()}] Iniciando checkout para {quantity} entradas...")

        state, payment_url = await assistant.execute_purchase_flow(
            event_url=event_url,
            preferred_sectors=sectors,
            quantity=quantity,
            buyer_profile=profile_data
        )

        if state == BrowserState.USER_ACTION_REQUIRED:
            logger.info(f"✅ [{profile_name.upper()}] ¡Entradas en carrito! Pantalla de pago lista.")

        return state, payment_url

    async def close_all(self):
        for mgr in self.managers.values():
            await mgr.close()
        self.managers.clear()

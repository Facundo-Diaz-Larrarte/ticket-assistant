import asyncio
import logging
from typing import List, Optional
from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError
from app.core.models import BuyerProfile, Event
from app.core.enums import BrowserState
from app.core.exceptions import HumanActionRequiredException
from app.providers.eden import selectors
from app.notifications.sound import play_alert_sound_async

logger = logging.getLogger(__name__)

class EdenCheckoutAssistant:
    """Asistente de compra automática para Eden Entradas."""

    def __init__(self, page: Page, dry_run: bool = True):
        self.page = page
        self.dry_run = dry_run
        self.state = BrowserState.IDLE

    async def execute_purchase_flow(
        self,
        event_url: str,
        preferred_sectors: List[str],
        quantity: int,
        buyer_profile: Optional[BuyerProfile] = None
    ) -> BrowserState:
        """Ejecuta la navegación, selección y carga de datos hasta la pasarela de pago."""
        try:
            self.state = BrowserState.NAVIGATING
            logger.info(f"Navegando a {event_url}...")
            await self.page.goto(event_url, wait_until="domcontentloaded", timeout=15000)

            # 1. Click en Comprar
            await self._click_buy_button()

            # 2. Selección de Sector
            self.state = BrowserState.SELECTING
            await self._select_preferred_sector(preferred_sectors)

            # 3. Selección de Cantidad
            await self._select_quantity(quantity)

            # 4. Continuar al checkout
            await self._click_continue()

            # 5. Rellenar datos del comprador si aparecen
            self.state = BrowserState.CHECKOUT
            if buyer_profile:
                await self._fill_buyer_data(buyer_profile)

            # 6. Intentar capturar URL de pasarela o checkout actual
            payment_url = self.page.url
            try:
                # Si hay iframe o link de MercadoPago/pasarela
                mp_link = self.page.locator('a[href*="mercadopago"], a[href*="checkout"], iframe[src*="mercadopago"]').first
                if await mp_link.is_visible(timeout=1000):
                    href = await mp_link.get_attribute("href") or await mp_link.get_attribute("src")
                    if href:
                        payment_url = href
            except Exception:
                pass

            # 7. Human Checkpoint (Detención de seguridad)
            self.state = BrowserState.USER_ACTION_REQUIRED
            logger.info("==================================================")
            logger.info("🛑 HUMAN CHECKPOINT ALCANZADO: PANTALLA DE PAGO LISTA")
            logger.info(f"URL de Pago / Carrito: {payment_url}")
            logger.info("==================================================")

            # Alarma sonora
            for _ in range(2):
                await play_alert_sound_async(frequency=1200, duration_ms=500)
                await asyncio.sleep(0.2)

            return BrowserState.USER_ACTION_REQUIRED, payment_url

        except HumanActionRequiredException:
            self.state = BrowserState.USER_ACTION_REQUIRED
            return self.state, self.page.url
        except Exception as e:
            logger.error(f"Error en flujo de compra asistida: {e}", exc_info=True)
            self.state = BrowserState.FAILED
            return self.state, None

    async def _click_buy_button(self):
        """Intenta hacer click en el botón de comprar usando la lista de selectores tolerantes."""
        for selector in selectors.BUY_BUTTONS:
            try:
                elem = self.page.locator(selector).first
                if await elem.is_visible(timeout=1500):
                    logger.info(f"Haciendo click en botón de compra: {selector}")
                    await elem.click()
                    return
            except Exception:
                continue
        logger.warning("No se encontró botón explícito de compra, continuando en la vista actual...")

    async def _select_preferred_sector(self, preferred_sectors: List[str]):
        """Selecciona el primer sector disponible de la lista, o permite elección manual si está vacío."""
        if not preferred_sectors:
            logger.info("Sectores configurados como vacíos: esperando selección manual de sector/VIP por el usuario.")
            return

        for sector_name in preferred_sectors:
            try:
                # Buscar elemento que contenga el nombre del sector
                locator = self.page.locator(f'text="{sector_name}"').first
                if await locator.is_visible(timeout=1000):
                    logger.info(f"Seleccionando sector preferido: {sector_name}")
                    await locator.click()
                    return
            except Exception:
                continue
        logger.info("No se encontró sector prioritario por texto exacto, continuando...")

    async def _select_quantity(self, quantity: int):
        """Selecciona la cantidad de entradas."""
        try:
            # Buscar selects o botones de incremento (+)
            plus_btn = self.page.locator('button:has-text("+"), .quantity-plus, .btn-plus').first
            if await plus_btn.is_visible(timeout=1000):
                # Hacer clicks adicionales para la cantidad requerida (si arranca en 1)
                for _ in range(quantity - 1):
                    await plus_btn.click()
                    await asyncio.sleep(0.1)
        except Exception as e:
            logger.debug(f"Selector de cantidad no requerido o no encontrado: {e}")

    async def _click_continue(self):
        """Avanza al siguiente paso."""
        for selector in selectors.CONTINUE_BUTTONS:
            try:
                btn = self.page.locator(selector).first
                if await btn.is_visible(timeout=1500):
                    await btn.click()
                    return
            except Exception:
                continue

    async def _fill_buyer_data(self, profile: BuyerProfile):
        """Rellena de forma segura los campos de contacto del comprador."""
        mapping = {
            "first_name": profile.first_name,
            "last_name": profile.last_name,
            "dni": profile.dni,
            "email": profile.email,
            "phone": profile.phone
        }
        for field, value in mapping.items():
            for selector in selectors.BUYER_FORM.get(field, []):
                try:
                    input_elem = self.page.locator(selector).first
                    if await input_elem.is_visible(timeout=500):
                        await input_elem.fill(value)
                        break
                except Exception:
                    continue

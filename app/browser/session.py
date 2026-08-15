import os
import logging
from pathlib import Path
from typing import Optional
from playwright.async_api import async_playwright, BrowserContext, Page, Playwright
from app.core.config import BrowserSettings

logger = logging.getLogger(__name__)

class BrowserManager:
    """Gestiona el ciclo de vida del navegador Chromium con perfil persistente (sesión guardada)."""

    def __init__(self, settings: BrowserSettings):
        self.settings = settings
        self.user_data_dir = Path(settings.user_data_dir)
        self._playwright: Optional[Playwright] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

    async def get_or_create_context(self) -> BrowserContext:
        """Inicia o reutiliza el navegador con el perfil persistente de usuario."""
        if self._context is None:
            self.user_data_dir.mkdir(parents=True, exist_ok=True)
            self._playwright = await async_playwright().start()
            
            logger.info(f"Iniciando Chromium (Headed={not self.settings.headless}) con perfil en {self.user_data_dir}")
            self._context = await self._playwright.chromium.launch_persistent_context(
                user_data_dir=str(self.user_data_dir),
                headless=self.settings.headless,
                slow_mo=self.settings.slow_mo_ms,
                viewport={"width": 1280, "height": 800},
                args=[
                    "--no-sandbox",
                    "--disable-blink-features=AutomationControlled",
                    "--start-maximized"
                ]
            )
        return self._context

    async def get_page(self) -> Page:
        """Obtiene una página activa lista para interactuar."""
        context = await self.get_or_create_context()
        if not context.pages:
            self._page = await context.new_page()
        else:
            self._page = context.pages[0]
        return self._page

    async def close(self):
        """Cierra el contexto de navegación."""
        if self._context:
            await self._context.close()
            self._context = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        logger.info("Navegador cerrado.")

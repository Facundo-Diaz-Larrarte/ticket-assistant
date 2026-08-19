import httpx
import logging
from typing import List, Optional
from app.providers.base import TicketProvider
from app.core.models import Event
from app.core.enums import EventStatus
from app.core.exceptions import EventNotFoundError, BlockedError, RateLimitError
from app.providers.eden.parser import EdenParser
from app.providers.eden.scanner import EdenScanner

logger = logging.getLogger(__name__)

class EdenProvider(TicketProvider):
    """Adaptador concreto para Eden Entradas."""
    
    def __init__(self, client: Optional[httpx.AsyncClient] = None):
        self._client = client or httpx.AsyncClient(
            timeout=10.0,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"Windows"',
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Upgrade-Insecure-Requests": "1"
            },
            follow_redirects=True
        )
        self.scanner = EdenScanner(self._client)

    @property
    def name(self) -> str:
        return "eden"

    @property
    def domains(self) -> List[str]:
        return ["edenentradas.ar", "www.edenentradas.ar"]

    async def get_event(self, url_or_id: str) -> Event:
        """Descarga e interpreta la página del evento de Eden."""
        url = url_or_id if url_or_id.startswith("http") else f"https://www.edenentradas.ar/event/{url_or_id}"
        
        try:
            response = await self._client.get(url)
            
            if response.status_code == 404:
                raise EventNotFoundError(f"Evento no encontrado en {url}")
            elif response.status_code == 429:
                raise RateLimitError("Rate limit excedido en Eden Entradas (HTTP 429)")
            elif response.status_code in (403, 405):
                logger.warning(f"Desafío o bloqueo anti-bot detectado en Eden (HTTP {response.status_code}). Pausando peticiones...")
                raise BlockedError(f"Acceso temporalmente restringido por protección CloudFront/WAF (HTTP {response.status_code})")
            elif response.status_code != 200:
                logger.warning(f"Respuesta no estándar de Eden: {response.status_code}")

            return EdenParser.parse_event_html(response.text, url)
            
        except httpx.RequestError as e:
            logger.error(f"Error de red al consultar {url}: {e}")
            raise

    async def get_event_status(self, url_or_id: str) -> EventStatus:
        """Obtiene el estado de disponibilidad del evento con mínima latencia."""
        event = await self.get_event(url_or_id)
        return event.status

    async def search_events(self, query: str = "") -> List[Event]:
        """Busca eventos en el catálogo de Eden."""
        return await self.scanner.search_catalog(query)

    async def close(self):
        await self._client.aclose()

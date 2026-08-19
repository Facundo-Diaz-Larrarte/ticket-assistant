import re
import httpx
import logging
from bs4 import BeautifulSoup
from typing import List, Optional, Set
from app.core.models import Event, WatchlistItem
from app.core.enums import EventStatus

logger = logging.getLogger(__name__)

class EdenScanner:
    """Escanea el catálogo y la home de Eden Entradas para descubrir eventos nuevos y coincidencias con la Watchlist."""
    
    BASE_URL = "https://www.edenentradas.ar"

    def __init__(self, client: httpx.AsyncClient):
        self.client = client

    async def fetch_home_events(self) -> List[Event]:
        """Extrae todos los eventos listados en la página principal de Eden Entradas."""
        try:
            resp = await self.client.get(self.BASE_URL)
            if resp.status_code != 200:
                logger.warning(f"No se pudo cargar la home de Eden (status {resp.status_code})")
                return []

            soup = BeautifulSoup(resp.text, "lxml")
            events: List[Event] = []
            seen_slugs: Set[str] = set()

            # Buscar todos los enlaces que apunten a /event/
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if "/event/" in href:
                    # Normalizar URL
                    slug = href.split("/event/")[-1].strip("/").strip()
                    if not slug or slug in seen_slugs:
                        continue
                    seen_slugs.add(slug)
                    
                    full_url = f"{self.BASE_URL}/event/{slug}"
                    
                    # Extraer título del enlace o contenido interno
                    title_elem = a.find(class_=re.compile(r"item_title|title|name", re.I))
                    if title_elem:
                        name = title_elem.get_text(strip=True)
                    else:
                        img = a.find("img")
                        if img and img.get("alt"):
                            name = img.get("alt").replace("Banner ", "").strip()
                        else:
                            name = slug.replace("-", " ").title()

                    events.append(Event(
                        id=f"eden_{slug}",
                        provider="eden",
                        external_id=slug,
                        name=name,
                        url=full_url,
                        slug=slug,
                        status=EventStatus.UNKNOWN
                    ))

            logger.info(f"[EDEN SCANNER] Se extrajeron {len(events)} eventos públicos de la home de Eden.")
            return events

        except Exception as e:
            logger.error(f"Error parseando eventos de la home de Eden: {e}")
            return []

    async def search_catalog(self, query: str = "") -> List[Event]:
        """Busca eventos en la página principal filtrando por término."""
        all_events = await self.fetch_home_events()
        if not query:
            return all_events

        q_lower = query.lower()
        return [ev for ev in all_events if q_lower in ev.name.lower() or q_lower in (ev.slug or "").lower()]

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Normaliza texto quitando tildes y mayúsculas para comparaciones precisas."""
        if not text:
            return ""
        replacements = (
            ("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"),
            ("Á", "a"), ("É", "e"), ("Í", "i"), ("Ó", "o"), ("Ú", "u")
        )
        t = text.lower()
        for orig, dest in replacements:
            t = t.replace(orig, dest)
        return t

    async def scan_watchlist(self, watchlist: List[WatchlistItem]) -> List[Event]:
        """Compara la lista de vigilancia (Watchlist) contra los eventos activos de la home con filtro estricto de ciudad."""
        matched_events: List[Event] = []
        catalog_events = await self.fetch_home_events()
        
        for item in watchlist:
            for ev in catalog_events:
                name_norm = self._normalize_text(ev.name)
                slug_norm = self._normalize_text(ev.slug or "")
                
                # Comprobar si coincide alguna palabra clave de la banda
                matches_band = any(
                    self._normalize_text(kw) in name_norm or self._normalize_text(kw) in slug_norm
                    for kw in item.keywords
                )

                if not matches_band:
                    continue

                # Cargar detalles profundos del evento descubierto (Ciudad real, Venue, Shows, Sectores)
                detailed_event = ev
                try:
                    resp = await self.client.get(ev.url)
                    if resp.status_code == 200:
                        from app.providers.eden.parser import EdenParser
                        detailed_event = EdenParser.parse_event_html(resp.text, ev.url)
                except Exception as e:
                    logger.debug(f"Error obteniendo detalles profundos de {ev.url}: {e}")

                # Filtro ESTRICTO de ciudad si está especificada en la watchlist
                if item.city:
                    target_city_norm = self._normalize_text(item.city) # ej: "rio cuarto"
                    
                    event_locations_combined = self._normalize_text(
                        f"{detailed_event.city or ''} {detailed_event.venue or ''} {detailed_event.address or ''} {detailed_event.name} {detailed_event.slug or ''}"
                    )
                    
                    # Si el evento no contiene "rio cuarto" (ej: es en Forja o Plaza de la Música en Córdoba Capital), se descarta
                    if target_city_norm not in event_locations_combined:
                        logger.debug(f"Descartando {detailed_event.name} porque no es en {item.city}")
                        continue

                matched_events.append(detailed_event)

        return matched_events

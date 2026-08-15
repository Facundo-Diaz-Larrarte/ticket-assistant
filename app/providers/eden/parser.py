import re
import json
import hashlib
import logging
from typing import Optional, Dict, Any, List
from bs4 import BeautifulSoup
from app.core.models import Event, Show, Sector
from app.core.enums import EventStatus

logger = logging.getLogger(__name__)

BOOTSTRAP_REGEX = re.compile(r'App\.bootstrapData\(({.+?})\);', re.DOTALL)

class EdenParser:
    """Parser especializado y ultra rápido para Eden Entradas."""
    
    @staticmethod
    def extract_bootstrap_json(html_content: str) -> Optional[Dict[str, Any]]:
        """Extrae el payload estructurado JSON incrustado en el HTML."""
        match = BOOTSTRAP_REGEX.search(html_content)
        if match:
            raw_json = match.group(1)
            try:
                return json.loads(raw_json)
            except json.JSONDecodeError as e:
                logger.warning(f"Error decodificando App.bootstrapData: {e}")
        return None

    @staticmethod
    def parse_status_from_raw(data: Dict[str, Any]) -> EventStatus:
        """Determina el estado a partir de los campos estructurados de Eden."""
        # Estado en nivel raíz de data
        sales_status = str(data.get("salesStatus", "")).upper()
        if sales_status == "SOLD_OUT":
            return EventStatus.SOLD_OUT
        elif sales_status in ("AVAILABLE", "ON_SALE"):
            return EventStatus.AVAILABLE
        elif sales_status in ("NOT_STARTED", "UPCOMING", "PRÓXIMAMENTE"):
            return EventStatus.NOT_STARTED
        elif sales_status == "FINISHED":
            return EventStatus.FINISHED

        # Evaluar funciones (shows)
        shows = data.get("shows", [])
        if shows:
            any_available = any(show.get("available", False) for show in shows)
            if any_available:
                return EventStatus.AVAILABLE
            else:
                return EventStatus.SOLD_OUT

        return EventStatus.UNKNOWN

    @classmethod
    def parse_event_html(cls, html_content: str, url: str) -> Event:
        """Parsea un HTML completo de Eden Entradas a un modelo Event."""
        payload_hash = hashlib.sha256(html_content.encode("utf-8")).hexdigest()
        bootstrap = cls.extract_bootstrap_json(html_content)
        
        if bootstrap and "model" in bootstrap and "data" in bootstrap["model"]:
            event_data = bootstrap["model"]["data"]
            return cls._parse_from_bootstrap_data(event_data, url, payload_hash)

        # Fallback a BeautifulSoup si no viniera bootstrapData
        return cls._parse_with_beautifulsoup(html_content, url, payload_hash)

    @classmethod
    def _parse_from_bootstrap_data(cls, data: Dict[str, Any], url: str, payload_hash: str) -> Event:
        ext_id = str(data.get("id", ""))
        name = data.get("name", "Evento Eden")
        slug = data.get("link") or data.get("tag")
        
        venue_data = data.get("venue", {}) or {}
        venue_name = venue_data.get("name")
        address_data = venue_data.get("address", {}) or {}
        city = address_data.get("city")
        address = address_data.get("formatReadableSimple") or address_data.get("street")
        image_url = data.get("thumbImage")

        status = cls.parse_status_from_raw(data)

        shows_list: List[Show] = []
        for s in data.get("shows", []):
            show_id = str(s.get("id", ""))
            show_name = s.get("name")
            show_avail = bool(s.get("available", False))
            
            sectors_list: List[Sector] = []
            for sec in s.get("sectors", []):
                sectors_list.append(Sector(
                    id=str(sec.get("id", "")),
                    name=sec.get("name", "General"),
                    price=sec.get("price"),
                    service_charge=sec.get("serviceCharge"),
                    available=sec.get("available", show_avail),
                    raw_data=sec
                ))

            shows_list.append(Show(
                id=show_id,
                name=show_name,
                available=show_avail,
                sectors=sectors_list
            ))

        return Event(
            id=f"eden_{ext_id}",
            provider="eden",
            external_id=ext_id,
            name=name,
            url=url,
            slug=slug,
            city=city,
            venue=venue_name,
            address=address,
            status=status,
            shows=shows_list,
            image_url=image_url,
            raw_payload_hash=payload_hash
        )

    @classmethod
    def _parse_with_beautifulsoup(cls, html_content: str, url: str, payload_hash: str) -> Event:
        soup = BeautifulSoup(html_content, "lxml")
        title_elem = soup.find("h1") or soup.find("title")
        title = title_elem.get_text(strip=True) if title_elem else "Evento Eden"
        
        # Detectar textos clave en la página
        text_lower = soup.get_text().lower()
        if "agotad" in text_lower or "sold out" in text_lower:
            status = EventStatus.SOLD_OUT
        elif "comprar" in text_lower:
            status = EventStatus.AVAILABLE
        elif "próximamente" in text_lower or "proximamente" in text_lower:
            status = EventStatus.UPCOMING
        else:
            status = EventStatus.UNKNOWN

        return Event(
            id=f"eden_html_{hashlib.md5(url.encode()).hexdigest()[:8]}",
            provider="eden",
            external_id="unknown",
            name=title,
            url=url,
            status=status,
            raw_payload_hash=payload_hash
        )

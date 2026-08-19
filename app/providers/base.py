from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from app.core.models import Event
from app.core.enums import EventStatus


class TicketProvider(ABC):
    """Interfaz abstracta que deben implementar todos los adaptadores de ticketeras

    (Eden, Autoentrada, Passline, AllAccess, Deportick, etc.).
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Nombre identificador único del proveedor (ej: 'eden', 'autoentrada')."""
        pass

    @property
    def domains(self) -> List[str]:
        """Lista de dominios que maneja este provider (ej: ['edenentradas.ar'])."""
        return []

    @abstractmethod
    async def get_event(self, url_or_id: str) -> Event:
        """Obtiene y normaliza los detalles completos de un evento."""
        pass

    @abstractmethod
    async def get_event_status(self, url_or_id: str) -> EventStatus:
        """Obtiene el estado de disponibilidad actual con mínima latencia."""
        pass

    @abstractmethod
    async def search_events(self, query: str = "") -> List[Event]:
        """Busca eventos en el catálogo público por término o artista."""
        pass

    async def health_check(self) -> Dict[str, Any]:
        """Verifica la conectividad y estado de salud de la plataforma."""
        try:
            events = await self.search_events("")
            return {
                "provider": self.name,
                "status": "HEALTHY" if len(events) >= 0 else "DEGRADED",
                "message": "Conectividad correcta."
            }
        except Exception as e:
            return {
                "provider": self.name,
                "status": "BROKEN",
                "error": str(e)
            }

    @abstractmethod
    async def close(self):
        """Cierra conexiones activas del cliente HTTP."""
        pass

from abc import ABC, abstractmethod
from typing import List, Optional
from app.core.models import Event, Show, Sector, AvailabilitySnapshot
from app.core.enums import EventStatus

class TicketProvider(ABC):
    """Interfaz abstracta que deben implementar todos los adaptadores de ticketeras (Eden, Ticketek, AllAccess, etc.)."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Nombre identificador del proveedor (ej: 'eden', 'ticketek')."""
        pass

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

    @abstractmethod
    async def close(self):
        """Cierra conexiones activas del cliente HTTP."""
        pass

import logging
from typing import Dict, List, Optional
from urllib.parse import urlparse
from app.providers.base import TicketProvider
from app.providers.eden.provider import EdenProvider

logger = logging.getLogger(__name__)


class ProviderRegistry:
    """Registro central y despachador dinámico de adaptadores de ticketeras."""

    def __init__(self):
        self._providers: Dict[str, TicketProvider] = {}
        self._domain_map: Dict[str, str] = {}
        self._register_default_providers()

    def _register_default_providers(self):
        """Registra los adaptadores disponibles por defecto."""
        eden = EdenProvider()
        self.register(eden)

    def register(self, provider: TicketProvider):
        """Registra una nueva ticketera en el sistema."""
        self._providers[provider.name.lower()] = provider
        for domain in provider.domains:
            self._domain_map[domain.lower()] = provider.name.lower()
        logger.info(f"TicketProvider registrado: '{provider.name}' (dominios: {provider.domains})")

    def get(self, name: str) -> Optional[TicketProvider]:
        """Obtiene un provider por su nombre identificador (ej: 'eden')."""
        return self._providers.get(name.lower())

    def get_by_url(self, url: str) -> Optional[TicketProvider]:
        """Resuelve el provider adecuado analizando el dominio de la URL del evento."""
        try:
            parsed = urlparse(url)
            netloc = parsed.netloc.lower()
            # Quitar puerto si existe
            if ":" in netloc:
                netloc = netloc.split(":")[0]

            provider_name = self._domain_map.get(netloc)
            if not provider_name:
                # Probar sin subdominio www
                clean_domain = netloc.replace("www.", "")
                provider_name = self._domain_map.get(clean_domain)

            if provider_name:
                return self._providers.get(provider_name)
        except Exception as e:
            logger.debug(f"Error resolviendo provider para URL {url}: {e}")

        # Fallback a Eden si no se puede resolver
        return self.get("eden")

    def list_providers(self) -> List[str]:
        """Retorna la lista de ticketeras registradas."""
        return list(self._providers.keys())

    async def close_all(self):
        """Cierra conexiones de todas las ticketeras registradas."""
        for name, p in self._providers.items():
            try:
                await p.close()
            except Exception as e:
                logger.debug(f"Error cerrando provider {name}: {e}")

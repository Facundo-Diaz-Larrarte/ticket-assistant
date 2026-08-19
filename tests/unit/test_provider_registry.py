import pytest
from app.providers.registry import ProviderRegistry
from app.providers.eden.provider import EdenProvider
from app.core.enums import EventStatus

def test_provider_registry_initialization():
    registry = ProviderRegistry()
    assert "eden" in registry.list_providers()
    
    eden = registry.get("eden")
    assert eden is not None
    assert eden.name == "eden"
    assert "edenentradas.ar" in eden.domains

def test_provider_registry_get_by_url():
    registry = ProviderRegistry()
    
    # URL de Eden
    provider = registry.get_by_url("https://www.edenentradas.ar/event/desakta2-150826")
    assert provider is not None
    assert provider.name == "eden"

    # URL sin www
    provider_no_www = registry.get_by_url("https://edenentradas.ar/event/q-lokura")
    assert provider_no_www is not None
    assert provider_no_www.name == "eden"

@pytest.mark.asyncio
async def test_provider_contract_methods():
    registry = ProviderRegistry()
    eden = registry.get("eden")
    
    # Test health_check method
    health = await eden.health_check()
    assert "provider" in health
    assert health["provider"] == "eden"
    assert health["status"] in ("HEALTHY", "DEGRADED", "BROKEN")

    await registry.close_all()

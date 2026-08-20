from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from app.core.enums import EventStatus, SalePhaseType, ValueSource

class Sector(BaseModel):
    """Sector o tipo de entrada dentro de un evento."""
    id: Optional[str] = None
    name: str
    price: Optional[float] = None
    service_charge: Optional[float] = None
    currency: str = "ARS"
    available: bool = True
    raw_data: Optional[Dict[str, Any]] = None

class Show(BaseModel):
    """Función o fecha específica dentro de un evento."""
    id: Optional[str] = None
    name: Optional[str] = None
    start_date: Optional[datetime] = None
    available: bool = False
    sectors: List[Sector] = Field(default_factory=list)

class Event(BaseModel):
    """Modelo normalizado y unificado de un evento de cualquier ticketera."""
    id: Optional[str] = None
    provider: str
    external_id: str
    name: str
    url: str
    slug: Optional[str] = None
    city: Optional[str] = None
    venue: Optional[str] = None
    address: Optional[str] = None
    status: EventStatus = EventStatus.UNKNOWN
    max_tickets_per_user: Optional[int] = None
    shows: List[Show] = Field(default_factory=list)
    image_url: Optional[str] = None
    raw_payload_hash: Optional[str] = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AvailabilitySnapshot(BaseModel):
    """Instantánea de disponibilidad para historial y análisis."""
    event_id: str
    provider: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: EventStatus
    available_shows_count: int = 0
    available_sectors: List[str] = Field(default_factory=list)
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    source: ValueSource = ValueSource.OBSERVED

class BuyerProfile(BaseModel):
    """Datos personales para rellenado automático seguro."""
    first_name: str
    last_name: str
    dni: str
    email: str
    phone: str
    address: Optional[str] = None
    postal_code: Optional[str] = None
    city: Optional[str] = None
    province: Optional[str] = None

class WatchlistItem(BaseModel):
    """Definición de un artista o evento a vigilar en el catálogo."""
    name: str
    provider: str = "eden"
    keywords: List[str]
    city: Optional[str] = None
    venue: Optional[str] = None
    quantity: int = 2
    sectors: List[str] = Field(default_factory=list)
    buyer_profile: str = "default"
    auto_buy: bool = True
    notify_telegram: bool = True

class MonitoredEventConfig(BaseModel):
    """Configuración para una URL específica conocida."""
    url: str
    provider: str = "eden"
    quantity: int = 2
    sectors: List[str] = Field(default_factory=list)
    buyer_profile: str = "default"
    auto_buy: bool = True
    notify_telegram: bool = True

# Alias for backwards compatibility
NormalizedEvent = Event


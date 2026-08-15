from enum import Enum

class EventStatus(str, Enum):
    """Estado de disponibilidad de un evento o función."""
    NOT_FOUND = "NOT_FOUND"          # No existe en el catálogo o retorna 404
    UPCOMING = "UPCOMING"            # Anunciado, pero la venta aún no empezó
    NOT_STARTED = "NOT_STARTED"      # Página creada, venta cerrada
    AVAILABLE = "AVAILABLE"          # Entradas disponibles para compra
    LOW_AVAILABILITY = "LOW_AVAILABILITY" # Pocas entradas restantes
    SOLD_OUT = "SOLD_OUT"            # Todas las entradas agotadas
    FINISHED = "FINISHED"            # Evento finalizado o fecha pasada
    BLOCKED = "BLOCKED"              # Bloqueo o detección de anti-bot
    ERROR = "ERROR"                  # Error al consultar el proveedor
    UNKNOWN = "UNKNOWN"              # Estado irreconocible

class BrowserState(str, Enum):
    """Estado del asistente de navegación."""
    IDLE = "IDLE"
    READY = "READY"
    NAVIGATING = "NAVIGATING"
    SELECTING = "SELECTING"
    CHECKOUT = "CHECKOUT"
    USER_ACTION_REQUIRED = "USER_ACTION_REQUIRED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class SalePhaseType(str, Enum):
    """Tipo de fase de venta."""
    PRESALE = "PRESALE"
    GENERAL = "GENERAL"
    VIP = "VIP"
    OTHER = "OTHER"

class ValueSource(str, Enum):
    """Origen de un dato para auditoría e inteligencia."""
    OBSERVED = "OBSERVED"
    PUBLISHED = "PUBLISHED"
    ESTIMATED = "ESTIMATED"
    INFERRED = "INFERRED"

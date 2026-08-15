class TicketAssistantException(Exception):
    """Excepción base para el asistente de compras y monitoreo."""
    pass

class ProviderException(TicketAssistantException):
    """Error al comunicarse o parsear datos de una ticketera."""
    pass

class EventNotFoundError(ProviderException):
    """El evento no existe en la ticketera (404 o eliminado)."""
    pass

class RateLimitError(ProviderException):
    """El proveedor respondió con HTTP 429 Too Many Requests."""
    pass

class BlockedError(ProviderException):
    """El proveedor bloqueó la consulta o presentó un desafío/CAPTCHA."""
    pass

class SessionExpiredError(TicketAssistantException):
    """La sesión de usuario en el navegador ha expirado."""
    pass

class HumanActionRequiredException(TicketAssistantException):
    """El bot llegó a un punto donde se requiere intervención humana obligatoria."""
    pass

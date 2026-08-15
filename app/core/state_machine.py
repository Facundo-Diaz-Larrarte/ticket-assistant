import logging
from typing import Set, Tuple
from app.core.enums import EventStatus
from app.core.events import event_bus

logger = logging.getLogger(__name__)

# Transiciones de estado válidas
VALID_TRANSITIONS: Set[Tuple[EventStatus, EventStatus]] = {
    (EventStatus.UNKNOWN, EventStatus.NOT_FOUND),
    (EventStatus.UNKNOWN, EventStatus.UPCOMING),
    (EventStatus.UNKNOWN, EventStatus.NOT_STARTED),
    (EventStatus.UNKNOWN, EventStatus.AVAILABLE),
    (EventStatus.UNKNOWN, EventStatus.SOLD_OUT),
    
    (EventStatus.NOT_FOUND, EventStatus.UPCOMING),
    (EventStatus.NOT_FOUND, EventStatus.AVAILABLE),
    (EventStatus.NOT_FOUND, EventStatus.NOT_STARTED),
    
    (EventStatus.NOT_STARTED, EventStatus.AVAILABLE),
    (EventStatus.NOT_STARTED, EventStatus.SOLD_OUT),
    
    (EventStatus.UPCOMING, EventStatus.AVAILABLE),
    (EventStatus.UPCOMING, EventStatus.SOLD_OUT),
    
    (EventStatus.AVAILABLE, EventStatus.LOW_AVAILABILITY),
    (EventStatus.AVAILABLE, EventStatus.SOLD_OUT),
    (EventStatus.AVAILABLE, EventStatus.FINISHED),
    
    (EventStatus.LOW_AVAILABILITY, EventStatus.AVAILABLE),
    (EventStatus.LOW_AVAILABILITY, EventStatus.SOLD_OUT),
    
    (EventStatus.SOLD_OUT, EventStatus.AVAILABLE),      # Restock
    (EventStatus.SOLD_OUT, EventStatus.LOW_AVAILABILITY), # Restock parcial
    (EventStatus.SOLD_OUT, EventStatus.FINISHED),
    
    (EventStatus.BLOCKED, EventStatus.AVAILABLE),
    (EventStatus.BLOCKED, EventStatus.SOLD_OUT),
    (EventStatus.ERROR, EventStatus.AVAILABLE),
    (EventStatus.ERROR, EventStatus.SOLD_OUT),
}

class EventStateMachine:
    """Gestiona el estado de un evento y emite eventos en transiciones clave."""
    def __init__(self, event_id: str, initial_status: EventStatus = EventStatus.UNKNOWN):
        self.event_id = event_id
        self.current_status = initial_status

    async def transition_to(self, new_status: EventStatus, event_data: dict = None) -> bool:
        if new_status == self.current_status:
            return False

        old_status = self.current_status
        self.current_status = new_status
        logger.info(f"[{self.event_id}] Transition: {old_status.value} -> {new_status.value}")

        # Disparadores clave
        if new_status == EventStatus.AVAILABLE:
            if old_status in (EventStatus.NOT_FOUND, EventStatus.UPCOMING, EventStatus.NOT_STARTED):
                await event_bus.emit("EVENT_RELEASED_NOW", event_id=self.event_id, data=event_data, from_status=old_status)
            elif old_status == EventStatus.SOLD_OUT:
                await event_bus.emit("EVENT_RESTOCKED", event_id=self.event_id, data=event_data, from_status=old_status)
            else:
                await event_bus.emit("EVENT_AVAILABLE", event_id=self.event_id, data=event_data, from_status=old_status)
                
        elif new_status == EventStatus.SOLD_OUT:
            await event_bus.emit("EVENT_SOLD_OUT", event_id=self.event_id, data=event_data, from_status=old_status)

        return True

import asyncio
import inspect
import logging
from typing import Callable, Dict, List, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

@dataclass
class InternalEvent:
    name: str
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

class EventBus:
    """Bus asíncrono desacoplado para comunicar el Monitor, Telegram y Browser."""
    def __init__(self):
        self._subscribers: Dict[str, List[Callable[[InternalEvent], Any]]] = {}

    def subscribe(self, event_name: str, handler: Callable[[InternalEvent], Any]):
        if event_name not in self._subscribers:
            self._subscribers[event_name] = []
        self._subscribers[event_name].append(handler)
        logger.debug(f"Subscribed handler to event: {event_name}")

    async def emit(self, event_name: str, **data):
        event = InternalEvent(name=event_name, data=data)
        handlers = self._subscribers.get(event_name, [])
        logger.info(f"[EVENT BUS] Emitting '{event_name}' to {len(handlers)} handler(s)")
        
        for handler in handlers:
            try:
                if inspect.iscoroutinefunction(handler):
                    asyncio.create_task(handler(event))
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"Error executing handler for event {event_name}: {e}", exc_info=True)

# Instancia global del bus
event_bus = EventBus()

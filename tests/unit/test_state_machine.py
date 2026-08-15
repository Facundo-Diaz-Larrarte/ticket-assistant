import pytest
from app.core.enums import EventStatus
from app.core.state_machine import EventStateMachine
from app.core.events import event_bus

@pytest.mark.asyncio
async def test_state_machine_transition_and_events():
    events_received = []

    def on_event_released(event):
        events_received.append(event.name)

    event_bus.subscribe("EVENT_RELEASED_NOW", on_event_released)
    
    sm = EventStateMachine("test_event_1", EventStatus.NOT_STARTED)
    
    # Transición a disponible (lanzamiento)
    changed = await sm.transition_to(EventStatus.AVAILABLE)
    assert changed is True
    assert sm.current_status == EventStatus.AVAILABLE
    assert "EVENT_RELEASED_NOW" in events_received

    # Transición a Sold Out
    changed = await sm.transition_to(EventStatus.SOLD_OUT)
    assert changed is True
    assert sm.current_status == EventStatus.SOLD_OUT

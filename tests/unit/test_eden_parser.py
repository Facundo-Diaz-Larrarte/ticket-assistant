import pytest
from pathlib import Path
from app.providers.eden.parser import EdenParser
from app.core.enums import EventStatus

def test_parse_eden_html_fixture():
    fixture_path = Path("tests/fixtures/eden/desakta2_event.html")
    assert fixture_path.exists()
    
    html_content = fixture_path.read_text(encoding="utf-8")
    event = EdenParser.parse_event_html(html_content, "https://www.edenentradas.ar/event/desakta2-150826")

    assert event.name == "Desakta2 - Rio Cuarto"
    assert event.external_id == "17716"
    assert event.provider == "eden"
    assert event.status == EventStatus.SOLD_OUT
    assert event.venue == "Opus Costanera"
    assert event.city == "Rio Cuarto"
    assert len(event.shows) == 1
    assert event.shows[0].available is False
    assert len(event.shows[0].sectors) == 1
    assert event.shows[0].sectors[0].name == "Campo General"
    assert event.shows[0].sectors[0].price == 15000

def test_parse_available_status():
    raw_data = {
        "salesStatus": "AVAILABLE",
        "shows": [{"available": True}]
    }
    status = EdenParser.parse_status_from_raw(raw_data)
    assert status == EventStatus.AVAILABLE

def test_parse_not_started_status():
    raw_data = {
        "salesStatus": "NOT_STARTED",
        "shows": []
    }
    status = EdenParser.parse_status_from_raw(raw_data)
    assert status == EventStatus.NOT_STARTED

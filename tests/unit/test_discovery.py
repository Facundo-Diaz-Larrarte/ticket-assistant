import pytest
from app.core.models import WatchlistItem, Event
from app.providers.eden.scanner import EdenScanner

def test_text_normalization():
    assert EdenScanner._normalize_text("Río Cuarto") == "rio cuarto"
    assert EdenScanner._normalize_text("Córdoba") == "cordoba"
    assert EdenScanner._normalize_text("Q' LOKURA") == "q' lokura"

from app.core.config import load_settings, load_events_config, load_buyer_profiles

def test_load_settings():
    settings = load_settings("config/settings.yaml")
    assert settings.app.name == "Ticket Assistant"
    assert settings.monitoring.default_interval_seconds == 5.0
    assert settings.sound.enabled is True

def test_load_events_config():
    events_cfg = load_events_config("config/events.yaml")
    assert len(events_cfg.watchlist) >= 1
    assert "Desakta2" in events_cfg.watchlist[0].keywords
    assert len(events_cfg.monitored_events) >= 1

def test_load_buyer_profiles_example():
    profiles = load_buyer_profiles("config/buyer_profiles.example.yaml")
    assert "default" in profiles
    assert profiles["default"].first_name == "Facundo"

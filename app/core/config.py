import os
import yaml
from pathlib import Path
from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from app.core.models import WatchlistItem, MonitoredEventConfig, BuyerProfile

# Cargar variables de entorno desde .env si existe
load_dotenv()

class AppSettings(BaseModel):
    name: str = "Ticket Assistant"
    environment: str = "development"
    dry_run: bool = True

class MonitoringSettings(BaseModel):
    default_interval_seconds: float = 5.0
    launch_window_interval_seconds: float = 1.5
    adaptive_backoff_max_seconds: float = 60.0
    max_consecutive_errors: int = 5

class TelegramSettings(BaseModel):
    enabled: bool = True
    bot_token: str = Field(default_factory=lambda: os.getenv("TELEGRAM_BOT_TOKEN", ""))
    chat_id: str = Field(default_factory=lambda: os.getenv("TELEGRAM_CHAT_ID", ""))

class BrowserSettings(BaseModel):
    headless: bool = False
    slow_mo_ms: int = 50
    user_data_dir: str = "data/profiles/eden"
    timeout_ms: int = 15000

class SoundSettings(BaseModel):
    enabled: bool = True
    beep_frequency_hz: int = 1000
    beep_duration_ms: int = 800

class GlobalSettings(BaseModel):
    app: AppSettings = Field(default_factory=AppSettings)
    monitoring: MonitoringSettings = Field(default_factory=MonitoringSettings)
    telegram: TelegramSettings = Field(default_factory=TelegramSettings)
    browser: BrowserSettings = Field(default_factory=BrowserSettings)
    sound: SoundSettings = Field(default_factory=SoundSettings)

class EventsFileConfig(BaseModel):
    watchlist: List[WatchlistItem] = Field(default_factory=list)
    monitored_events: List[MonitoredEventConfig] = Field(default_factory=list)

def load_settings(config_path: str = "config/settings.yaml") -> GlobalSettings:
    path = Path(config_path)
    if not path.exists():
        return GlobalSettings()
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return GlobalSettings(**data)

def load_events_config(config_path: str = "config/events.yaml") -> EventsFileConfig:
    path = Path(config_path)
    if not path.exists():
        return EventsFileConfig()
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return EventsFileConfig(**data)

def load_buyer_profiles(config_path: str = "config/buyer_profiles.yaml") -> Dict[str, BuyerProfile]:
    path = Path(config_path)
    if not path.exists():
        # Fallback to example if exists
        example_path = Path("config/buyer_profiles.example.yaml")
        if example_path.exists():
            path = example_path
        else:
            return {}
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return {k: BuyerProfile(**v) for k, v in data.items()}

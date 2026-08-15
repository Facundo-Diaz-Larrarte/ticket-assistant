from app.providers.eden.provider import EdenProvider
from app.notifications.telegram import TelegramNotifier
from app.notifications.sound import play_alert_sound_async
from app.storage.sqlite import IntelligenceDatabase
from app.analytics.intelligence import TicketIntelligenceEngine

logger = logging.getLogger(__name__)

class UnifiedMonitor:
    """Monitor unificado para escaneo de Watchlist de artistas y vigilancia de URLs directas con Ticket Intelligence."""

    def __init__(self, settings: GlobalSettings, events_config: EventsFileConfig):
        self.settings = settings
        self.events_config = events_config
        self.eden_provider = EdenProvider()
        self.db = IntelligenceDatabase()
        self.intelligence = TicketIntelligenceEngine(self.db)
        self.telegram = TelegramNotifier(
            bot_token=settings.telegram.bot_token,
            chat_id=settings.telegram.chat_id,
            enabled=settings.telegram.enabled
        )
        
        self.state_machines: Dict[str, EventStateMachine] = {}
        self.known_watchlist_matches: Dict[str, EventStatus] = {}
        self.is_running = False

    def get_or_create_state_machine(self, event_id: str) -> EventStateMachine:
        if event_id not in self.state_machines:
            self.state_machines[event_id] = EventStateMachine(event_id)
        return self.state_machines[event_id]

    async def start(self):
        """Inicia el ciclo principal de monitoreo e inicializa la base de datos histórica."""
        await self.db.init_db()
        self.is_running = True
        logger.info("Iniciando ciclo de monitoreo continuo de Ticket Assistant con Ticket Intelligence™...")
        interval = self.settings.monitoring.default_interval_seconds

        while self.is_running:
            try:
                # 1. Monitoreo de URLs directas
                for item in self.events_config.monitored_events:
                    await self._check_direct_event(item)

                # 2. Escaneo de Watchlist en catálogo de Eden
                if self.events_config.watchlist:
                    await self._check_watchlist()

            except Exception as e:
                logger.error(f"Error en iteración de monitoreo: {e}", exc_info=True)

            await asyncio.sleep(interval)

    async def stop(self):
        self.is_running = False
        await self.eden_provider.close()
        logger.info("Monitoreo detenido.")

    async def _check_direct_event(self, config: MonitoredEventConfig):
        try:
            event = await self.eden_provider.get_event(config.url)
            
            # Registrar observación histórica en base de datos
            await self.db.record_snapshot(
                event_id=event.id or config.url,
                provider=event.provider,
                name=event.name,
                city=event.city,
                venue=event.venue,
                status=event.status.value,
                available_shows=len([s for s in event.shows if s.available])
            )

            sm = self.get_or_create_state_machine(event.id or config.url)
            old_status = sm.current_status
            changed = await sm.transition_to(event.status, event.model_dump())
            
            if changed and event.status == EventStatus.AVAILABLE:
                is_restock = (old_status == EventStatus.SOLD_OUT)
                logger.info(f"¡ENTRADAS DISPONIBLES! Evento: {event.name} ({event.url})")
                
                # Calcular pronóstico de demanda
                forecast = await self.intelligence.calculate_sold_out_forecast(
                    event_name=event.name,
                    city=event.city,
                    venue=event.venue
                )

                # Alerta sonora
                if self.settings.sound.enabled:
                    asyncio.create_task(play_alert_sound_async())

                # Alerta Telegram
                if config.notify_telegram:
                    from app.core.config import load_buyer_profiles
                    profiles = load_buyer_profiles()
                    profile = profiles.get(config.buyer_profile)
                    
                    await self.telegram.notify_event_available(
                        event_name=event.name,
                        event_url=event.url,
                        venue=event.venue,
                        city=event.city,
                        is_restock=is_restock,
                        buyer_dni=profile.dni if profile else None,
                        buyer_phone=profile.phone if profile else None,
                        buyer_email=profile.email if profile else None,
                        forecast=forecast
                    )

        except Exception as e:
            logger.debug(f"Error consultando evento directo {config.url}: {e}")

    async def _check_watchlist(self):
        try:
            matches = await self.eden_provider.scanner.scan_watchlist(self.events_config.watchlist)
            for event in matches:
                # Registrar observación histórica en base de datos
                await self.db.record_snapshot(
                    event_id=event.id or event.url,
                    provider=event.provider,
                    name=event.name,
                    city=event.city,
                    venue=event.venue,
                    status=event.status.value,
                    available_shows=len([s for s in event.shows if s.available]) if event.shows else 0
                )

                last_status = self.known_watchlist_matches.get(event.id)
                self.known_watchlist_matches[event.id] = event.status

                # Si es un evento nuevo que no conocíamos o cambió a disponible
                if last_status is None or (last_status != EventStatus.AVAILABLE and event.status == EventStatus.AVAILABLE):
                    logger.info(f"[WATCHLIST MATCH] ¡Evento detectado!: {event.name} - Estado: {event.status.value}")
                    
                    if event.status == EventStatus.AVAILABLE:
                        # Calcular pronóstico de demanda
                        forecast = await self.intelligence.calculate_sold_out_forecast(
                            event_name=event.name,
                            city=event.city,
                            venue=event.venue
                        )

                        if self.settings.sound.enabled:
                            asyncio.create_task(play_alert_sound_async())

                        from app.core.config import load_buyer_profiles
                        profiles = load_buyer_profiles()
                        profile = profiles.get("default") or (list(profiles.values())[0] if profiles else None)

                        await self.telegram.notify_event_available(
                            event_name=event.name,
                            event_url=event.url,
                            venue=event.venue,
                            city=event.city,
                            is_restock=False,
                            buyer_dni=profile.dni if profile else None,
                            buyer_phone=profile.phone if profile else None,
                            buyer_email=profile.email if profile else None,
                            forecast=forecast
                        )
        except Exception as e:
            logger.debug(f"Error escaneando watchlist: {e}")

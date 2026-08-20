import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, Any

from app.core.config import GlobalSettings, EventsFileConfig
from app.core.models import MonitoredEventConfig, Event
from app.core.enums import EventStatus
from app.core.state_machine import EventStateMachine
from app.providers.registry import ProviderRegistry
from app.notifications.telegram import TelegramNotifier
from app.notifications.sound import play_alert_sound_async
from app.storage.sqlite import IntelligenceDatabase
from app.analytics.intelligence import TicketIntelligenceEngine

logger = logging.getLogger(__name__)


class UnifiedMonitor:
    """Monitor unificado multi-ticketera con Ticket Intelligence V1:

    - Despacho dinámico de providers vía ProviderRegistry.
    - Escaneo de Watchlist y vigilancia de URLs directas.
    - Congelamiento pre-apertura de predicciones (Prediction Freezing).
    - Polling Adaptativo según ventana temporal de apertura.
    - Cierre de ciclo de aprendizaje automático (Outcome Tracking).
    """

    def __init__(self, settings: GlobalSettings, events_config: EventsFileConfig):
        self.settings = settings
        self.events_config = events_config
        self.providers = ProviderRegistry()
        self.db = IntelligenceDatabase()
        self.intelligence = TicketIntelligenceEngine(self.db)
        self.telegram = TelegramNotifier(
            bot_token=settings.telegram.bot_token,
            chat_id=settings.telegram.chat_id,
            enabled=settings.telegram.enabled
        )

        self.state_machines: Dict[str, EventStateMachine] = {}
        self.known_watchlist_matches: Dict[str, EventStatus] = {}
        self.frozen_predictions: Dict[str, Dict[str, Any]] = {}
        self.sale_start_times: Dict[str, datetime] = {}
        self.is_running = False

    def get_or_create_state_machine(self, event_id: str) -> EventStateMachine:
        if event_id not in self.state_machines:
            self.state_machines[event_id] = EventStateMachine(event_id)
        return self.state_machines[event_id]

    async def _freeze_prediction_if_needed(self, event: Event) -> Dict[str, Any]:
        """Calcula y congela la predicción pre-apertura en la base de datos si aún no se registró."""
        event_id = event.id or event.url
        if event_id in self.frozen_predictions:
            return self.frozen_predictions[event_id]

        now = datetime.now(timezone.utc)
        now_str = now.isoformat()

        # Asegurar que el evento esté registrado en la tabla events
        await self.db.upsert_event(
            event_id=event_id,
            provider=event.provider,
            name=event.name,
            external_id=event.id,
            first_seen_at=now_str,
            final_status=event.status.value
        )

        forecast = await self.intelligence.calculate_sold_out_forecast(
            event_name=event.name,
            city=event.city,
            venue=event.venue
        )

        prediction_id = f"pred_{event_id.replace('/', '_')}_{int(now.timestamp())}"
        factors = forecast.get("factors", {})

        await self.db.save_prediction(
            prediction_id=prediction_id,
            event_id=event_id,
            calculated_at=now_str,
            sold_out_score=forecast["sold_out_score"],
            confidence=forecast["confidence"],
            artist_score=factors.get("artist_history_score"),
            local_score=factors.get("local_performance_score"),
            venue_score=factors.get("venue_scarcity_score"),
            price_score=factors.get("price_attractiveness_score"),
            date_score=factors.get("date_quality_score"),
            model_version="v1.0"
        )

        self.frozen_predictions[event_id] = forecast
        logger.info(
            f"[PREDICTION FROZEN] Evento: {event.name} | Score: {forecast['sold_out_score']} "
            f"({forecast['classification']}) | Conf: {forecast['confidence']}"
        )
        return forecast

    def _calculate_adaptive_sleep(self) -> float:
        """Determina la frecuencia de polling adaptativo según cercanía de aperturas y estado en vivo."""
        now = datetime.now(timezone.utc)
        min_sleep = self.settings.monitoring.default_interval_seconds

        # Si algún evento está en vivo disponible, polling agresivo
        for sm in self.state_machines.values():
            if sm.current_status == EventStatus.AVAILABLE:
                return self.settings.monitoring.launch_window_interval_seconds or 3.0

        # Si conocemos fechas de apertura próximas
        for sale_time in self.sale_start_times.values():
            time_to_sale = (sale_time - now).total_seconds()
            if 0 <= time_to_sale <= 1800:  # Menos de 30 min para abrir
                return min(min_sleep, 5.0)
            elif 1800 < time_to_sale <= 86400:  # Entre 30 min y 24hs
                return min(min_sleep, 30.0)

        return min_sleep

    async def start(self):
        """Inicia el ciclo principal de monitoreo continuo."""
        await self.db.init_db()
        self.is_running = True
        logger.info("Iniciando ciclo de monitoreo continuo con Ticket Intelligence V1...")

        current_interval = self.settings.monitoring.default_interval_seconds
        while self.is_running:
            try:
                # 1. Monitoreo de URLs directas
                for item in self.events_config.monitored_events:
                    await self._check_direct_event(item)

                # 2. Escaneo de Watchlist en catálogo de Eden
                if self.events_config.watchlist:
                    await self._check_watchlist()

                # Polling adaptativo dinámico
                current_interval = self._calculate_adaptive_sleep()

            except Exception as e:
                logger.error(f"Error en iteración de monitoreo: {e}", exc_info=True)
                current_interval = min(current_interval * 1.5, self.settings.monitoring.adaptive_backoff_max_seconds)
                logger.info(f"Pausa adaptativa por protección: esperando {current_interval:.1f}s...")

            await asyncio.sleep(current_interval)

    async def stop(self):
        self.is_running = False
        await self.providers.close_all()
        logger.info("Monitoreo detenido.")

    async def _check_direct_event(self, config: MonitoredEventConfig):
        try:
            provider = self.providers.get(config.provider) if config.provider else self.providers.get_by_url(config.url)
            if not provider:
                provider = self.providers.get("eden")

            event = await provider.get_event(config.url)
            event_id = event.id or config.url
            now = datetime.now(timezone.utc)
            now_str = now.isoformat()

            # 1. Congelar predicción pre-apertura
            forecast = await self._freeze_prediction_if_needed(event)

            # 2. Registrar Snapshot puntual
            await self.db.record_snapshot(
                event_id=event_id,
                provider=event.provider,
                name=event.name,
                city=event.city,
                venue=event.venue,
                status=event.status.value,
                available_shows=len([s for s in event.shows if s.available]) if event.shows else 0
            )

            # 3. Transición en Máquina de Estados
            sm = self.get_or_create_state_machine(event_id)
            old_status = sm.current_status
            changed = await sm.transition_to(event.status, event.model_dump())

            # Detectar apertura de venta / restock
            if changed and event.status == EventStatus.AVAILABLE:
                if event_id not in self.sale_start_times:
                    self.sale_start_times[event_id] = now

                is_restock = (old_status == EventStatus.SOLD_OUT)
                logger.info(f"¡ENTRADAS DISPONIBLES! Evento: {event.name} ({event.url})")

                if self.settings.sound.enabled:
                    asyncio.create_task(play_alert_sound_async())

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

            # Detectar transición a SOLD_OUT y registrar Outcome real
            elif changed and event.status == EventStatus.SOLD_OUT:
                sale_start = self.sale_start_times.get(event_id, now)
                duration_sec = (now - sale_start).total_seconds()
                duration_hours = round(duration_sec / 3600.0, 2)

                await self.db.record_outcome(
                    event_id=event_id,
                    sold_out=True,
                    sold_out_at=now_str,
                    time_to_sold_out_seconds=duration_sec,
                    final_status="SOLD_OUT"
                )
                logger.info(
                    f"[OUTCOME RECORDED] Evento agotado: {event.name} en {duration_hours} horas. "
                    f"Resultado guardado en la base de datos."
                )

        except Exception as e:
            logger.debug(f"Error consultando evento directo {config.url}: {e}")

    async def _check_watchlist(self):
        try:
            # Escanear watchlist en los providers que soporten catálogo
            eden_provider = self.providers.get("eden")
            if hasattr(eden_provider, "scanner"):
                matches = await eden_provider.scanner.scan_watchlist(self.events_config.watchlist)
            else:
                matches = []
            now = datetime.now(timezone.utc)
            now_str = now.isoformat()

            for event in matches:
                event_id = event.id or event.url

                # Congelar predicción pre-apertura
                forecast = await self._freeze_prediction_if_needed(event)

                # Registrar Snapshot
                await self.db.record_snapshot(
                    event_id=event_id,
                    provider=event.provider,
                    name=event.name,
                    city=event.city,
                    venue=event.venue,
                    status=event.status.value,
                    available_shows=len([s for s in event.shows if s.available]) if event.shows else 0
                )

                last_status = self.known_watchlist_matches.get(event_id)
                self.known_watchlist_matches[event_id] = event.status

                if last_status is None or (last_status != EventStatus.AVAILABLE and event.status == EventStatus.AVAILABLE):
                    logger.info(f"[WATCHLIST MATCH] Evento detectado: {event.name} - Estado: {event.status.value}")

                    if event.status == EventStatus.AVAILABLE:
                        if event_id not in self.sale_start_times:
                            self.sale_start_times[event_id] = now

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

                elif last_status == EventStatus.AVAILABLE and event.status == EventStatus.SOLD_OUT:
                    sale_start = self.sale_start_times.get(event_id, now)
                    duration_sec = (now - sale_start).total_seconds()
                    await self.db.record_outcome(
                        event_id=event_id,
                        sold_out=True,
                        sold_out_at=now_str,
                        time_to_sold_out_seconds=duration_sec,
                        final_status="SOLD_OUT"
                    )
                    logger.info(f"[OUTCOME RECORDED] Match de Watchlist agotado: {event.name}")

        except Exception as e:
            logger.debug(f"Error escaneando watchlist: {e}")

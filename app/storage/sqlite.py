import aiosqlite
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)

DB_PATH = Path("data/ticket_intelligence.db")


class IntelligenceDatabase:
    """Base de datos histórica en SQLite (Schema V2) para registrar observaciones de eventos,

    predicciones congeladas, snapshots en tiempo real y resultados reales (outcomes).
    """

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    async def init_db(self):
        """Crea las tablas relacionales del Event Model V2 si no existen."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("PRAGMA foreign_keys = ON;")

            # 1. Artistas
            await db.execute("""
                CREATE TABLE IF NOT EXISTS artists (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    genre TEXT DEFAULT 'CUARTETO',
                    default_sold_out_rate REAL DEFAULT 0.50
                )
            """)

            # 2. Venues / Lugares
            await db.execute("""
                CREATE TABLE IF NOT EXISTS venues (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    city TEXT NOT NULL,
                    province TEXT NOT NULL DEFAULT 'Cordoba',
                    capacity_estimate INTEGER,
                    venue_type TEXT DEFAULT 'BOLICHE'
                )
            """)

            # 3. Eventos
            await db.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    provider TEXT NOT NULL,
                    external_id TEXT,
                    name TEXT NOT NULL,
                    artist_id TEXT,
                    venue_id TEXT,
                    announced_at TIMESTAMP,
                    sale_start_at TIMESTAMP,
                    first_seen_at TIMESTAMP,
                    available_at TIMESTAMP,
                    sold_out_at TIMESTAMP,
                    event_date TIMESTAMP,
                    nominal_price REAL,
                    real_price_usd REAL,
                    final_status TEXT,
                    exclude_from_backtest BOOLEAN DEFAULT 0,
                    event_quality TEXT DEFAULT 'CONFIRMED',
                    source_event_url TEXT,
                    FOREIGN KEY(artist_id) REFERENCES artists(id),
                    FOREIGN KEY(venue_id) REFERENCES venues(id)
                )
            """)

            # 4. Snapshots en tiempo real
            await db.execute("""
                CREATE TABLE IF NOT EXISTS snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT,
                    timestamp TIMESTAMP NOT NULL,
                    status TEXT NOT NULL,
                    available_shows INTEGER,
                    min_price REAL,
                    max_price REAL,
                    FOREIGN KEY(event_id) REFERENCES events(id)
                )
            """)

            # 5. Predicciones congeladas pre-apertura
            await db.execute("""
                CREATE TABLE IF NOT EXISTS predictions (
                    id TEXT PRIMARY KEY,
                    event_id TEXT NOT NULL,
                    calculated_at TIMESTAMP NOT NULL,
                    sold_out_score REAL NOT NULL,
                    confidence TEXT NOT NULL,
                    artist_score REAL,
                    local_score REAL,
                    venue_score REAL,
                    price_score REAL,
                    date_score REAL,
                    model_version TEXT NOT NULL,
                    FOREIGN KEY(event_id) REFERENCES events(id)
                )
            """)

            # 6. Resultados reales (Outcomes)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS outcomes (
                    event_id TEXT PRIMARY KEY,
                    sold_out BOOLEAN,
                    sold_out_at TIMESTAMP,
                    time_to_sold_out_seconds REAL,
                    final_status TEXT,
                    quality TEXT DEFAULT 'CONFIRMED',
                    FOREIGN KEY(event_id) REFERENCES events(id)
                )
            """)

            # Vista de compatibilidad o tabla antigua para consultas rápidas
            await db.execute("""
                CREATE TABLE IF NOT EXISTS events_history (
                    id TEXT PRIMARY KEY,
                    provider TEXT,
                    external_id TEXT,
                    name TEXT,
                    artist TEXT,
                    city TEXT,
                    venue TEXT,
                    first_seen_at TIMESTAMP,
                    sold_out_at TIMESTAMP,
                    time_to_sold_out_seconds REAL,
                    total_snapshots INTEGER DEFAULT 0,
                    final_status TEXT
                )
            """)

            # Migraciones seguras si la DB ya existía previamente
            for col_def in [
                ("events", "exclude_from_backtest", "BOOLEAN DEFAULT 0"),
                ("events", "event_quality", "TEXT DEFAULT 'CONFIRMED'"),
                ("events", "source_event_url", "TEXT"),
                ("outcomes", "quality", "TEXT DEFAULT 'CONFIRMED'")
            ]:
                table, col_name, col_type = col_def
                try:
                    await db.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}")
                except Exception:
                    pass  # Columna ya existe

            await db.commit()
            logger.info("Base de datos de Ticket Intelligence V2 inicializada.")

    async def upsert_artist(self, artist_id: str, name: str, genre: str = "CUARTETO", default_sold_out_rate: float = 0.50):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO artists (id, name, genre, default_sold_out_rate)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    genre = excluded.genre,
                    default_sold_out_rate = excluded.default_sold_out_rate
            """, (artist_id, name, genre, default_sold_out_rate))
            await db.commit()

    async def upsert_venue(self, venue_id: str, name: str, city: str, province: str = "Cordoba", capacity_estimate: Optional[int] = None, venue_type: str = "BOLICHE"):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO venues (id, name, city, province, capacity_estimate, venue_type)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    city = excluded.city,
                    province = excluded.province,
                    capacity_estimate = excluded.capacity_estimate,
                    venue_type = excluded.venue_type
            """, (venue_id, name, city, province, capacity_estimate, venue_type))
            await db.commit()

    async def upsert_event(
        self,
        event_id: str,
        provider: str,
        name: str,
        artist_id: Optional[str] = None,
        venue_id: Optional[str] = None,
        external_id: Optional[str] = None,
        announced_at: Optional[str] = None,
        sale_start_at: Optional[str] = None,
        first_seen_at: Optional[str] = None,
        available_at: Optional[str] = None,
        sold_out_at: Optional[str] = None,
        event_date: Optional[str] = None,
        nominal_price: Optional[float] = None,
        real_price_usd: Optional[float] = None,
        final_status: Optional[str] = "AVAILABLE",
        exclude_from_backtest: bool = False,
        event_quality: str = "CONFIRMED",
        source_event_url: Optional[str] = None
    ):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO events (
                    id, provider, external_id, name, artist_id, venue_id,
                    announced_at, sale_start_at, first_seen_at, available_at,
                    sold_out_at, event_date, nominal_price, real_price_usd, final_status,
                    exclude_from_backtest, event_quality, source_event_url
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    artist_id = COALESCE(excluded.artist_id, events.artist_id),
                    venue_id = COALESCE(excluded.venue_id, events.venue_id),
                    sale_start_at = COALESCE(excluded.sale_start_at, events.sale_start_at),
                    sold_out_at = COALESCE(excluded.sold_out_at, events.sold_out_at),
                    final_status = COALESCE(excluded.final_status, events.final_status),
                    nominal_price = COALESCE(excluded.nominal_price, events.nominal_price),
                    exclude_from_backtest = excluded.exclude_from_backtest,
                    event_quality = excluded.event_quality,
                    source_event_url = excluded.source_event_url
            """, (
                event_id, provider, external_id or event_id, name, artist_id, venue_id,
                announced_at, sale_start_at, first_seen_at, available_at,
                sold_out_at, event_date, nominal_price, real_price_usd, final_status,
                1 if exclude_from_backtest else 0, event_quality, source_event_url
            ))
            await db.commit()

    async def record_outcome(
        self,
        event_id: str,
        sold_out: Optional[bool],
        sold_out_at: Optional[str] = None,
        time_to_sold_out_seconds: Optional[float] = None,
        final_status: str = "SOLD_OUT",
        quality: str = "CONFIRMED"
    ):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO outcomes (event_id, sold_out, sold_out_at, time_to_sold_out_seconds, final_status, quality)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(event_id) DO UPDATE SET
                    sold_out = excluded.sold_out,
                    sold_out_at = excluded.sold_out_at,
                    time_to_sold_out_seconds = excluded.time_to_sold_out_seconds,
                    final_status = excluded.final_status,
                    quality = excluded.quality
            """, (
                event_id,
                (1 if sold_out else 0) if sold_out is not None else None,
                sold_out_at,
                time_to_sold_out_seconds,
                final_status,
                quality
            ))
            await db.commit()

    async def get_backtest_events(self) -> List[Dict[str, Any]]:
        """Obtiene todos los eventos aptos para evaluación de backtesting (no excluidos y con outcome verificable)."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT 
                    e.id,
                    e.name as event_name,
                    e.artist_id,
                    a.name as artist_name,
                    e.venue_id,
                    v.name as venue_name,
                    v.city,
                    v.capacity_estimate,
                    e.event_date,
                    e.sale_start_at,
                    e.nominal_price,
                    e.event_quality,
                    o.sold_out,
                    o.sold_out_at,
                    o.time_to_sold_out_seconds,
                    o.quality as outcome_quality
                FROM events e
                LEFT JOIN artists a ON e.artist_id = a.id
                LEFT JOIN venues v ON e.venue_id = v.id
                LEFT JOIN outcomes o ON e.id = o.event_id
                WHERE (e.exclude_from_backtest = 0 OR e.exclude_from_backtest IS NULL)
                  AND o.sold_out IS NOT NULL
                ORDER BY e.event_date ASC
            """)
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def save_prediction(
        self,
        prediction_id: str,
        event_id: str,
        calculated_at: str,
        sold_out_score: float,
        confidence: str,
        artist_score: Optional[float] = None,
        local_score: Optional[float] = None,
        venue_score: Optional[float] = None,
        price_score: Optional[float] = None,
        date_score: Optional[float] = None,
        model_version: str = "v1.0"
    ):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO predictions (
                    id, event_id, calculated_at, sold_out_score, confidence,
                    artist_score, local_score, venue_score, price_score, date_score, model_version
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    sold_out_score = excluded.sold_out_score,
                    confidence = excluded.confidence
            """, (
                prediction_id, event_id, calculated_at, sold_out_score, confidence,
                artist_score, local_score, venue_score, price_score, date_score, model_version
            ))
            await db.commit()

    async def record_snapshot(
        self,
        event_id: str,
        provider: str,
        name: str,
        city: Optional[str],
        venue: Optional[str],
        status: str,
        available_shows: int,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None
    ):
        """Registra una observación en tiempo real y mantiene actualizadas las tablas correspondientes."""
        now = datetime.now(timezone.utc)
        now_str = now.isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            # 1. Asegurar registro en events_history (compatibilidad)
            cursor = await db.execute("SELECT first_seen_at, sold_out_at, total_snapshots FROM events_history WHERE id = ?", (event_id,))
            row = await cursor.fetchone()

            if not row:
                artist = name.split("-")[0].strip() if "-" in name else name.split(" en ")[0].strip()
                await db.execute("""
                    INSERT INTO events_history (id, provider, external_id, name, artist, city, venue, first_seen_at, total_snapshots, final_status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                """, (event_id, provider, event_id, name, artist, city or "", venue or "", now_str, status))
            else:
                first_seen, sold_out_at, snapshots_count = row
                sold_out_timestamp = sold_out_at
                time_to_sold_out = None

                if status == "SOLD_OUT" and not sold_out_at:
                    sold_out_timestamp = now_str
                    first_dt = datetime.fromisoformat(first_seen) if isinstance(first_seen, str) else first_seen
                    if first_dt.tzinfo is None:
                        first_dt = first_dt.replace(tzinfo=timezone.utc)
                    time_to_sold_out = (now - first_dt).total_seconds()

                await db.execute("""
                    UPDATE events_history 
                    SET total_snapshots = total_snapshots + 1, final_status = ?, sold_out_at = COALESCE(sold_out_at, ?), time_to_sold_out_seconds = COALESCE(time_to_sold_out_seconds, ?)
                    WHERE id = ?
                """, (status, sold_out_timestamp, time_to_sold_out, event_id))

            # 2. Insertar Snapshot puntual
            await db.execute("""
                INSERT INTO snapshots (event_id, timestamp, status, available_shows, min_price, max_price)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (event_id, now_str, status, available_shows, min_price, max_price))

            await db.commit()

    async def get_artist_stats(self, artist_query: str) -> Dict[str, Any]:
        """Obtiene el historial de agotamiento de una banda o artista cruzando tablas V2 y V1."""
        clean_query = artist_query.lower().strip()
        async with aiosqlite.connect(self.db_path) as db:
            # Primero consultar si hay outcomes registrados en la estructura relacional V2
            cursor = await db.execute("""
                SELECT 
                    COUNT(e.id) as total_events,
                    SUM(CASE WHEN o.sold_out = 1 OR e.final_status = 'SOLD_OUT' THEN 1 ELSE 0 END) as sold_out_events,
                    AVG(o.time_to_sold_out_seconds) as avg_seconds
                FROM events e
                LEFT JOIN artists a ON e.artist_id = a.id
                LEFT JOIN outcomes o ON e.id = o.event_id
                WHERE LOWER(e.name) LIKE ? OR LOWER(COALESCE(a.name, '')) LIKE ? OR LOWER(COALESCE(a.id, '')) LIKE ?
            """, (f"%{clean_query}%", f"%{clean_query}%", f"%{clean_query}%"))
            
            row = await cursor.fetchone()
            total_events = row[0] or 0
            sold_out_events = row[1] or 0
            avg_seconds = row[2] or 0

            # Si no encontró en V2, fallback a events_history
            if total_events == 0:
                cursor2 = await db.execute("""
                    SELECT COUNT(*), 
                           SUM(CASE WHEN final_status = 'SOLD_OUT' THEN 1 ELSE 0 END),
                           AVG(time_to_sold_out_seconds)
                    FROM events_history 
                    WHERE LOWER(name) LIKE ? OR LOWER(artist) LIKE ?
                """, (f"%{clean_query}%", f"%{clean_query}%"))
                row2 = await cursor2.fetchone()
                total_events = row2[0] or 0
                sold_out_events = row2[1] or 0
                avg_seconds = row2[2] or 0

            return {
                "total_events": total_events,
                "sold_out_events": sold_out_events,
                "sold_out_rate": (sold_out_events / total_events) if total_events > 0 else None,
                "avg_hours_to_sold_out": (avg_seconds / 3600.0) if avg_seconds else None
            }

    async def get_local_artist_stats(self, artist_query: str, city_query: str) -> Dict[str, Any]:
        """Obtiene el historial de una banda en una plaza/ciudad específica."""
        clean_artist = artist_query.lower().strip()
        clean_city = city_query.lower().strip()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT 
                    COUNT(e.id) as total_events,
                    SUM(CASE WHEN o.sold_out = 1 OR e.final_status = 'SOLD_OUT' THEN 1 ELSE 0 END) as sold_out_events,
                    AVG(o.time_to_sold_out_seconds) as avg_seconds
                FROM events e
                LEFT JOIN artists a ON e.artist_id = a.id
                LEFT JOIN venues v ON e.venue_id = v.id
                LEFT JOIN outcomes o ON e.id = o.event_id
                WHERE (LOWER(e.name) LIKE ? OR LOWER(COALESCE(a.name, '')) LIKE ?)
                  AND (LOWER(COALESCE(v.city, '')) LIKE ? OR LOWER(e.name) LIKE ?)
            """, (f"%{clean_artist}%", f"%{clean_artist}%", f"%{clean_city}%", f"%{clean_city}%"))
            
            row = await cursor.fetchone()
            total = row[0] or 0
            sold = row[1] or 0
            avg_sec = row[2] or 0

            return {
                "total_events": total,
                "sold_out_events": sold,
                "sold_out_rate": (sold / total) if total > 0 else None,
                "avg_hours_to_sold_out": (avg_sec / 3600.0) if avg_sec else None
            }

    async def get_venue_info(self, venue_query: str) -> Optional[Dict[str, Any]]:
        """Obtiene información y aforo de un venue por ID o coincidencia en el nombre."""
        if not venue_query:
            return None
        clean_v = venue_query.lower().strip()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT id, name, city, province, capacity_estimate, venue_type
                FROM venues
                WHERE id = ? OR LOWER(name) LIKE ?
            """, (clean_v, f"%{clean_v}%"))
            row = await cursor.fetchone()
            if row:
                return {
                    "id": row[0],
                    "name": row[1],
                    "city": row[2],
                    "province": row[3],
                    "capacity_estimate": row[4],
                    "venue_type": row[5]
                }
            return None

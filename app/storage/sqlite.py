import aiosqlite
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)

DB_PATH = Path("data/ticket_intelligence.db")

class IntelligenceDatabase:
    """Base de datos histórica en SQLite para registrar observaciones de eventos y calcular demanda."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    async def init_db(self):
        """Crea las tablas necesarias si no existen."""
        async with aiosqlite.connect(self.db_path) as db:
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
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT,
                    timestamp TIMESTAMP,
                    status TEXT,
                    available_shows INTEGER,
                    min_price REAL,
                    max_price REAL,
                    FOREIGN KEY(event_id) REFERENCES events_history(id)
                )
            """)
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS artist_profiles (
                    artist_name TEXT PRIMARY KEY,
                    total_events INTEGER DEFAULT 0,
                    sold_out_events INTEGER DEFAULT 0,
                    avg_time_to_sold_out_hours REAL DEFAULT 0.0,
                    demand_score REAL DEFAULT 50.0
                )
            """)
            await db.commit()
            logger.info("Base de datos de Ticket Intelligence inicializada.")

    async def record_snapshot(self, event_id: str, provider: str, name: str, city: Optional[str], venue: Optional[str], status: str, available_shows: int, min_price: Optional[float] = None, max_price: Optional[float] = None):
        """Registra una observación en tiempo real y calcula métricas de velocidad."""
        now = datetime.now(timezone.utc)
        now_str = now.isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            # 1. Asegurar registro del evento
            cursor = await db.execute("SELECT first_seen_at, sold_out_at, total_snapshots FROM events_history WHERE id = ?", (event_id,))
            row = await cursor.fetchone()

            if not row:
                # Extraer nombre aproximado del artista
                artist = name.split("-")[0].strip() if "-" in name else name.split(" en ")[0].strip()
                await db.execute("""
                    INSERT INTO events_history (id, provider, external_id, name, artist, city, venue, first_seen_at, total_snapshots, final_status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                """, (event_id, provider, event_id, name, artist, city or "", venue or "", now_str, status))
            else:
                first_seen, sold_out_at, snapshots_count = row
                sold_out_timestamp = sold_out_at
                time_to_sold_out = None

                # Si pasó a Sold Out y no estaba registrado
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
        """Obtiene el historial de agotamiento de una banda o artista."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT COUNT(*), 
                       SUM(CASE WHEN final_status = 'SOLD_OUT' THEN 1 ELSE 0 END),
                       AVG(time_to_sold_out_seconds)
                FROM events_history 
                WHERE LOWER(name) LIKE ? OR LOWER(artist) LIKE ?
            """, (f"%{artist_query.lower()}%", f"%{artist_query.lower()}%"))
            
            row = await cursor.fetchone()
            total_events = row[0] or 0
            sold_out_events = row[1] or 0
            avg_seconds = row[2] or 0

            return {
                "total_events": total_events,
                "sold_out_events": sold_out_events,
                "sold_out_rate": (sold_out_events / total_events) if total_events > 0 else None,
                "avg_hours_to_sold_out": (avg_seconds / 3600.0) if avg_seconds else None
            }

import os
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from app.core.config import load_settings, load_events_config
from app.monitoring.monitor import UnifiedMonitor

class HealthHandler(BaseHTTPRequestHandler):
    """Endpoint simple de salud HTTP para plataformas cloud como Render / Railway."""
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Ticket Assistant Monitor is running 24/7 OK")

    def log_message(self, format, *args):
        # Silenciar logs ruidosos de pings de salud
        pass

def run_http_server(port: int = 8080):
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()

async def main():
    # Obtener puerto asignado por la nube (Render / Railway / Fly.io)
    port = int(os.environ.get("PORT", 8080))
    
    # Iniciar servidor HTTP en un hilo secundario para cumplir con el Web Service de Render
    http_thread = threading.Thread(target=run_http_server, args=(port,), daemon=True)
    http_thread.start()
    print(f"[CLOUD SERVER] Servidor HTTP de salud activo en puerto {port}")

    # Iniciar el monitor continuo
    settings = load_settings()
    events_cfg = load_events_config()
    monitor = UnifiedMonitor(settings, events_cfg)
    
    try:
        await monitor.start()
    finally:
        await monitor.stop()

if __name__ == "__main__":
    asyncio.run(main())

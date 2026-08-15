# Ticket Monitoring & Purchase Assistant

Asistente local para el monitoreo, descubrimiento y preparación de compra de tickets de espectáculos con baja latencia y alta velocidad de reacción.

Construido con una arquitectura desacoplada y modular (agnóstica de ticketera), comenzando con soporte nativo para **Eden Entradas** y preparado para sumar futuros proveedores (Ticketek, AllAccess, EntradaUno, etc.).

---

## 🚀 Características Principales

1. **Scanner de Descubrimiento (Watchlist)**: Sondea el catálogo de Eden por palabras clave (ej: `"Desakta2"`, `"La Mona"`) y ciudad, detectando shows nuevos apenas se cargan en la base de datos de la productora.
2. **Monitor de Disponibilidad Ligero (Sub-100ms)**: Lee el payload estructurado incrustado de Eden sin renderizar ni sobrecargar servidores, detectando aperturas de venta y remanentes.
3. **Alertas Push en Telegram (Gratis)**: Notificación instantánea a tu celular con el enlace directo y sectores cuando se habilitan entradas.
4. **Asistente de Navegación (Playwright Headed)**: Abre Chromium visible con tu sesión real guardada, selecciona sector y cantidad según tus preferencias, y avanza el checkout.
5. **Human Checkpoint**: Se detiene con alarma sonora obligatoriamente en la pasarela de pago para que tú autorices la transacción (CVV / 3D Secure / Banco).

---

## 🛠️ Instalación

1. Clona o abre la carpeta del proyecto en tu terminal.
2. Instala las dependencias:
```bash
pip install -r requirements.txt
playwright install chromium
```

---

## ⚙️ Configuración

- **`config/events.yaml`**: Define tu lista de artistas o eventos de interés (`watchlist`) y URLs directas si ya las conoces.
- **`config/settings.yaml`**: Configura intervalos de sondeo, activación de alertas sonoras y credenciales de Telegram (opcional).
- **`config/buyer_profiles.yaml`**: Copia `config/buyer_profiles.example.yaml` a `config/buyer_profiles.yaml` con tus datos personales de contacto para agilizar el checkout.

---

## 🎮 Comandos de Uso

### 1. Diagnóstico del Sistema (Preflight Check)
Verifica que tu conexión, la API de Eden, tus configuraciones y el sonido estén listos:
```bash
python -m app.main preflight
```

### 2. Iniciar Sesión en Eden (Por cada cuenta / DNI)
Abre un navegador independiente para cada cuenta para guardar las sesiones sin que se mezclen:
```bash
python -m app.main login --profile facu
python -m app.main login --profile cuenta2
python -m app.main login --profile cuenta3
```

### 3. Disparar Compra en Paralelo (Multi-Cuenta simultánea)
Reserva 4 entradas en la cuenta de Facu y 4 entradas en la cuenta 2 al mismo tiempo:
```bash
python -m app.main buy https://www.edenentradas.ar/event/desakta2-150826 --profiles facu,cuenta2 --quantity 4
```

### 4. Buscar Eventos en el Catálogo de Eden
```bash
python -m app.main search "Desakta2"
```

### 5. Iniciar el Monitor Continuo 24/7 (Watchlist + URLs)
```bash
python -m app.main monitor
```

### 5. Inspeccionar una URL en Detalle
```bash
python scripts/inspect_event.py https://www.edenentradas.ar/event/desakta2-150826
```

---

## 🧪 Ejecución de Tests
```bash
pytest
```

# Plan Maestro — Ticket Monitoring & Purchase Assistant

## 0. Objetivo del proyecto

Construir un sistema local que permita:

1. Monitorear eventos de ticketing.
2. Detectar cambios de disponibilidad con baja latencia.
3. Alertar inmediatamente al usuario.
4. Tener un navegador previamente preparado y autenticado.
5. Automatizar las partes repetitivas del proceso de compra:
   - apertura del evento;
   - navegación;
   - selección de sector;
   - selección de cantidad;
   - carga de datos personales;
   - avance del checkout.
6. Detenerse antes de cualquier autorización sensible que requiera intervención humana:
   - MFA;
   - OTP;
   - CAPTCHA;
   - 3D Secure;
   - CVV cuando corresponda;
   - autorización bancaria;
   - validaciones posteriores de Eden.
7. Registrar datos públicos históricos de eventos para construir posteriormente:
   - estimación de demanda;
   - probabilidad de sold-out;
   - expected time-to-sell-out;
   - velocidad de absorción;
   - análisis comparativo entre eventos.

El primer proveedor será:

```text
Eden Entradas
https://www.edenentradas.ar
```

Pero la arquitectura debe permitir agregar posteriormente:

```text
Ticketek
AllAccess
EntradaUno
otros providers
```

---

# 1. Principios arquitectónicos

## 1.1 No construir un bot monolítico

Separar claramente:

```text
Monitoring
Browser Automation
Provider Logic
User Profiles
Logging
Data Collection
Forecasting
```

Nunca mezclar toda la lógica de Eden dentro de un único script.

---

## 1.2 Provider-agnostic core

El core de la aplicación no debe saber cómo funciona específicamente Eden.

Crear una interfaz conceptual:

```python
TicketProvider
```

con capacidades como:

```python
get_event()
get_event_status()
get_sale_phases()
get_public_inventory_information()
get_ticket_limits()
get_sectors()
```

Implementación inicial:

```python
EdenProvider(TicketProvider)
```

Posteriormente:

```python
TicketekProvider
AllAccessProvider
EntradaUnoProvider
```

---

# 2. Límites técnicos y operativos

El sistema puede:

```text
✓ observar páginas públicas
✓ analizar HTML público
✓ analizar JSON embebido públicamente
✓ inspeccionar requests normales realizados por el navegador
✓ reutilizar una sesión legítima del propio usuario
✓ automatizar navegación normal del navegador
✓ rellenar datos del comprador
✓ seleccionar entradas
✓ preparar checkout
✓ registrar información pública
```

El sistema NO debe implementar:

```text
✗ CAPTCHA bypass
✗ fingerprint spoofing
✗ evasión de mecanismos anti-bot
✗ saltos de cola virtual
✗ manipulación de tokens firmados
✗ explotación de endpoints internos
✗ bypass de rate limits
✗ múltiples cuentas destinadas a superar límites
✗ falsificación de DNI
✗ automatización de MFA
✗ automatización de OTP
✗ automatización de 3DS
✗ intento de superar HTTP 403
```

Si aparece uno de estos mecanismos:

```text
BLOCKED
CHALLENGE
CAPTCHA
MFA_REQUIRED
```

el sistema debe:

```text
STOP
+
USER_ACTION_REQUIRED
```

---

# 3. Consideraciones legales

No asumir que:

```text
"scraping público = 100 % legal"
```

La evaluación depende de:

```text
qué recurso se consulta
si requiere autorización
qué dicen los términos
frecuencia de consultas
tipo de automatización
objetivo de utilización
```

La Ley 26.388 incorporó al Código Penal argentino el art. 153 bis sobre acceso sin autorización o excediendo la autorización a sistemas o datos informáticos de acceso restringido.

La arquitectura debe evitar depender de acceso a recursos restringidos.

Eden además establece condiciones propias y condiciones dependientes del productor.

El sistema debe tratar las reglas de cada evento como variables dinámicas.

Ejemplos:

```text
max_tickets = 4
max_tickets = 6
```

No asumir un máximo global.

También pueden variar:

```text
formas de pago
verificación posterior
tipo de entrada
Quentro
E-TKT
preventa
venta general
límite de compra
condiciones particulares
```

Eden documenta eventos con procesos de verificación de compra mediante código o monto, y otros medios de pago como Mercado Pago/MODO donde el flujo puede ser distinto.

---

# 4. Arquitectura general

```text
                           TICKET PLATFORM
                                  │
                                  ▼
                    ┌────────────────────────┐
                    │    PROVIDER ADAPTER    │
                    │        Eden            │
                    └────────────┬───────────┘
                                 │
                 ┌───────────────┴────────────────┐
                 │                                │
                 ▼                                ▼
       ┌─────────────────┐               ┌─────────────────┐
       │ EVENT MONITOR   │               │ DATA COLLECTOR  │
       │                 │               │                 │
       │ httpx/asyncio   │               │ historical data │
       └────────┬────────┘               └────────┬────────┘
                │                                 │
       EVENT_AVAILABLE                            ▼
                │                         ┌─────────────────┐
                ▼                         │ DATABASE        │
       ┌─────────────────┐                └────────┬────────┘
       │ EVENT BUS       │                         │
       └────────┬────────┘                         ▼
                │                        ┌─────────────────┐
                ▼                        │ FORECAST ENGINE │
       ┌─────────────────┐               └─────────────────┘
       │ BROWSER WORKER  │
       │ Playwright      │
       │ Chromium headed │
       └────────┬────────┘
                │
                ▼
       ┌─────────────────┐
       │ CHECKOUT        │
       │ ASSISTANT       │
       └────────┬────────┘
                │
                ▼
       USER_ACTION_REQUIRED
                │
                ▼
         USER AUTHORIZATION
```

---

# 5. Arquitectura inicial del repositorio

```text
ticket-assistant/
│
├── app/
│
│   ├── core/
│   │   ├── models.py
│   │   ├── events.py
│   │   ├── enums.py
│   │   ├── state_machine.py
│   │   └── exceptions.py
│   │
│   ├── providers/
│   │   ├── base.py
│   │   │
│   │   └── eden/
│   │       ├── provider.py
│   │       ├── parser.py
│   │       ├── monitor.py
│   │       ├── selectors.py
│   │       └── models.py
│   │
│   ├── monitoring/
│   │   ├── monitor.py
│   │   ├── polling.py
│   │   └── transitions.py
│   │
│   ├── browser/
│   │   ├── worker.py
│   │   ├── session.py
│   │   ├── preflight.py
│   │   ├── automation.py
│   │   └── human_checkpoint.py
│   │
│   ├── notifications/
│   │   ├── sound.py
│   │   └── telegram.py
│   │
│   ├── storage/
│   │   ├── repository.py
│   │   └── sqlite.py
│   │
│   ├── analytics/
│   │   ├── collector.py
│   │   ├── features.py
│   │   └── forecasting.py
│   │
│   └── main.py
│
├── config/
│   ├── events.yaml
│   └── settings.yaml
│
├── data/
│   ├── profiles/
│   └── ticket_assistant.db
│
├── logs/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
│
├── scripts/
│   ├── inspect_event.py
│   ├── start_monitor.py
│   └── browser_preflight.py
│
├── pyproject.toml
├── .gitignore
├── README.md
└── ARCHITECTURE.md
```

---

# 6. Stack tecnológico inicial

## Backend / Core

```text
Python 3.12+
```

## HTTP

```text
httpx
```

Utilizar:

```text
AsyncClient
HTTP connection pooling
timeouts explícitos
```

---

## Parsing

Inicialmente:

```text
BeautifulSoup
```

Si existen JSON públicos:

```text
json
pydantic
```

Prioridad:

```text
API pública
↓
JSON embebido
↓
HTML
```

---

## Browser Automation

```text
Playwright
Chromium
headed mode
```

No usar browser headless para la ejecución de compra.

---

## Persistencia

MVP:

```text
SQLite
```

No introducir PostgreSQL/Supabase inicialmente.

---

## Configuración

```text
YAML
+
Pydantic Settings
```

---

## Testing

```text
pytest
pytest-asyncio
```

---

# 7. Modelo de datos

## Event

```python
Event:
    id
    provider
    external_id
    name
    url
    city
    venue
    event_datetime
    producer
```

---

## SalePhase

```python
SalePhase:
    id
    event_id
    name

    type:
        PRESALE
        GENERAL
        VIP
        OTHER

    start_at
    end_at

    initial_stock
    initial_stock_known

    max_tickets

    status
```

---

## Sector

```python
Sector:
    id
    sale_phase_id
    name
    price
    currency
    status
```

---

## AvailabilitySnapshot

```python
AvailabilitySnapshot:
    event_id
    timestamp

    status

    sectors_available
    sale_phases_available

    raw_public_data_hash
```

---

# 8. Estados

Crear:

```python
class EventStatus(Enum):
    UNKNOWN
    UPCOMING
    AVAILABLE
    LOW_AVAILABILITY
    SOLD_OUT
    FINISHED
    ERROR
    BLOCKED
```

Browser:

```python
class BrowserState(Enum):
    IDLE
    READY
    NAVIGATING
    SELECTING
    CHECKOUT
    USER_ACTION_REQUIRED
    COMPLETED
    FAILED
```

---

# 9. State machine

Flujo:

```text
IDLE
 ↓
MONITORING
 ↓
AVAILABLE_DETECTED
 ↓
BROWSER_NAVIGATING
 ↓
SELECTING
 ↓
CHECKOUT_PREPARATION
 ↓
USER_ACTION_REQUIRED
 ↓
COMPLETED
```

Errores posibles:

```text
SESSION_EXPIRED
BLOCKED
EVENT_UNAVAILABLE
SELECTOR_NOT_FOUND
TIMEOUT
UNKNOWN_PAGE
```

Nunca continuar silenciosamente ante un estado desconocido.

---

# 10. Configuración por evento

Ejemplo:

```yaml
provider: eden

event:
  url: "https://www.edenentradas.ar/event/example"

purchase:
  quantity: 2

preferences:
  sectors:
    - "Campo"
    - "Platea"

buyer_profile: "facu"

monitor:
  enabled: true
```

No codificar preferencias directamente en Python.

---

# 11. Buyer profiles

Archivo local:

```text
buyer_profiles.yaml
```

Ejemplo:

```yaml
facu:
  first_name: "Facundo"
  last_name: ""
  dni: ""
  email: ""
  phone: ""
```

Nunca guardar:

```text
CVV
OTP
MFA codes
3DS codes
```

Agregar:

```text
buyer_profiles.yaml
```

al `.gitignore`.

---

# 12. FASE 0 — Reverse engineering permitido del frontend

Objetivo:

Entender cómo funciona Eden sin escribir todavía automatización compleja.

## Procedimiento

Abrir un evento disponible.

Chrome:

```text
F12
→ Network
→ Fetch/XHR
```

Registrar:

```text
request URL
HTTP method
status code
response type
si requiere login
si contiene información de evento
si contiene stock
si contiene sectores
si contiene disponibilidad
```

NO registrar ni compartir:

```text
cookies
Authorization headers
session tokens
JWT
payment credentials
```

---

# 13. Clasificación de endpoints

Cada request descubierto debe clasificarse:

## PUBLIC

```text
sin autenticación
información pública
sin mecanismos especiales
```

Puede evaluarse como fuente del monitor.

---

## SESSION

```text
requiere sesión normal del usuario
```

No replicar innecesariamente fuera del navegador.

Utilizar Playwright.

---

## PROTECTED

Indicadores:

```text
403
CAPTCHA
challenge
fingerprint
queue token
signed token
```

Resultado:

```text
DO NOT AUTOMATE DIRECTLY
```

---

# 14. FASE 1 — Eden Provider

Implementar:

```python
EdenProvider
```

Responsabilidades:

```text
parse_event()
parse_sale_phases()
parse_ticket_limits()
parse_public_stock()
parse_status()
parse_sectors()
```

Salida siempre normalizada al modelo del core.

---

# 15. Parser tolerante

Nunca depender de un único texto exacto.

Ejemplo:

```text
COMPRAR
COMPRAR AHORA
AGOTADO
FINALIZADO
PRÓXIMAMENTE
```

Implementar normalización:

```text
lowercase
trim
unicode normalization
accent handling
```

Tests con fixtures HTML.

---

# 16. FASE 2 — Availability Monitor

Implementar con:

```text
asyncio
+
httpx.AsyncClient
```

Mantener conexiones persistentes.

No abrir un proceso HTTP nuevo para cada request.

---

## Monitor loop

Conceptualmente:

```python
while monitoring:

    current = await provider.get_event_status()

    if current != previous:
        emit_transition(previous, current)

    previous = current

    await sleep(interval)
```

---

# 17. Monitor adaptativo

No utilizar polling extremadamente agresivo.

Configurar modos:

```text
NORMAL
LAUNCH_WINDOW
```

Ejemplo conceptual:

```text
NORMAL:
polling más espaciado

LAUNCH_WINDOW:
polling más frecuente pero razonable
```

Mantener:

```text
jitter pequeño
timeouts
backoff ante errores
```

Ante:

```text
429
403
```

reducir frecuencia / detener.

Nunca intensificar requests.

---

# 18. Transiciones relevantes

Especialmente:

```text
UPCOMING → AVAILABLE
SOLD_OUT → AVAILABLE
AVAILABLE → SOLD_OUT
```

Emitir:

```text
EVENT_AVAILABLE
EVENT_SOLD_OUT
EVENT_RESTOCKED
```

---

# 19. FASE 3 — Browser Worker

Utilizar:

```python
launch_persistent_context()
```

Directorio:

```text
data/profiles/eden/
```

Modo:

```text
headless=False
```

---

# 20. Sesión persistente

Primera ejecución:

```text
abrir navegador
↓
usuario inicia sesión manualmente
↓
Eden valida cuenta
↓
cerrar
```

Ejecuciones futuras:

```text
reuse browser profile
```

No almacenar contraseña en el código.

---

# 21. Browser precalentado

NO:

```text
EVENT_AVAILABLE
↓
launch browser
```

SÍ:

```text
antes de venta
↓
launch browser
↓
session validated
↓
browser READY
```

Cuando llega:

```text
EVENT_AVAILABLE
```

realizar:

```text
refresh / navigate
```

inmediatamente.

---

# 22. FASE 4 — Preflight

Implementar comando:

```text
python -m app preflight
```

Resultado esperado:

```text
EDEN PREFLIGHT

Internet                 OK
Eden accessible          OK
Event URL                OK
Session                  OK
Browser                  READY
Buyer profile            READY
Requested quantity       2
Preferred sector         Campo
Monitor                  READY
Notifications            READY
```

Si algo falla:

```text
PRE-FLIGHT FAILED
```

No iniciar automatización.

---

# 23. FASE 5 — Checkout Assistant

Automatizar únicamente acciones normales de UI.

Ejemplos:

```text
Comprar
sector
cantidad
continuar
datos comprador
checkout
```

---

# 24. Estrategia de selectores

Orden de preferencia:

```text
1. role
2. label
3. text semántico
4. data-testid
5. atributos estables
6. CSS
7. XPath sólo excepcionalmente
```

Ejemplo:

```python
page.get_by_role("button", name="Comprar")
```

Evitar:

```text
div:nth-child(...)
```

---

# 25. Auto-waiting

No introducir:

```python
sleep(2)
sleep(1)
```

innecesariamente.

Utilizar:

```text
Playwright auto-waiting
wait_for()
expect()
```

---

# 26. Estrategia de sectores

Configuración:

```yaml
sectors:
  - Campo
  - Platea Baja
  - Platea Alta
```

Interpretación:

```text
preferencia 1
↓
si no existe
preferencia 2
↓
si no existe
preferencia 3
```

Nunca seleccionar automáticamente un sector fuera de la configuración del usuario.

---

# 27. Cantidad de tickets

La cantidad solicitada debe cumplir:

```text
desired_quantity <= event.max_tickets
```

Si:

```text
event.max_tickets = UNKNOWN
```

no asumir 4 o 6.

Puede requerirse confirmación previa/configuración.

---

# 28. Human checkpoint

La automatización debe detenerse ante:

```text
payment authorization
MFA
OTP
3DS
CAPTCHA
security challenge
```

Estado:

```text
USER_ACTION_REQUIRED
```

Emitir:

```text
alerta sonora
+
notificación visual
```

---

# 29. FASE 6 — Notifications

Implementar inicialmente:

```text
desktop sound
```

Luego opcional:

```text
Telegram
```

Eventos:

```text
AVAILABLE
RESTOCK
SESSION_EXPIRED
USER_ACTION_REQUIRED
ERROR
```

---

# 30. FASE 7 — Logging

Registrar timestamps de alta precisión.

Ejemplo:

```text
10:00:00.134 monitor_request
10:00:00.318 status_available

10:00:00.319 event_available

10:00:00.322 browser_received

10:00:00.610 navigation_started

10:00:01.014 purchase_page_ready
```

---

# 31. Métricas de performance

Calcular:

```text
Detection latency
Event bus latency
Navigation latency
DOM ready latency
Selection latency
Checkout preparation latency
```

Ejemplo:

```text
Detection                184 ms
Internal event              3 ms
Browser navigation        401 ms
Selection                 250 ms
──────────────────────────────
Total                     838 ms
```

No establecer objetivos irreales antes de medir.

---

# 32. Observability

Mantener:

```text
logs/application.log
logs/browser.log
logs/monitor.log
```

Opcionalmente JSON logs:

```json
{
  "timestamp": "...",
  "type": "EVENT_AVAILABLE",
  "event_id": "...",
  "latency_ms": 183
}
```

---

# 33. FASE 8 — Data Collector

Cada consulta debe permitir registrar información pública útil.

Ejemplo:

```text
timestamp
event
sale phase
status
price
sector
public stock
max tickets
```

---

# 34. Base histórica

SQLite inicialmente.

Tablas:

```text
events
sale_phases
sectors
availability_snapshots
public_inventory
status_transitions
```

---

# 35. Public inventory

Cuando Eden explícitamente publica algo como:

```text
Stock preventa: 4.000
```

guardar:

```python
initial_stock = 4000
initial_stock_known = True
```

Si no publica:

```python
initial_stock = None
initial_stock_known = False
```

Nunca fabricar estimaciones y almacenarlas como observaciones reales.

---

# 36. Separar hechos de estimaciones

Campo:

```text
value_source
```

Valores:

```text
OBSERVED
PUBLISHED
ESTIMATED
INFERRED
```

Ejemplo:

```text
initial_stock = 4000
source = PUBLISHED
```

versus:

```text
remaining_stock = 1200
source = ESTIMATED
```

---

# 37. FASE 9 — Ticket Intelligence

No implementar ML durante el MVP.

Primero construir dataset.

El objetivo futuro:

```text
P(sold-out < 1h)

P(sold-out < 6h)

P(sold-out < 24h)

Expected Time To Sell Out
```

---

# 38. Features futuras

## Evento

```text
venue
capacity
city
date
weekday
time
```

## Artista

```text
historical demand
historical sell-outs
social signals
search trends
```

## Venta

```text
price
presale stock
number of sale phases
ticket limit
time since opening
```

## Comportamiento

```text
sector depletion
status transitions
time-to-first-sold-out
restocks
```

---

# 39. Modelos futuros

Primera generación:

```text
Logistic Regression
Survival Analysis
Gradient Boosting
```

No deep learning inicialmente.

---

# 40. Métrica central

La variable más interesante:

```text
TIME TO SOLD OUT
```

Survival analysis:

```text
T = tiempo entre apertura de venta y sold-out
```

También:

```text
sold_out_1h
sold_out_6h
sold_out_24h
```

---

# 41. FASE 10 — Dashboard

NO construir todavía.

Cuando exista suficiente funcionalidad:

```text
EVENTS
───────────────────────────────
Evento A       SOLD OUT
Evento B       MONITORING
Evento C       UPCOMING

SYSTEM
───────────────────────────────
Browser         READY
Session         ACTIVE
Monitor         ACTIVE

ANALYTICS
───────────────────────────────
P(sold-out 24h)       82%
```

Puede implementarse más adelante con:

```text
FastAPI
+
React/Next.js
```

Pero no forma parte del MVP.

---

# 42. Testing strategy

## Unit tests

Parser:

```text
UPCOMING
AVAILABLE
SOLD_OUT
```

Límites:

```text
4 tickets
6 tickets
unknown
```

Stocks:

```text
4.000
1.061
unknown
```

---

## Integration tests

Utilizar HTML guardado localmente.

Nunca depender exclusivamente de requests reales a Eden durante tests.

Fixtures:

```text
tests/fixtures/eden/
```

---

# 43. Browser tests

Testear:

```text
navigation
selectors
buyer form
fallback sectors
unexpected UI
```

Nunca realizar compra real durante tests automatizados.

---

# 44. Dry-run mode

Obligatorio.

Configuración:

```yaml
dry_run: true
```

Con `dry_run`:

```text
monitoriza
abre browser
navega
selecciona

PERO NO cruza checkpoint configurado
```

Debe utilizarse durante desarrollo.

---

# 45. Kill switch

Agregar:

```text
CTRL+C
```

y botón/flag:

```text
STOP AUTOMATION
```

Debe cancelar:

```text
monitor
browser actions
pending tasks
```

de forma segura.

---

# 46. Error handling

Casos mínimos:

```text
NETWORK_ERROR
RATE_LIMITED
BLOCKED
SESSION_EXPIRED
SELECTOR_CHANGED
EVENT_REMOVED
EVENT_SOLD_OUT
PAYMENT_PAGE
UNKNOWN_STATE
```

Nunca continuar por defecto ante `UNKNOWN_STATE`.

---

# 47. Seguridad local

`.gitignore`:

```text
data/profiles/
buyer_profiles.yaml
.env
*.db
logs/
```

No subir a GitHub:

```text
cookies
profile Chromium
PII
session data
```

---

# 48. Documentación obligatoria

Crear:

```text
README.md
ARCHITECTURE.md
SAFETY_BOUNDARIES.md
PROVIDERS.md
TESTING.md
```

---

# 49. Orden exacto de implementación

## Milestone 0 — Inspection

Objetivo:

```text
entender Eden
```

Entregable:

```text
docs/eden-network-analysis.md
```

Debe documentar:

```text
páginas
estados
requests
endpoints
clasificación PUBLIC/SESSION/PROTECTED
```

---

## Milestone 1 — Core

Implementar:

```text
models
enums
provider interface
state machine
configuration
```

Acceptance criteria:

```text
pytest green
provider abstraction definida
```

---

## Milestone 2 — Eden Parser

Implementar:

```text
event parser
status parser
sale phase parser
ticket limit parser
public stock parser
```

Acceptance:

```text
fixtures reales
tests deterministas
```

---

## Milestone 3 — Monitor

Implementar:

```text
async http client
polling
transitions
logging
```

Acceptance:

```text
detecta AVAILABLE
detecta SOLD_OUT
detecta RESTOCK
```

---

## Milestone 4 — Browser

Implementar:

```text
persistent profile
browser worker
session detection
preflight
```

Acceptance:

```text
navegador persistente
sesión reutilizada
```

---

## Milestone 5 — Basic Assistant

Automatizar:

```text
open event
click purchase CTA
navigation
```

Dry-run solamente.

---

## Milestone 6 — Purchase Configuration

Agregar:

```text
quantity
sector preferences
buyer profile
fallback sectors
```

---

## Milestone 7 — Checkout Preparation

Automatizar flujo hasta:

```text
USER_ACTION_REQUIRED
```

Nunca atravesar automáticamente challenges de seguridad.

---

## Milestone 8 — Performance

Instrumentar:

```text
latency logs
timings
bottlenecks
```

Optimizar después de medir.

---

## Milestone 9 — Collector

Guardar:

```text
status snapshots
prices
public stock
sale phases
transitions
```

---

## Milestone 10 — Intelligence

Sólo cuando exista dataset suficiente.

Construir:

```text
features
baseline model
survival analysis
evaluation
```

---

# 50. MVP v0.1

La primera versión considerada exitosa debe hacer solamente esto:

```text
1. usuario pega URL Eden

2. sistema analiza evento

3. usuario configura:
   - cantidad
   - sector
   - alternativa

4. usuario inicia sesión previamente

5. preflight verifica todo

6. monitor comienza

7. Eden cambia a AVAILABLE

8. browser reacciona

9. navega el flujo

10. completa datos permitidos

11. llega al human checkpoint

12. usuario continúa manualmente
```

Todo lo demás es V2+.

---

# 51. Definition of Done — MVP

Considerar MVP terminado cuando:

```text
✓ evento Eden puede cargarse desde config

✓ provider identifica correctamente estado

✓ monitor detecta transición

✓ no dispara eventos duplicados

✓ browser persistente funciona

✓ sesión se conserva

✓ preflight funciona

✓ evento se abre automáticamente

✓ selección configurable funciona

✓ buyer profile funciona

✓ human checkpoint funciona

✓ dry-run funciona

✓ logging de latencias funciona

✓ existe kill switch

✓ tests principales pasan

✓ ningún secreto está versionado
```

---

# 52. No-go criteria

Detener una implementación si requiere:

```text
CAPTCHA bypass
403 bypass
fingerprint spoofing
queue bypass
token forgery
session impersonation
MFA automation
OTP automation
```

En esos casos:

```text
document issue
↓
fallback to USER_ACTION_REQUIRED
```

---

# 53. Roadmap resumido

```text
V0
│
├── Eden inspection
├── Core
├── Eden Provider
└── Parser

V0.1
│
├── Monitor
├── Browser Worker
├── Preflight
└── Alerts

V0.2
│
├── Quantity
├── Sectors
├── Buyer profile
└── Checkout assistant

V0.3
│
├── Logging
├── performance
├── collector
└── historical database

V1
│
├── stable Eden adapter
├── UI
└── production-grade local assistant

V1.5
│
├── Ticketek
├── AllAccess
└── EntradaUno

V2
│
├── forecasting
├── sell-out probability
├── survival analysis
└── analytics dashboard
```

---

# 54. Instrucción inicial para los agentes de programación

Prioridad:

```text
NO programar directamente el flujo completo.
```

Primera tarea:

```text
Realizar Eden Inspection.
```

Después:

```text
crear el core
↓
crear EdenProvider
↓
crear fixtures
↓
crear parsers deterministas
↓
crear monitor
↓
recién después Playwright
```

No implementar:

```text
dashboard
ML
cloud
multi-provider
Telegram complejo
PostgreSQL
```

antes de que Eden funcione correctamente.

---

# 55. Primera prueba real recomendada

Elegir:

```text
evento Eden actualmente disponible
```

Modo:

```text
dry_run = true
```

Probar:

```text
Event URL
↓
Provider parsing
↓
Availability
↓
Browser opening
↓
Purchase CTA
↓
Navigation
↓
STOP
```

Una vez estable:

```text
añadir sector
↓
cantidad
↓
buyer information
↓
checkpoint
```

---

# 56. Decisión arquitectónica final

El proyecto no debe conceptualizarse como:

```text
"bot que compra entradas"
```

Sino como dos sistemas relacionados:

```text
TICKET EXECUTION ENGINE
+
TICKET INTELLIGENCE
```

## Ticket Execution Engine

Optimiza:

```text
detección
reacción
navegación
preparación de checkout
```

## Ticket Intelligence

Construye:

```text
dataset histórico
demanda
escasez
sell-out probability
time-to-sell-out
```

Ambos comparten:

```text
Provider Adapters
Event Models
Public Data Collector
```

pero deben permanecer desacoplados.

---

# 57. Resultado final esperado

La visión de largo plazo:

```text
                     TICKET ENGINE

        ┌─────────────────────────────┐
        │       PROVIDERS             │
        │ Eden / Ticketek / AA / ...  │
        └──────────────┬──────────────┘
                       │
         ┌─────────────┴──────────────┐
         ▼                            ▼
 EXECUTION ENGINE             INTELLIGENCE ENGINE
         │                            │
 Monitor                        Historical Data
 Browser                        Demand Models
 Checkout Assistant             Sell-out Forecast
         │                            │
         ▼                            ▼
 Faster Purchase             Better Decisions
```

Primero debe funcionar impecablemente:

```text
Eden
→ Monitor
→ Browser
→ Checkout preparation
```

Después se escala.

Ese es el orden de construcción.
# Ticket Assistant — Plan Maestro y Roadmap de Largo Plazo

**Versión:** 1.0  
**Estado inicial:** Eden Entradas operativo  
**Foco inicial:** Cuarteto — Córdoba y Río Cuarto  
**Expansión futura:** otros recitales → eventos masivos → fútbol  
**Stack principal:** Python  
**Principio de diseño:** sistema determinístico, modular, basado en datos y multi-ticketera.

---

# 1. Visión

Ticket Assistant evolucionará desde un monitor/asistente de compra para Eden Entradas hacia una plataforma de **inteligencia, monitoreo y preparación operativa para eventos de alta demanda**.

El objetivo principal no es esperar a que un evento haga sold-out.

El objetivo es:

> **Identificar antes de la apertura de venta aquellos eventos que presentan una probabilidad elevada de agotamiento, priorizarlos y preparar automáticamente el flujo de compra permitido para reducir el tiempo de reacción.**

El sistema deberá aprender progresivamente de:

- eventos históricos;
- comportamiento por artista;
- comportamiento geográfico;
- venue;
- capacidad;
- precios;
- fecha;
- velocidad de agotamiento;
- comportamiento observado en tiempo real;
- resultados de predicciones anteriores.

Inicialmente el dominio será:

> **Bandas de cuarteto en Córdoba y Río Cuarto.**

Ejemplos:

- Q' Lokura
- DesaKTa2
- La Konga
- Euge Quevedo / LBC
- La Mona Jiménez
- Luck Ra
- otros artistas relevantes del circuito

Con el tiempo podrá ampliarse hacia:

1. otros géneros musicales;
2. recitales nacionales;
3. recitales internacionales;
4. festivales;
5. espectáculos masivos;
6. partidos de fútbol.

---

# 2. Principios del sistema

Ticket Assistant debe mantener cinco principios.

## 2.1. Inteligencia antes que ejecución

La decisión sobre qué evento merece atención debe producirse **antes de que se abra la venta**.

El bot de ejecución no debería tener que "pensar" cuando comienza una venta.

Debe recibir una decisión previamente calculada:

```text
EVENTO: Q' Lokura — Río Cuarto
SOLD-OUT SCORE: 91/100
CONFIDENCE: HIGH

SALE_START: 12:00
ACTION: PRIORITY
QUANTITY: configuración permitida
SECTOR: preferido
MAX_PRICE: configuración usuario
```

---

## 2.2. Determinismo en el core

El núcleo del sistema será Python tradicional.

No se utilizarán LLMs o agentes para:

- calcular scores;
- decidir estados;
- detectar aperturas;
- controlar el monitor;
- ejecutar reglas;
- calcular métricas;
- gestionar la base histórica.

Estas tareas deben ser:

- rápidas;
- reproducibles;
- testeables;
- económicas;
- explicables.

---

## 2.3. Agentes como capa opcional

Hermes, OpenClaw u otros agentes podrán incorporarse en el futuro para:

- descubrir anuncios no estructurados;
- revisar noticias;
- analizar publicaciones;
- completar metadatos;
- investigar capacidad de venues;
- encontrar eventos nuevos.

Pero nunca serán requisito del core.

Arquitectura conceptual:

```text
           FUENTES NO ESTRUCTURADAS
                    │
              AI Agent opcional
                    │
                    ▼
             eventos candidatos
                    │
                    ▼
              TICKET ASSISTANT
              CORE DETERMINÍSTICO
```

---

# 3. Estado actual del proyecto

## Ya construido

### Discovery

- Scanner de catálogo de Eden.
- Watchlist por artistas/palabras clave.
- Detección automática de eventos nuevos.

### Monitoring

- Monitor continuo.
- URLs directas.
- Watchlist.
- State machine.
- detección de cambios de disponibilidad.

### Providers

Existe abstracción:

```python
TicketProvider
```

y actualmente:

```python
EdenProvider
```

Esto permite convertir progresivamente Ticket Assistant en un sistema multi-ticketera.

### Notifications

Implementado:

- Telegram
- alertas sonoras

**Punto del antiguo roadmap correspondiente a Telegram: COMPLETADO.**

### Browser Assistant

Implementado:

- Playwright;
- navegador visible;
- perfiles persistentes;
- sesiones;
- preparación de checkout;
- separación por perfiles;
- checkpoint humano final.

### Storage

SQLite con:

- `events_history`;
- `snapshots`;
- `artist_profiles`;
- `first_seen_at`;
- `sold_out_at`;
- tiempo observado hasta sold-out;
- estado final.

### Intelligence

Existe:

```python
TicketIntelligenceEngine
```

que actualmente utiliza:

- priors por artista;
- histórico almacenado;
- ajustes geográficos;
- tasa histórica de sold-out;
- tiempo medio observado.

---

# 4. Problema principal de la V1 actual

Actualmente existen probabilidades precargadas por artista, por ejemplo conceptualmente:

```text
Q' Lokura → 95%
DesaKTa2  → 92%
La Mona   → 98%
```

Esto sirve como prototipo, pero no constituye una probabilidad estadística estimada.

Por lo tanto, el próximo gran objetivo será sustituir:

```text
baseline_probability
```

por:

```text
SoldOutScore
+
DataConfidence
```

basados en observaciones históricas.

---

# 5. Ticket Intelligence V1

## Objetivo

Responder antes de la apertura:

> ¿Qué tan atractivo es monitorear este evento debido a su riesgo de sold-out?

No intentaremos inicialmente afirmar:

```text
P(SoldOut) = 91%
```

Diremos:

```text
Sold-Out Score = 91/100
Confidence = HIGH
```

---

# 6. Sold-Out Score V1

El score será:

\[
Score =
0.35A +
0.30L +
0.15V +
0.10P +
0.10D
\]

donde:

| Componente | Peso |
|---|---:|
| Artist History | 35% |
| Local Performance | 30% |
| Venue Scarcity | 15% |
| Price Attractiveness | 10% |
| Date Quality | 10% |

Cada componente tendrá escala:

```text
0 — 100
```

---

# 7. Artist History Score

Mide la capacidad reciente del artista para agotar eventos.

Primera versión:

\[
A =
\frac{SoldOuts}{Eventos}
\times 100
\]

Idealmente usando aproximadamente los últimos:

```text
10 eventos relevantes
```

Posteriormente se agregará peso por recencia.

Ejemplo:

```text
Últimos 10 eventos Q' Lokura
9 sold-out

Artist Score = 90
```

---

# 8. Recency Weighting

No debe valer lo mismo:

```text
sold-out hace 2 meses
```

que:

```text
sold-out hace 4 años
```

Se incorporará progresivamente un decay temporal.

Conceptualmente:

\[
w_t=e^{-\lambda t}
\]

y:

\[
A=
100
\frac{\sum w_i SoldOut_i}
{\sum w_i}
\]

Esto permitirá que la inteligencia se adapte a cambios de popularidad.

---

# 9. Local Performance Score

El cuarteto tiene un componente geográfico particularmente importante.

Prioridad de búsqueda:

```text
1. Artista + Río Cuarto
2. Artista + Córdoba
3. Artista + Villa María
4. Ciudades comparables
5. Histórico general
```

Ejemplo:

```text
Q' Lokura
Río Cuarto

5 eventos
5 sold-out
```

No se asignará automáticamente 100%.

Se utilizará suavizado estadístico para evitar conclusiones extremas con pocas observaciones.

---

# 10. Bayesian Smoothing

Para muestras pequeñas:

\[
ScoreLocal =
100
\frac{s+\alpha p}
{n+\alpha}
\]

donde:

- `s` = sold-outs observados;
- `n` = eventos observados;
- `p` = tasa base del mercado;
- `α` = fuerza del prior.

Esto evita:

```text
1 evento
1 sold-out
= 100% aparente
```

---

# 11. Venue Scarcity Score

Se construirá una base propia de venues.

Ejemplo:

```text
venues

Opus Costanera
Predio West
Plaza de la Música
Atenas
Kempes
Movistar Arena
...
```

Campos:

```text
venue_id
name
city
province
capacity_estimate
venue_type
capacity_confidence
```

Inicialmente la escasez podrá clasificarse:

```text
VERY_HIGH
HIGH
NORMAL
LOW
VERY_LOW
```

Más adelante:

\[
DemandPressure =
\frac{ExpectedDemand}
{VenueCapacity}
\]

---

# 12. Price Attractiveness Score

No deben compararse precios nominales argentinos de distintos períodos.

Se almacenará:

```text
nominal_price
real_price
price_date
```

Los precios históricos podrán convertirse utilizando:

- IPC;
- eventualmente USD de referencia.

Indicador:

\[
PriceRatio =
\frac{PrecioActual}
{MedianaPrecioComparable}
\]

Ejemplo:

```text
<= 0.80 → score muy alto
0.80–0.95 → alto
0.95–1.05 → normal
1.05–1.20 → bajo
>1.20 → muy bajo
```

---

# 13. Date Quality Score

Variables posibles:

```text
viernes
sábado
domingo
feriado
víspera de feriado
vacaciones
evento especial
competencia simultánea
otro show reciente del artista
```

Inicialmente funcionará como sistema de reglas.

Posteriormente los pesos podrán aprenderse de los datos.

---

# 14. Data Confidence

Debe estar separado del Sold-Out Score.

Ejemplo:

```text
Sold-Out Score: 91/100
Confidence: HIGH
Observaciones relevantes: 24
```

Una primera aproximación:

\[
Confidence = 1-e^{-n/10}
\]

Aproximadamente:

```text
5 eventos   → 39
10 eventos  → 63
20 eventos  → 86
30 eventos  → 95
```

Interpretación:

> Confidence mide suficiencia de evidencia, no probabilidad de acertar.

---

# 15. Dataset histórico inicial

No se buscarán cientos de eventos para comenzar.

Objetivo inicial:

```text
20–30 eventos relevantes
```

Priorizando:

### Artistas

- Q' Lokura
- DesaKTa2
- La Konga
- Euge Quevedo / LBC
- La Mona
- Luck Ra

### Mercados

1. Río Cuarto
2. Córdoba
3. Villa María
4. ciudades comparables

### Campos

```text
event_id
artist_id
event_name
city
venue
event_date
sale_start_at
price_initial
capacity_estimate
sold_out
sold_out_at
time_to_sold_out
source
source_confidence
```

---

# 16. Mejorar el schema temporal

Actualmente deben diferenciarse claramente:

```text
announced_at
sale_start_at
first_seen_at
available_at
sold_out_at
```

Porque:

```text
first_seen_at
```

no necesariamente equivale a:

```text
sale_start_at
```

El tiempo correcto de agotamiento será:

\[
T_{SoldOut}
=
SoldOutAt-SaleStartAt
\]

cuando ambos timestamps sean conocidos.

---

# 17. Event Model V2

Crear entidades explícitas:

```text
Artist
Venue
Event
Sale
Snapshot
Prediction
Outcome
Provider
```

Evitar inferir permanentemente el artista a partir del nombre del evento.

Ejemplo futuro:

```text
artists
venues
events
event_artists
predictions
availability_snapshots
outcomes
providers
```

---

# 18. Prediction Record

Cada predicción deberá quedar congelada antes de la venta.

Ejemplo:

```text
prediction_id
event_id
calculated_at
sold_out_score
confidence
artist_score
local_score
venue_score
price_score
date_score
model_version
```

Esto es fundamental.

Nunca se debe recalcular retroactivamente una predicción y fingir que ese fue el valor original.

---

# 19. Outcome Record

Después del evento:

```text
event_id
sold_out
sold_out_at
time_to_sold_out
final_status
```

Opcionalmente, para análisis propio:

```text
operation_result
```

pero el predictor debe poder funcionar independientemente de cualquier resultado económico posterior.

---

# 20. Aprendizaje continuo

El sistema genera su propio dataset.

Ejemplo:

```text
12:00 AVAILABLE
12:05 AVAILABLE
12:20 sector agotado
12:40 AVAILABLE
13:10 casi agotado
14:32 SOLD_OUT
```

Ticket Assistant obtiene:

```text
sale_start = 12:00
sold_out = 14:32
time_to_sold_out = 152 min
```

Esto vale más que muchos datos históricos reconstruidos.

---

# 21. State Machine general

Estados propuestos:

```text
DISCOVERED
    ↓
ANALYZED
    ↓
WATCH
    ↓
PRIORITY
    ↓
READY
    ↓
LIVE
    ↓
AVAILABLE
    ↓
SOLD_OUT
```

Estados alternativos:

```text
CANCELLED
POSTPONED
UNKNOWN
ERROR
```

---

# 22. Política inicial del score

Ejemplo:

```text
0–59
IGNORE

60–74
WATCH

75–84
CANDIDATE

85–100
HIGH PRIORITY
```

Los thresholds no deben quedar hardcodeados permanentemente.

Deben ser configuración.

---

# 23. Preparación previa a la apertura

Para eventos `HIGH PRIORITY`:

```text
event_id
provider
sale_start_at
target_quantity
preferred_sector
fallback_sector
max_price
buyer_profile
execution_mode
```

Todo debe quedar configurado **antes de la apertura**.

---

# 24. Execution Layer

El objetivo es que la ejecución sea deliberadamente simple:

```text
Predicción
    ↓
Decisión
    ↓
Preparación
    ↓
Venta abre
    ↓
Monitor detecta
    ↓
Browser Assistant
    ↓
Checkout permitido
    ↓
Checkpoint humano
```

El sistema no debe diseñarse para:

- superar límites por comprador;
- evadir CAPTCHA;
- falsear identidades;
- eludir sistemas de cola;
- evadir controles antifraude;
- saltar restricciones de la ticketera.

---

# 25. Monitor adaptativo

No tiene sentido utilizar la misma frecuencia constantemente.

Ejemplo:

```text
>24h antes
polling bajo

1–24h
polling moderado

<30 minutos
polling mayor

venta abierta
modo live
```

Manteniendo siempre una política conservadora respecto de infraestructura y límites de cada proveedor.

---

# 26. Snapshots

Continuar almacenando:

```text
timestamp
status
available_shows
min_price
max_price
```

Futuro:

```text
available_sectors
sold_out_sectors
ticket_types
sale_phase
lot
```

Solo cuando estos datos sean públicamente observables.

---

# 27. Métricas de inteligencia

Cuando exista suficiente histórico:

### Precision

De los eventos marcados HIGH PRIORITY:

> ¿Cuántos realmente agotaron?

### False Positive Rate

> ¿Cuántos fueron clasificados como excelentes y no agotaron?

### Recall

> ¿Cuántos sold-outs importantes detectamos previamente?

### Brier Score

Cuando existan probabilidades.

### Calibration Error

Cuando exista modelo probabilístico.

---

# 28. Backtesting

Cada nueva versión del scorer deberá probarse contra eventos históricos.

Regla:

> El modelo solo puede utilizar información que estaba disponible antes de la venta.

Pipeline:

```text
Historical Event
        ↓
ocultar resultado
        ↓
generar features
        ↓
calcular score
        ↓
revelar resultado
        ↓
evaluar
```

---

# 29. Conversión futura Score → Probability

Una vez acumuladas suficientes observaciones:

```text
Score 90–100
34 eventos
32 sold-out
```

entonces:

\[
P(SoldOut|Score90-100)
=
32/34
\]

Podremos empezar a mostrar:

```text
SOLD-OUT SCORE
92/100

HISTORICAL CALIBRATED PROBABILITY
94%
```

---

# 30. Modelo estadístico futuro

Cuando exista suficiente información:

### Primera opción

Logistic Regression.

\[
P(Y=1|X)
=
\frac{1}
{1+e^{-(\beta_0+\beta X)}}
\]

### Posteriormente

Evaluar:

- Bayesian Logistic Regression;
- Gradient Boosting;
- Survival Analysis;
- calibrated classifiers.

Deep Learning no es necesario para este problema inicialmente.

---

# 31. Survival Analysis

Una evolución importante será dejar de preguntar solamente:

> ¿hará sold-out?

y preguntar:

> ¿cuánto tardará?

Objetivo:

\[
P(T_{SoldOut}<t)
\]

Ejemplo:

```text
P(Sold-out < 1h)   34%
P(Sold-out < 6h)   71%
P(Sold-out < 24h)  92%
```

Esto requiere un dataset significativamente mayor.

No pertenece a V1.

---

# 32. Multi-ticketera

Ticket Assistant no debe convertirse en:

```text
eden-bot
```

Debe ser:

```text
Ticket Assistant
   ├── Eden
   ├── Provider B
   ├── Provider C
   └── ...
```

---

# 33. Provider Architecture

Ya existe conceptualmente:

```python
TicketProvider
```

Cada nueva plataforma implementará su propio adapter.

Ejemplo:

```text
providers/
│
├── base.py
│
├── eden/
│   ├── provider.py
│   ├── parser.py
│   ├── scanner.py
│   └── ...
│
├── provider_b/
│   ├── provider.py
│   ├── parser.py
│   ├── scanner.py
│   └── ...
│
└── provider_c/
```

---

# 34. Contrato común de providers

Cada provider debería poder resolver al menos:

```python
get_event()
get_event_status()
search_events()
close()
```

Posteriormente:

```python
get_sale_start()
get_availability()
get_sectors()
normalize_url()
health_check()
```

si son aplicables.

---

# 35. Estados normalizados

Cada ticketera puede utilizar estados diferentes.

Ticket Assistant deberá traducirlos a:

```text
UNKNOWN
ANNOUNCED
COMING_SOON
AVAILABLE
PARTIAL
SOLD_OUT
CANCELLED
POSTPONED
```

Ejemplo:

```text
Eden:
"Comprar"

Provider B:
"Tickets disponibles"

Provider C:
saleStatus = ON_SALE
```

Todos terminan como:

```python
EventStatus.AVAILABLE
```

---

# 36. Refactor importante del monitor

Actualmente Eden todavía forma parte directa del monitor.

Objetivo futuro:

```python
provider = provider_registry.get(event.provider)
```

en lugar de:

```python
self.eden_provider
```

Arquitectura:

```text
UnifiedMonitor
      │
ProviderRegistry
      │
 ┌────┼────┐
Eden  B    C
```

---

# 37. Provider Registry

Crear:

```text
ProviderRegistry
```

que permita:

```python
providers["eden"]
providers["provider_b"]
```

El monitor deja de conocer plataformas concretas.

---

# 38. Segunda ticketera

No intentar implementar diez plataformas simultáneamente.

Procedimiento:

```text
1. estabilizar Eden
2. implementar inteligencia V1
3. elegir segunda ticketera
4. implementar Adapter B
5. observar diferencias reales
6. mejorar la abstracción
```

La segunda plataforma servirá como prueba de arquitectura.

---

# 39. Tests contractuales de providers

Todos los adapters deberán pasar los mismos tests:

```text
puede identificar un evento
normaliza nombre
normaliza status
normaliza ciudad
normaliza venue
maneja 404
maneja rate limit
maneja cambios de estructura
cierra conexiones correctamente
```

---

# 40. Provider Health

Agregar:

```text
HEALTHY
DEGRADED
BROKEN
BLOCKED
UNKNOWN
```

Ticket Assistant debe poder detectar cuando una ticketera cambia su HTML/estructura.

---

# 41. Observabilidad

Logs por:

```text
event_id
provider
timestamp
state
latency
prediction_id
browser_session
```

Métricas:

```text
monitor latency
provider errors
parser failures
state transitions
notification latency
browser launch time
```

---

# 42. Dashboard V1

No hace falta inicialmente una gran aplicación web.

Primera UI:

```text
EVENTO
ARTISTA
CIUDAD
VENUE
TICKETERA
SALE START
SCORE
CONFIDENCE
STATUS
PRIORITY
LAST CHECK
```

Ejemplo:

```text
Q' Lokura — Río Cuarto

Sold-Out Score      91
Confidence          HIGH
Provider            Eden
Sale                18/08 12:00
Status              READY
Priority            HIGH
```

---

# 43. Watchlist avanzada

Actualmente la watchlist utiliza artistas/palabras clave.

Evolución:

```text
artist
genre
city
province
venue
minimum_score
provider
```

Ejemplo:

```yaml
artist: "Q' Lokura"
region: "Cordoba"
minimum_score: 80
```

---

# 44. Event Discovery Engine

Fuentes posibles:

### Nivel 1

Ticketeras soportadas.

### Nivel 2

Webs oficiales de venues.

### Nivel 3

Webs oficiales de artistas.

### Nivel 4

Fuentes externas de eventos.

### Nivel 5

Agentes opcionales para fuentes no estructuradas.

---

# 45. Foco inicial: Cuarteto

La primera versión de inteligencia debe especializarse.

No intentar mezclar inmediatamente:

```text
Q' Lokura
Taylor Swift
River vs Boca
festival electrónico
```

porque las dinámicas de demanda son diferentes.

Primera taxonomía:

```text
EventDomain = MUSIC
Genre = CUARTETO
Region = CORDOBA
```

---

# 46. Expansión a otros recitales

Una vez validado cuarteto:

```text
MUSIC
├── CUARTETO
├── ROCK
├── URBANO
├── POP
├── ELECTRONICA
└── INTERNATIONAL
```

Cada segmento podrá tener:

- priors diferentes;
- features diferentes;
- pesos diferentes;
- comportamiento geográfico diferente.

---

# 47. Expansión al fútbol

Fútbol debe tratarse como **otro dominio**, no simplemente como otro género de evento.

```text
EventDomain = FOOTBALL
```

Variables adicionales:

```text
home_team
away_team
competition
stage
derby
table_position
importance
stadium
capacity
membership_priority
public_sale
ticket_transferability
```

Ejemplos de factores:

```text
clásico
fase eliminatoria
final
rival histórico
Copa Libertadores
partido decisivo
capacidad
cantidad habilitada al público
```

---

# 48. Football Intelligence Engine

A largo plazo:

\[
FootballDemandScore =
f(
teams,
competition,
importance,
stadium,
capacity,
history,
public_allocation,
date
)
\]

No compartir directamente el modelo estadístico del cuarteto.

Sí compartir:

- infraestructura;
- providers;
- database;
- snapshots;
- monitoring;
- scoring framework;
- confidence;
- backtesting;
- alerts.

---

# 49. Arquitectura objetivo de largo plazo

```text
                     EVENT SOURCES
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
    Ticketeras          Venues           Discovery
        │                                   Agents
        └─────────────────┬─────────────────┘
                          │
                    Event Discovery
                          │
                          ▼
                 Event Normalization
                          │
                          ▼
                    EVENT DATABASE
                          │
             ┌────────────┴────────────┐
             │                         │
       Historical Data             Live Data
             │                         │
             └────────────┬────────────┘
                          │
                          ▼
                  FEATURE ENGINE
                          │
                          ▼
                INTELLIGENCE ENGINE
                          │
             ┌────────────┴────────────┐
             │                         │
       Sold-Out Score             Confidence
             │                         │
             └────────────┬────────────┘
                          │
                          ▼
                    DECISION ENGINE
                          │
                 ┌────────┴────────┐
                 │                 │
               Ignore           Priority
                                   │
                                   ▼
                               Watchlist
                                   │
                                   ▼
                                Monitor
                                   │
                             Sale detected
                                   │
                                   ▼
                           Browser Assistant
                                   │
                                   ▼
                           Human Checkpoint
```

---

# 50. Roadmap por fases

## FASE 0 — Base actual

**Estado: mayormente completada**

- [x] Python project
- [x] Eden Provider
- [x] Eden Scanner
- [x] Watchlist
- [x] Direct URL Monitor
- [x] State Machine
- [x] Telegram
- [x] Sound Alerts
- [x] SQLite
- [x] Snapshots
- [x] Browser Assistant
- [x] Persistent Sessions
- [x] Human Checkpoint
- [x] TicketProvider abstraction
- [x] Intelligence Engine prototipo
- [x] CLI
- [x] Preflight
- [x] Tests base

---

## FASE 1 — Intelligence V1

**Prioridad: máxima**

- [ ] Eliminar probabilities hardcodeadas como output principal
- [ ] Implementar `SoldOutScore`
- [ ] Implementar `DataConfidence`
- [ ] Crear `ArtistScore`
- [ ] Crear `LocalScore`
- [ ] Crear `VenueScore`
- [ ] Crear `PriceScore`
- [ ] Crear `DateScore`
- [ ] Agregar recency weighting
- [ ] Implementar Bayesian smoothing
- [ ] Parametrizar pesos
- [ ] Parametrizar thresholds
- [ ] Versionar scorer

**Resultado esperado:**

```text
Score + Confidence
```

---

## FASE 2 — Historical Dataset

- [ ] Seleccionar 5–7 artistas iniciales
- [ ] Reconstruir 20–30 eventos relevantes
- [ ] Registrar fuentes
- [ ] Registrar confidence de cada dato
- [ ] Crear tabla Artists
- [ ] Crear tabla Venues
- [ ] Mejorar Events
- [ ] Agregar `sale_start_at`
- [ ] Agregar `announced_at`
- [ ] Agregar capacidad estimada
- [ ] Agregar precio histórico
- [ ] Normalizar precio argentino

---

## FASE 3 — Prediction Tracking

- [ ] Crear tabla Predictions
- [ ] Congelar score pre-sale
- [ ] Crear Outcomes
- [ ] Asociar Prediction → Outcome
- [ ] Guardar model version
- [ ] Guardar features individuales
- [ ] Crear histórico de aciertos
- [ ] Crear histórico de errores

---

## FASE 4 — Monitoring Intelligence

- [ ] Polling adaptativo
- [ ] Registrar `sale_start`
- [ ] Medir tiempo real hasta sold-out
- [ ] Ampliar snapshots
- [ ] Detectar agotamiento parcial si es observable
- [ ] Registrar cambios por sector/lote cuando sea público
- [ ] Métricas de latencia
- [ ] Provider health

---

## FASE 5 — Backtesting

- [ ] Backtest del scorer
- [ ] Precision
- [ ] Recall
- [ ] False Positive Rate
- [ ] análisis por artista
- [ ] análisis por ciudad
- [ ] análisis por venue
- [ ] análisis por rango de score
- [ ] comparar versiones del scorer

---

## FASE 6 — Core Multi-Provider

- [ ] Provider Registry
- [ ] eliminar dependencia directa Eden del UnifiedMonitor
- [ ] normalizar estados
- [ ] normalizar modelos
- [ ] tests contractuales de Provider
- [ ] provider health checks
- [ ] configuración por proveedor

---

## FASE 7 — Segunda Ticketera

- [ ] Seleccionar Provider B
- [ ] Analizar arquitectura pública
- [ ] Crear Adapter
- [ ] Crear Parser
- [ ] Crear Scanner cuando corresponda
- [ ] Crear Browser Flow específico
- [ ] Pasar Provider Contract Tests
- [ ] Integrar con UnifiedMonitor
- [ ] Integrar con histórico
- [ ] Comparar Eden vs Provider B
- [ ] refactorizar solamente las abstracciones demostradas necesarias

---

## FASE 8 — UI / Dashboard

- [ ] Eventos descubiertos
- [ ] Watchlist
- [ ] Score
- [ ] Confidence
- [ ] Provider
- [ ] Sale Start
- [ ] Status
- [ ] Priority
- [ ] Predictions
- [ ] Historical Outcomes
- [ ] Provider Health

---

## FASE 9 — Probability Calibration

**Requiere dataset suficiente.**

- [ ] Agrupar eventos por score
- [ ] calcular frecuencia real de sold-out
- [ ] calibration curve
- [ ] Brier Score
- [ ] Logistic Regression
- [ ] comparar contra scorer heurístico
- [ ] calibrar outputs
- [ ] empezar a mostrar probabilidades

Resultado:

```text
Sold-Out Score: 92
Historical Probability: 91%
Confidence: HIGH
```

---

## FASE 10 — Otros géneros musicales

- [ ] Crear EventDomain
- [ ] Crear Genre
- [ ] Rock
- [ ] Urbano
- [ ] Pop
- [ ] Electrónica
- [ ] internacional
- [ ] parámetros específicos por segmento
- [ ] backtesting independiente

---

## FASE 11 — AI Discovery opcional

Solo después de consolidar el core.

Posibles herramientas:

- Hermes
- OpenClaw
- otros agents/harnesses

Objetivos:

- [ ] buscar nuevos anuncios
- [ ] leer fuentes no estructuradas
- [ ] completar venue
- [ ] completar capacidad
- [ ] descubrir nuevas fechas
- [ ] generar candidatos

Los agentes nunca reemplazan el scorer determinístico.

---

## FASE 12 — Football Domain

- [ ] EventDomain.FOOTBALL
- [ ] Teams
- [ ] Competitions
- [ ] Stadiums
- [ ] MatchImportance
- [ ] Derby
- [ ] TicketAllocation
- [ ] PublicSale
- [ ] FootballDemandScore
- [ ] histórico
- [ ] backtesting
- [ ] providers correspondientes

---

# 51. Prioridades inmediatas

No avanzar simultáneamente en todo.

Orden recomendado desde el estado actual:

### Sprint 1

```text
SoldOutScore
DataConfidence
eliminar hardcoded probabilities
```

### Sprint 2

```text
schema histórico V2
Artists
Venues
Events
Predictions
```

### Sprint 3

```text
dataset inicial 20–30 eventos
Q' Lokura
DesaKTa2
La Konga
Euge/LBC
La Mona
Luck Ra
```

### Sprint 4

```text
backtesting inicial
ajuste de pesos
ajuste de thresholds
```

### Sprint 5

```text
prediction tracking
outcomes
learning loop
```

### Sprint 6

```text
desacoplar UnifiedMonitor de Eden
ProviderRegistry
Provider contract tests
```

### Sprint 7

```text
segunda ticketera
```

---

# 52. Qué NO construir todavía

No priorizar:

- Deep Learning;
- modelos complejos;
- agentes autónomos;
- vector databases;
- RAG;
- arquitecturas distribuidas complejas;
- microservicios;
- Kubernetes;
- gran dashboard;
- diez ticketeras;
- fútbol;
- análisis nacional completo.

El objetivo inmediato es conseguir:

> **un sistema simple que clasifique correctamente eventos de cuarteto de alta demanda en Córdoba/Río Cuarto.**

---

# 53. Ventaja acumulativa

El mayor activo futuro de Ticket Assistant no será Playwright.

Tampoco EdenProvider.

Será:

```text
EVENT INTELLIGENCE DATASET
```

Cada día de funcionamiento agrega:

```text
evento
artista
venue
ciudad
precio
fecha
apertura
estado
snapshots
sold-out
tiempo hasta sold-out
predicción previa
resultado real
```

Por lo tanto, el sistema mejora incluso cuando no se ejecuta ninguna compra.

---

# 54. North Star

La evolución conceptual será:

```text
V0
Monitor de Eden

↓

V1
Monitor + Purchase Assistant

↓

V2
Ticket Intelligence

↓

V3
Sold-Out Prediction System

↓

V4
Multi-Ticketing Event Intelligence

↓

V5
Multi-Domain High-Demand Event Intelligence
```

El objetivo de largo plazo puede resumirse como:

> **Construir un sistema que descubra eventos, estime anticipadamente su presión de demanda, priorice aquellos con mayor riesgo de agotamiento, monitorice su apertura y prepare la ejecución con mínima latencia, independientemente de la ticketera o del tipo de evento.**

---

# 55. Arquitectura tecnológica recomendada

Mantener:

```text
Python
AsyncIO
HTTPX
Playwright
SQLite
Telegram
Pytest
YAML
```

Más adelante:

```text
SQLite
    ↓
PostgreSQL
```

solo cuando exista una necesidad concreta:

- múltiples workers;
- servidor remoto;
- dashboard;
- concurrencia elevada;
- histórico grande;
- acceso desde diferentes máquinas.

No migrar por anticipación.

---

# 56. Criterio de éxito de V1 Intelligence

La primera versión estará validada cuando:

1. utilice datos reales;
2. no dependa de probabilidades arbitrarias por artista;
3. explique por qué asignó un score;
4. exprese incertidumbre;
5. pueda reproducir el resultado;
6. pueda realizar backtesting;
7. registre predicción antes del evento;
8. compare posteriormente predicción vs realidad;
9. mejore conforme acumula datos;
10. funcione completamente sin LLM.

---

# 57. Próximo objetivo concreto

**Ticket Intelligence V1.**

Entregable:

```text
Event
  ↓
FeatureExtractor
  ↓
ArtistScore
LocalScore
VenueScore
PriceScore
DateScore
  ↓
SoldOutScore
  ↓
DataConfidence
  ↓
Decision
```

Output esperado:

```text
Q' LOKURA — RÍO CUARTO
──────────────────────────────

Sold-Out Score        91 / 100
Confidence            HIGH

Artist History        93
Local Performance     96
Venue Scarcity        87
Price                  76
Date                   91

Historical Sample     24

Classification:
HIGH PRIORITY
```

Este debe ser el siguiente bloque importante de desarrollo antes de agregar nuevas plataformas o dominios.
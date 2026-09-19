# Design Decisions

## 1. Scope and system boundary

The assignment has two concrete data paths:

1. Sensor measurements arrive through `POST /sensor-data` and are stored.
2. Device commands arrive through `POST /device-control` and are published to
   MQTT.

The objective mentions an IoT-to-MQTT-to-backend flow at a high level, but the
implementation requirements explicitly define sensor ingestion as an HTTP API.
The design follows the concrete endpoint requirements and uses MQTT where its
asynchronous, device-oriented semantics add value.

The solution remains a modular monolith. Redis, Kafka, Kubernetes, additional
microservices, and AI were intentionally excluded because the current workload
does not justify their operational cost.

## 2. Why FastAPI

FastAPI provides request routing, dependency injection, lifecycle hooks, OpenAPI,
and Pydantic integration in a compact codebase. Those capabilities directly serve
the assignment:

- Pydantic makes the API contract executable and visible in Swagger.
- Dependency injection separates HTTP concerns from services and repositories.
- Lifespan hooks give the MQTT client explicit startup and shutdown ownership.
- Synchronous handlers run in FastAPI's worker threadpool, so the synchronous
  SQLAlchemy session does not block the event loop.

A larger team might standardize on another framework, but changing frameworks
would not materially improve this scope.

## 3. Why PostgreSQL, SQLAlchemy, and Alembic

PostgreSQL was chosen over SQLite because concurrent writers, durable storage,
timezone-aware timestamps, operational tooling, and production migration paths
are relevant to real IoT ingestion. It also makes dependency health meaningful.

SQLAlchemy 2 provides explicit sessions, transaction control, connection pooling,
and a clean ORM model. The write transaction is owned by `SensorService`:

```text
API -> Pydantic schema -> SensorService -> SensorRepository -> SQLAlchemy -> PostgreSQL
```

The repository maps and stages the row; the service commits or rolls back. This
keeps transaction policy out of the HTTP route and avoids hiding commits inside
low-level persistence methods.

Alembic, rather than `Base.metadata.create_all`, owns schema evolution. The Docker
entrypoint runs `alembic upgrade head` before Uvicorn, giving a reviewer a
repeatable first startup and preserving a versioned upgrade path.

The implementation uses synchronous SQLAlchemy because each request performs one
small transaction and the simpler failure semantics are valuable here. If profiling
showed connection wait or threadpool pressure at higher ingestion rates, an async
driver/session or buffered ingestion path would be evaluated.

## 4. Why `recorded_at` and `created_at` are separate

`recorded_at` is supplied by the sensor and represents measurement time.
`created_at` is assigned by PostgreSQL and represents persistence time.

IoT networks can be delayed or intermittently offline. Replacing the sensor time
with server receipt time would make delayed readings appear current and would hide
transport latency. Keeping both values supports:

- ingestion-delay measurement;
- late-data detection;
- correct time-series ordering;
- troubleshooting device clocks and network outages.

In production, device clock quality would also be monitored because a timezone-
aware timestamp can still be inaccurate.

## 5. Why one persistent MQTT client

Opening and closing a broker connection for every HTTP command adds TCP/MQTT
handshake latency, wastes broker resources, and loses useful connection state.
Instead, FastAPI owns one Paho client for the complete application lifecycle:

- startup creates the client and starts its network loop;
- callbacks update `connected` or `disconnected` state;
- every command reuses that client;
- unexpected disconnects use Paho's bounded reconnect delay;
- shutdown disconnects and stops the loop.

This also gives `/status` a real state to report instead of attempting a fresh,
artificial connection on every health request.

## 6. MQTT topic and payload design

Commands use:

```text
greenhouse/control/{device_id}
```

The hierarchy is predictable and allows a device to subscribe only to its own
topic while operators can observe all commands with `greenhouse/control/#`.
Device identifiers are constrained before entering the topic, preventing wildcard
characters or arbitrary topic injection.

The payload repeats `device_id`, includes the command, and adds a backend-generated
UTC timestamp. Repeating the identity makes captured messages self-describing and
easier to audit without relying only on topic metadata.

## 7. Why QoS 1 and retain disabled

Device commands are more consequential than routine telemetry. QoS 0 could report
HTTP success after a local send without broker acknowledgement. QoS 1 makes the
backend wait for Mosquitto's PUBACK before returning success.

QoS 1 is at-least-once, not exactly-once. Duplicate delivery remains possible, so
ON/OFF handling should be idempotent. At larger scale, commands would also carry a
unique command ID that devices persist and deduplicate.

Retain is deliberately disabled. A stale retained `ON` command could be delivered
to a device that reconnects hours later. Persisted desired-state control would be
a separate, explicit design rather than an accidental side effect of retained
command messages.

## 8. Health semantics

`GET /status` checks dependencies rather than returning constants:

- backend is `up` if it can produce the response;
- database performs `SELECT 1` through the configured engine;
- MQTT reads callback-maintained connection state.

The endpoint returns HTTP 200 with `status: degraded` when a dependency is down.
This response is a successful health report containing an unhealthy dependency,
not a failed attempt to produce the report. Deployment platforms could split this
into shallow liveness and strict readiness endpoints later.

Database connections use a bounded timeout so health and API failures do not hang
indefinitely when PostgreSQL is unreachable.

## 9. Partial failure and error policy

PostgreSQL and MQTT fail independently:

- If PostgreSQL is unavailable, sensor writes roll back and return
  `DATABASE_UNAVAILABLE`.
- If MQTT is disconnected or PUBACK does not arrive, commands return
  `MQTT_UNAVAILABLE`.
- If either dependency is down, `/status` reports `degraded` while unaffected
  operations can continue.

All expected errors use a stable machine-readable code and safe message.
Validation failures add field-level details. Driver exceptions, connection URLs,
passwords, and stack traces go to internal logs only. This gives clients actionable
responses without leaking infrastructure information.

The direct HTTP-to-MQTT publish path is intentionally simple. It means a command
is not durably queued while the broker is offline; the caller receives 503 and can
retry. A production requirement for offline command acceptance would require a
durable command table and an outbox/dispatcher, not a silent in-memory queue.

## 10. Why Docker Compose

Compose packages the backend, PostgreSQL, and Mosquitto into one reproducible
review environment. Service healthchecks and dependency ordering remove manual
installation and startup races. The backend image runs as a non-root user and
applies Alembic migrations before serving traffic.

Compose is appropriate for a technical test and local development. It is not
presented as the final production orchestrator.

## 11. Testing strategy

The automated suite favors behavior with high regression value:

- successful sensor persistence through service and repository layers;
- invalid types, humidity limits, unknown fields, and malformed JSON;
- structured device command publication with QoS 1;
- missing or unsupported device commands;
- broker-unavailable error behavior;
- healthy and degraded dependency states;
- consistent framework and application error envelopes.

Unit/API tests use an isolated in-memory database where appropriate. Manual
integration tests run the real Compose stack to verify PostgreSQL migrations,
actual row persistence, MQTT subscriber delivery, dependency shutdown, recovery,
and safe 503 responses.

## 12. What would change at production scale

The current boundaries allow incremental evolution without immediately splitting
the service:

### Security

- Store secrets in a managed secret service rather than `.env`.
- Require MQTT authentication and TLS; disable anonymous broker access.
- Add HTTP authentication/authorization and device-level command permissions.
- Add request-size limits, rate limits, and audit logs.

### Reliability

- Run PostgreSQL with backups, replication, and managed failover.
- Run a clustered MQTT broker with persistent sessions where appropriate.
- Add command IDs, device acknowledgements, idempotency, and command expiry.
- Use a transactional outbox plus dispatcher if commands must survive broker
  outages after the HTTP request is accepted.
- Separate migration execution into a deployment job when multiple backend
  replicas start concurrently.

### Scale

- Measure before introducing buffering. If sensor write volume exceeds direct
  PostgreSQL capacity, batch ingestion or a durable event stream can be added.
- Partition sensor data by time/device and define retention/downsampling policies.
- Size SQLAlchemy pools per replica and enforce database connection budgets.
- Each backend replica may own an MQTT client; client IDs and reconnect behavior
  would need deliberate coordination.

### Operability

- Emit structured JSON logs, metrics, traces, and correlation IDs.
- Split liveness, readiness, and detailed operator health endpoints.
- Track publish latency, PUBACK failures, DB pool saturation, ingestion delay,
  validation rejection rate, and reconnect count.
- Add CI checks for tests, migration drift, image builds, and vulnerability scans.

These additions are deferred because they solve production requirements that are
outside the assignment, not because the current design assumes they are
unnecessary forever.

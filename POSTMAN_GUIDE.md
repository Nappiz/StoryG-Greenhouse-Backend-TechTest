# Postman Testing Guide

This guide verifies the complete API contract, validation behavior, PostgreSQL
persistence, MQTT delivery, health reporting, dependency failures, and recovery.

## 1. Start and verify the stack

From the project directory:

```bash
docker compose up -d --build
docker compose ps
```

All three services should be `healthy`:

- `backend`
- `postgres`
- `mosquitto`

Confirm Swagger is reachable at <http://localhost:8000/docs>.

## 2. Import the Postman files

In Postman:

1. Click **Import**.
2. Import `postman/Greenhouse-IoT-Backend.postman_collection.json`.
3. Import `postman/Greenhouse-IoT-Backend.postman_environment.json`.
4. Select **Greenhouse IoT Backend - Local** from the environment selector.
5. Confirm `base_url` is `http://localhost:8000`.

The collection creates a fresh RFC 3339 timestamp before every request. A
successful sensor request also saves its generated database ID as the collection
variable `sensor_reading_id`.

## 3. Run the normal health checks

Open folder **01 - Basic and Health**.

### Root - Backend Running

Expected:

- HTTP `200`
- Message: `Greenhouse IoT Backend is running`
- Both Postman tests pass.

### Status - Healthy

Expected:

```json
{
  "status": "healthy",
  "services": {
    "backend": "up",
    "database": "connected",
    "mqtt": "connected"
  }
}
```

If this is degraded, resolve the dependency before continuing:

```bash
docker compose ps
docker compose logs --tail 50 backend postgres mosquitto
```

## 4. Test sensor ingestion

Open folder **02 - Sensor Data** and send each request separately.

### Sensor - Valid

Expected:

- HTTP `201`.
- `success` is `true`.
- `data.id` is a positive integer.

Verify the database row through DBeaver:

1. Open the `greenhouse` connection.
2. Navigate to `Schemas -> public -> Tables -> sensor_readings`.
3. Right-click the table and choose **View Data -> All Rows**.
4. Find `device_id = sensor-postman-001`.

Equivalent SQL:

```sql
SELECT
    id,
    device_id,
    temperature,
    humidity,
    recorded_at,
    created_at,
    created_at - recorded_at AS ingest_delay
FROM sensor_readings
WHERE device_id = 'sensor-postman-001'
ORDER BY id DESC;
```

The remaining sensor requests should return HTTP `422` with
`error.code = VALIDATION_ERROR`:

- **Sensor - Empty Device ID**
- **Sensor - Humidity Above 100**
- **Sensor - Temperature as String**
- **Sensor - Invalid Timestamp**
- **Sensor - Malformed JSON**

Confirm that invalid requests do not create additional database rows.

## 5. Test device control and MQTT delivery

Before sending the Postman requests, open a separate terminal and start a real
subscriber:

```bash
docker compose exec mosquitto mosquitto_sub \
  -h localhost \
  -t "greenhouse/control/#" \
  -q 1 \
  -v
```

PowerShell accepts the command on one line:

```powershell
docker compose exec mosquitto mosquitto_sub -h localhost -t "greenhouse/control/#" -q 1 -v
```

Open folder **03 - Device Control**.

### Device - ON

Expected Postman response: HTTP `200` and command `ON`.

Expected subscriber output resembles:

```text
greenhouse/control/fan-postman-001 {"device_id":"fan-postman-001","command":"ON","timestamp":"2026-09-19T10:35:00Z"}
```

### Device - OFF

Expected Postman response: HTTP `200`, with an `OFF` event appearing in the
subscriber.

### Invalid commands

Both requests should return HTTP `422` and `VALIDATION_ERROR`:

- **Device - Invalid START Command**
- **Device - Missing Device ID**

No MQTT message should appear for either invalid request.

Stop the subscriber with `Ctrl+C` after this section.

## 6. Test Mosquitto failure and recovery

Do not use Postman's **Run collection** for this folder because the dependency must
be changed between requests.

Stop Mosquitto:

```bash
docker compose stop mosquitto
```

Wait two or three seconds, then send:

1. **04 - Dependency Failure -> Status - MQTT Down**
2. **04 - Dependency Failure -> Device - MQTT Down**

Expected status:

```json
{
  "status": "degraded",
  "services": {
    "backend": "up",
    "database": "connected",
    "mqtt": "disconnected"
  }
}
```

Expected device response: HTTP `503`:

```json
{
  "success": false,
  "error": {
    "code": "MQTT_UNAVAILABLE",
    "message": "MQTT broker is unavailable"
  }
}
```

Restart Mosquitto:

```bash
docker compose start mosquitto
```

The Paho client reconnects automatically. Wait until **Status - Recovered** passes.
This can take several seconds because reconnect delay is bounded rather than a busy
loop.

## 7. Test PostgreSQL failure and recovery

Make sure Mosquitto has recovered, then stop PostgreSQL:

```bash
docker compose stop postgres
```

Send:

1. **04 - Dependency Failure -> Status - Database Down**
2. **04 - Dependency Failure -> Sensor - Database Down**

The health request may take a few seconds because the database connection timeout
is deliberately bounded instead of failing from a cached value.

Expected status:

```json
{
  "status": "degraded",
  "services": {
    "backend": "up",
    "database": "disconnected",
    "mqtt": "connected"
  }
}
```

Expected sensor response: HTTP `503`:

```json
{
  "success": false,
  "error": {
    "code": "DATABASE_UNAVAILABLE",
    "message": "Database is unavailable"
  }
}
```

Restart PostgreSQL:

```bash
docker compose start postgres
```

Wait for `docker compose ps` to show PostgreSQL as healthy, then send
**Status - Recovered**. All dependencies should be connected again.

## 8. Suggested final evidence

Capture these results for the submission or presentation:

1. Postman `201` response from **Sensor - Valid**.
2. DBeaver row containing `sensor-postman-001`.
3. Postman `200` response from **Device - ON**.
4. Terminal subscriber showing the structured ON command.
5. Healthy `/status` response.
6. Degraded status while Mosquitto is stopped.
7. Degraded status while PostgreSQL is stopped.
8. Postman test results showing the validation cases pass.

## 9. Return the system to a healthy state

```bash
docker compose start postgres mosquitto backend
docker compose ps
```

Finish by sending **01 - Basic and Health -> Status - Healthy**. All Postman tests
should pass.

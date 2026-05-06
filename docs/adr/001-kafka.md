# ADR-001 — Apache Kafka for Event Streaming

**Status:** Accepted  
**Date:** 2026-05-06  
**Deciders:** Platform Engineering, Data Science

---

## Context

The Burnout & Cognitive Load Guardrail ingests collaboration metadata from four source systems (Slack, Google Calendar, Jira, GitHub) continuously. Each system emits events at different rates and with different schemas. The ingestion layer needs to:

- Buffer high-volume bursts without dropping events.
- Decouple producers (connectors) from consumers (ETL pipeline) so each can scale independently.
- Provide durable, replayable event storage to support backfills and DAG re-runs.
- Enforce schema contracts so upstream changes don't silently break the pipeline.

The two main candidates evaluated were **Apache Kafka** and **AWS SQS**.

---

## Decision

Use **Apache Kafka** (via AWS MSK in staging/production, via Confluent's Docker image locally) as the event streaming backbone.

Use the **Confluent Schema Registry** alongside Kafka to enforce Avro schemas on all topics.

---

## Rationale

| Criterion | Kafka | SQS |
|---|---|---|
| Message retention & replay | Configurable (days–forever) | Max 14 days, no replay |
| Consumer groups | Multiple independent consumers | One consumer deletes the message |
| Throughput | Millions of events/sec | ~3,000 msg/sec standard tier |
| Schema enforcement | Native via Schema Registry | No built-in schema support |
| Local development | Docker image (cp-kafka) | Requires LocalStack or mocks |
| Operational complexity | Higher | Lower |

The replay capability is the decisive factor: the ETL pipeline must support idempotent backfills up to 30 days. SQS's 14-day retention cap and lack of offset-based replay make it incompatible with this requirement.

The higher operational complexity of Kafka is mitigated by using **AWS MSK** (managed Kafka) in cloud environments, which eliminates broker management overhead.

---

## Consequences

**Positive:**
- Complete decoupling of ingestion speed from pipeline processing speed.
- Dead-letter queue (DLQ) topic pattern for malformed events without blocking producers.
- Schema Registry prevents silent schema drift from breaking downstream consumers.
- `docker compose up` gives engineers a complete local Kafka environment in seconds.

**Negative:**
- Kafka requires Zookeeper (or KRaft mode in ≥3.3) — more containers locally.
- MSK costs ~$0.21/broker-hour — three brokers = ~$450/month for staging.
- Avro serialization adds a schema compilation step to producer development.

**Mitigations:**
- Schema Registry runs locally in the same `docker-compose.yml`.
- MSK staging instance can be stopped outside working hours to reduce cost.

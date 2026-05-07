"""Kafka producer service with Schema Registry integration, DLQ, and retry.

Wire format: Confluent Schema Registry (magic byte 0x00 + 4-byte schema_id BE + Avro binary).
Failed deliveries are routed to dlq.{topic} as JSON envelopes for operational inspection.
"""

from __future__ import annotations

import asyncio
import io
import json
import logging
import struct
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import fastavro
import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from ingestion.models import BaseEvent

try:
    from confluent_kafka import KafkaException, Producer
except ImportError:  # allow import in environments without confluent_kafka
    Producer = None  # type: ignore[assignment,misc]
    KafkaException = Exception  # type: ignore[assignment,misc]

logger = logging.getLogger(__name__)

_MAGIC_BYTE = 0  # Confluent Schema Registry wire format header
_DLQ_PREFIX = "dlq"
_FLUSH_TIMEOUT_SECONDS = 30.0


class KafkaDeliveryError(Exception):
    """Raised when a message cannot be delivered after all retries."""


@dataclass
class _DeliveryResult:
    """Mutable container for confluent_kafka delivery callback state."""

    success: bool = False
    error: str = ""


class KafkaProducerService:
    """
    Async-friendly Kafka producer wrapping confluent_kafka.Producer.

    Usage:
        producer = KafkaProducerService(bootstrap_servers=..., schema_registry_url=..., schemas_dir=...)
        producer.load_schema("raw.slack.activity", "slack_activity.avsc")
        producer.register_schema("raw.slack.activity")   # optional; falls back to id=1 in dev
        await producer.produce_event("raw.slack.activity", event)
        await producer.flush()
    """

    def __init__(
        self,
        bootstrap_servers: str,
        schema_registry_url: str,
        schemas_dir: Path,
        *,
        producer_config: dict[str, str | int | bool] | None = None,
        _producer: Any | None = None,  # Any: confluent_kafka.Producer; injected in tests
    ) -> None:
        if _producer is not None:
            self._producer = _producer
        elif Producer is not None:
            config: dict[str, str | int | bool] = {
                "bootstrap.servers": bootstrap_servers,
                "acks": "all",
                "enable.idempotence": True,
                "retries": 2_147_483_647,  # max int — rely on delivery.timeout.ms
                "max.in.flight.requests.per.connection": 5,
                "delivery.timeout.ms": 120_000,
                **(producer_config or {}),
            }
            self._producer = Producer(config)
        else:
            raise RuntimeError("confluent_kafka is not installed.")

        self._schema_registry_url = schema_registry_url.rstrip("/")
        self._schemas_dir = schemas_dir
        # Any: fastavro parsed schema — no public type exposed by fastavro stubs
        self._parsed_schemas: dict[str, Any] = {}
        self._schema_ids: dict[str, int] = {}

    # ── Schema management ────────────────────────────────────────────────────

    def load_schema(self, topic: str, schema_filename: str) -> None:
        """Parse an Avro schema file and associate it with a topic.

        Call once at startup before any produce_event() calls.
        """
        schema_path = self._schemas_dir / schema_filename
        with schema_path.open() as f:
            raw: dict[str, object] = json.load(f)
        self._parsed_schemas[topic] = fastavro.parse_schema(raw)
        self._schema_ids.setdefault(topic, 1)
        logger.debug("Loaded schema for topic %s from %s", topic, schema_path)

    def register_schema(self, topic: str) -> int:
        """Register the topic's schema with the Schema Registry.

        Returns the assigned schema_id. Falls back to id=1 if the Schema Registry
        is unreachable — this allows local development without a running SR instance.
        """
        if topic not in self._parsed_schemas:
            raise ValueError(
                f"Schema for topic '{topic}' not loaded. Call load_schema() first."
            )

        # Derive filename from topic name (dots → underscores)
        filename = topic.replace(".", "_") + ".avsc"
        schema_path = self._schemas_dir / filename
        try:
            response = httpx.post(
                f"{self._schema_registry_url}/subjects/{topic}-value/versions",
                json={"schema": schema_path.read_text()},
                timeout=10.0,
            )
            response.raise_for_status()
            schema_id: int = response.json()["id"]
            self._schema_ids[topic] = schema_id
            logger.info("Registered schema for %s: schema_id=%d", topic, schema_id)
            return schema_id
        except httpx.HTTPError as exc:
            logger.warning(
                "Schema Registry unreachable (%s). Using schema_id=1 for %s (dev mode).",
                exc,
                topic,
            )
            return 1

    # ── Event production ─────────────────────────────────────────────────────

    async def produce_event(self, topic: str, event: BaseEvent) -> None:
        """Serialize event to Avro and produce to the Kafka topic asynchronously."""
        schema = self._parsed_schemas.get(topic)
        if schema is None:
            raise ValueError(
                f"No schema loaded for topic '{topic}'. Call load_schema() first."
            )
        schema_id = self._schema_ids.get(topic, 1)
        payload = self._serialize(event.model_dump(mode="json"), schema, schema_id)
        await asyncio.to_thread(
            self._produce_with_retry, topic, payload, event.event_id
        )

    async def flush(self, timeout: float = _FLUSH_TIMEOUT_SECONDS) -> None:
        """Block until all queued messages are acknowledged or the timeout expires."""
        await asyncio.to_thread(self._producer.flush, timeout)

    # ── Internal ─────────────────────────────────────────────────────────────

    def _serialize(
        self,
        data: dict[str, object],
        schema: Any,  # fastavro ParsedSchema — no public type in stubs
        schema_id: int,
    ) -> bytes:
        buf = io.BytesIO()
        buf.write(struct.pack(">bI", _MAGIC_BYTE, schema_id))  # 5-byte SR header
        fastavro.schemaless_writer(buf, schema, data)  # type: ignore[arg-type]
        return buf.getvalue()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(BufferError),
        reraise=True,
    )
    def _produce_with_retry(
        self, topic: str, payload: bytes, event_id: str
    ) -> None:
        """Produce a single message synchronously (called inside asyncio.to_thread)."""
        result = _DeliveryResult()

        def on_delivery(err: object, _msg: object) -> None:
            if err:
                result.error = str(err)
            else:
                result.success = True

        try:
            self._producer.produce(topic, value=payload, callback=on_delivery)
            unflushed = self._producer.flush(timeout=_FLUSH_TIMEOUT_SECONDS)
            if unflushed > 0:
                result.error = f"Flush timed out; {unflushed} message(s) unacknowledged"
        except KafkaException as exc:
            raise KafkaDeliveryError(
                f"KafkaException producing to {topic}: {exc}"
            ) from exc

        if not result.success:
            logger.error(
                "Delivery failed for event %s on topic %s: %s",
                event_id,
                topic,
                result.error,
            )
            self._send_to_dlq(topic, payload, result.error, event_id)

    def _send_to_dlq(
        self,
        original_topic: str,
        payload: bytes,
        error: str,
        event_id: str,
    ) -> None:
        """Route a failed message to the DLQ topic as a JSON envelope."""
        dlq_topic = f"{_DLQ_PREFIX}.{original_topic}"
        envelope = json.dumps(
            {
                "original_topic": original_topic,
                "event_id": event_id,
                "error": error,
                "payload_hex": payload.hex(),
                "failed_at": datetime.now(tz=timezone.utc).isoformat(),
            }
        ).encode()
        try:
            self._producer.produce(dlq_topic, value=envelope)
            self._producer.poll(0)
            logger.warning(
                "Event %s routed to DLQ topic %s", event_id, dlq_topic
            )
        except KafkaException:
            logger.exception(
                "Failed to route event %s to DLQ topic %s — event is lost",
                event_id,
                dlq_topic,
            )

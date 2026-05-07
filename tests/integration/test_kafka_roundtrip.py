"""Integration test: KafkaProducerService → Kafka → consumer round-trip.

Requires a running Kafka + Schema Registry stack.
Gate: set KAFKA_INTEGRATION_TEST=true in the environment.

Run with:
    docker compose up -d
    KAFKA_INTEGRATION_TEST=true pytest tests/integration/ -v -s
"""

from __future__ import annotations

import io
import json
import os
import struct
import uuid
from datetime import datetime, timezone
from pathlib import Path

import fastavro
import pytest

from ingestion.models import SlackActivityEvent
from ingestion.producer import KafkaProducerService

_INTEGRATION_ENABLED = os.getenv("KAFKA_INTEGRATION_TEST", "false").lower() == "true"
_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
_SCHEMA_REGISTRY_URL = os.getenv("KAFKA_SCHEMA_REGISTRY_URL", "http://localhost:8081")
_SCHEMAS_DIR = Path(__file__).parents[2] / "ingestion" / "schemas"
_TOPIC = "raw.slack.activity"
_SCHEMA_FILE = "slack_activity.avsc"


pytestmark = pytest.mark.skipif(
    not _INTEGRATION_ENABLED,
    reason="Set KAFKA_INTEGRATION_TEST=true to run Kafka integration tests",
)


@pytest.fixture()
def producer() -> KafkaProducerService:
    svc = KafkaProducerService(
        bootstrap_servers=_BOOTSTRAP,
        schema_registry_url=_SCHEMA_REGISTRY_URL,
        schemas_dir=_SCHEMAS_DIR,
    )
    svc.load_schema(_TOPIC, _SCHEMA_FILE)
    svc.register_schema(_TOPIC)
    return svc


@pytest.fixture()
def consumer():  # type: ignore[no-untyped-def]
    try:
        from confluent_kafka import Consumer  # type: ignore[import-untyped]
    except ImportError:
        pytest.skip("confluent_kafka not installed")

    c = Consumer(
        {
            "bootstrap.servers": _BOOTSTRAP,
            "group.id": f"test-roundtrip-{uuid.uuid4()}",
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
        }
    )
    c.subscribe([_TOPIC])
    yield c
    c.close()


@pytest.mark.asyncio
async def test_slack_event_kafka_roundtrip(
    producer: KafkaProducerService,
    consumer: object,
) -> None:
    event = SlackActivityEvent(
        workspace_id="W_INTEGRATION",
        team_id="T_INTEGRATION",
        channel_id="C_INTEGRATION",
        hour_bucket_utc=datetime(2024, 1, 15, 14, 0, tzinfo=timezone.utc),
        message_count=42,
        is_after_hours=False,
        day_of_week=0,
    )

    await producer.produce_event(_TOPIC, event)
    await producer.flush()

    # Poll until we find our message (max 10 seconds)
    received = None
    for _ in range(20):
        msg = consumer.poll(0.5)  # type: ignore[union-attr]
        if msg is None or msg.error():
            continue
        received = msg
        break

    assert received is not None, "No message received from Kafka within timeout"
    assert received.error() is None

    payload: bytes = received.value()

    # Verify Confluent Schema Registry wire format header
    magic, schema_id = struct.unpack(">bI", payload[:5])
    assert magic == 0, "Expected Schema Registry magic byte 0x00"
    assert schema_id >= 1

    # Deserialize Avro payload
    schema_dict = json.loads((_SCHEMAS_DIR / _SCHEMA_FILE).read_text())
    schema = fastavro.parse_schema(schema_dict)
    record = fastavro.schemaless_reader(io.BytesIO(payload[5:]), schema)

    assert record["workspace_id"] == "W_INTEGRATION"
    assert record["team_id"] == "T_INTEGRATION"
    assert record["message_count"] == 42
    assert record["is_after_hours"] is False

    # Verify no PII fields exist in the record
    pii_fields = {"user_id", "user_name", "text", "message_body", "email"}
    assert not pii_fields.intersection(record.keys()), (
        f"PII fields found in Kafka message: {pii_fields.intersection(record.keys())}"
    )

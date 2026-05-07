"""Unit tests for KafkaProducerService."""

from __future__ import annotations

import io
import json
import struct
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import fastavro
import pytest

from ingestion.models import SlackActivityEvent
from ingestion.producer import KafkaProducerService, _DLQ_PREFIX, _MAGIC_BYTE

_SCHEMAS_DIR = Path(__file__).parents[3] / "ingestion" / "schemas"
_TOPIC = "raw.slack.activity"
_SCHEMA_FILE = "slack_activity.avsc"


def _make_service(mock_producer: MagicMock) -> KafkaProducerService:
    svc = KafkaProducerService(
        bootstrap_servers="localhost:9092",
        schema_registry_url="http://localhost:8081",
        schemas_dir=_SCHEMAS_DIR,
        _producer=mock_producer,
    )
    svc.load_schema(_TOPIC, _SCHEMA_FILE)
    return svc


def _make_event() -> SlackActivityEvent:
    return SlackActivityEvent(
        workspace_id="W001",
        team_id="T001",
        channel_id="C001",
        hour_bucket_utc=datetime(2024, 1, 15, 14, 0, tzinfo=timezone.utc),
        message_count=5,
        is_after_hours=False,
        day_of_week=0,
    )


# ── produce_event ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_producer_produce_event_calls_kafka_produce(
    mock_producer: MagicMock,
) -> None:
    svc = _make_service(mock_producer)
    event = _make_event()

    await svc.produce_event(_TOPIC, event)

    assert mock_producer.produce.called
    call_args = mock_producer.produce.call_args
    assert call_args[0][0] == _TOPIC or call_args[1].get("topic") == _TOPIC or _TOPIC == call_args[0][0]


@pytest.mark.asyncio
async def test_producer_payload_uses_schema_registry_wire_format(
    mock_producer: MagicMock,
) -> None:
    svc = _make_service(mock_producer)
    event = _make_event()

    await svc.produce_event(_TOPIC, event)

    payload: bytes = mock_producer.produce.call_args[1].get("value") or mock_producer.produce.call_args[0][1]
    # Verify Confluent wire format: byte 0 = magic, bytes 1-4 = schema_id
    magic, schema_id = struct.unpack(">bI", payload[:5])
    assert magic == _MAGIC_BYTE


@pytest.mark.asyncio
async def test_producer_payload_is_valid_avro(
    mock_producer: MagicMock,
) -> None:
    svc = _make_service(mock_producer)
    event = _make_event()

    await svc.produce_event(_TOPIC, event)

    payload: bytes = mock_producer.produce.call_args[1].get("value") or mock_producer.produce.call_args[0][1]
    schema_json = (_SCHEMAS_DIR / _SCHEMA_FILE).read_text()
    parsed = fastavro.parse_schema(json.loads(schema_json))

    avro_bytes = payload[5:]  # strip 5-byte header
    record = fastavro.schemaless_reader(io.BytesIO(avro_bytes), parsed)
    assert record["workspace_id"] == "W001"
    assert record["team_id"] == "T001"
    assert record["message_count"] == 5


@pytest.mark.asyncio
async def test_producer_raises_value_error_when_schema_not_loaded(
    mock_producer: MagicMock,
) -> None:
    svc = KafkaProducerService(
        bootstrap_servers="localhost:9092",
        schema_registry_url="http://localhost:8081",
        schemas_dir=_SCHEMAS_DIR,
        _producer=mock_producer,
    )
    event = _make_event()

    with pytest.raises(ValueError, match="No schema loaded"):
        await svc.produce_event("unknown.topic", event)


# ── DLQ routing ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_producer_routes_to_dlq_on_delivery_failure(
    mock_producer: MagicMock,
) -> None:
    """When the delivery callback reports an error, message goes to DLQ."""
    svc = _make_service(mock_producer)
    event = _make_event()

    # Make the delivery callback fire with an error
    def produce_side_effect(topic: str, value: bytes, callback=None, **_: object) -> None:
        if callback and not topic.startswith(_DLQ_PREFIX):
            callback("Broker not available", None)

    mock_producer.produce.side_effect = produce_side_effect
    mock_producer.flush.return_value = 0

    await svc.produce_event(_TOPIC, event)

    # Second produce call must be to the DLQ topic
    dlq_call = mock_producer.produce.call_args_list[1]
    dlq_topic = dlq_call[0][0] if dlq_call[0] else dlq_call[1].get("topic", "")
    assert dlq_topic == f"{_DLQ_PREFIX}.{_TOPIC}"


@pytest.mark.asyncio
async def test_producer_dlq_envelope_is_valid_json(
    mock_producer: MagicMock,
) -> None:
    svc = _make_service(mock_producer)
    event = _make_event()

    def produce_side_effect(topic: str, value: bytes, callback=None, **_: object) -> None:
        if callback and not topic.startswith(_DLQ_PREFIX):
            callback("Simulated delivery failure", None)

    mock_producer.produce.side_effect = produce_side_effect
    mock_producer.flush.return_value = 0

    await svc.produce_event(_TOPIC, event)

    dlq_payload: bytes = mock_producer.produce.call_args_list[1][1].get("value") or (
        mock_producer.produce.call_args_list[1][0][1]
        if len(mock_producer.produce.call_args_list[1][0]) > 1
        else b"{}"
    )
    envelope = json.loads(dlq_payload.decode())
    assert envelope["original_topic"] == _TOPIC
    assert "error" in envelope
    assert "payload_hex" in envelope
    assert "failed_at" in envelope
    assert "event_id" in envelope


# ── load_schema / register_schema ─────────────────────────────────────────────

def test_producer_load_schema_parses_correctly(mock_producer: MagicMock) -> None:
    svc = _make_service(mock_producer)
    assert _TOPIC in svc._parsed_schemas  # noqa: SLF001


def test_producer_load_schema_raises_on_missing_file(mock_producer: MagicMock) -> None:
    svc = KafkaProducerService(
        bootstrap_servers="localhost:9092",
        schema_registry_url="http://localhost:8081",
        schemas_dir=_SCHEMAS_DIR,
        _producer=mock_producer,
    )
    with pytest.raises(FileNotFoundError):
        svc.load_schema("raw.fake.topic", "nonexistent.avsc")

"""KafkaBatchConsumeOperator — reads one day of Avro events from a Kafka topic.

Design constraints:
- Each DAG run creates a unique consumer group so re-runs always start fresh.
- Events are filtered to date_filter (YYYY-MM-DD) using the `date_utc` or
  `hour_bucket_utc` field inside the deserialized record.
- Avro deserialization strips the 5-byte Confluent Schema Registry wire-format
  header and uses the schema file on disk (schemas_dir / schema_file).
- Returns a list[dict] via XCom — must be JSON-serialisable.
"""

from __future__ import annotations

import io
import json
import logging
import os
import struct
import uuid
from pathlib import Path
from typing import Any

import fastavro

logger = logging.getLogger(__name__)

_MAGIC_BYTE: int = 0
_SR_HEADER_SIZE: int = 5
_POLL_TIMEOUT_S: float = 2.0
_MAX_EMPTY_POLLS: int = 10  # stop after this many consecutive empty polls


class KafkaBatchConsumeOperator:
    """Airflow operator that reads all events for a given date from a Kafka topic.

    Extend ``airflow.models.BaseOperator`` when Airflow is available.  Kept as a
    plain class here so it can be unit-tested without an Airflow installation.

    Args:
        topic: Kafka topic to consume from.
        schema_file: Avro schema filename inside schemas_dir.
        date_filter: ISO-8601 date string (YYYY-MM-DD) — only events matching
                     this date in their ``date_utc`` or ``hour_bucket_utc`` field
                     are returned.
        bootstrap_servers: Kafka broker address(es).
        schemas_dir: Directory containing Avro schema files.
        task_id: Unique identifier for this operator instance (used in consumer group).
    """

    def __init__(
        self,
        topic: str,
        schema_file: str,
        date_filter: str,
        bootstrap_servers: str = "localhost:9092",
        schemas_dir: Path | None = None,
        task_id: str = "consume",
    ) -> None:
        self.topic = topic
        self.schema_file = schema_file
        self.date_filter = date_filter
        self.bootstrap_servers = bootstrap_servers
        self.schemas_dir = schemas_dir or Path(__file__).parents[2] / "ingestion" / "schemas"
        self.task_id = task_id

    def _load_schema(self) -> Any:
        schema_path = self.schemas_dir / self.schema_file
        return fastavro.parse_schema(json.loads(schema_path.read_text()))

    def _deserialize(self, raw: bytes, schema: Any) -> dict[str, Any]:
        magic, _ = struct.unpack(">bI", raw[:_SR_HEADER_SIZE])
        if magic != _MAGIC_BYTE:
            raise ValueError(f"Unexpected magic byte: {magic}")
        return fastavro.schemaless_reader(io.BytesIO(raw[_SR_HEADER_SIZE:]), schema)

    def _matches_date(self, record: dict[str, Any]) -> bool:
        for field in ("date_utc", "hour_bucket_utc"):
            val = record.get(field, "")
            if str(val)[:10] == self.date_filter:
                return True
        return False

    def execute(self, run_id: str | None = None) -> list[dict[str, Any]]:
        """Consume and return all matching records for self.date_filter.

        Args:
            run_id: Airflow run_id string used to make the consumer group unique.
                    Falls back to a random UUID when not provided.

        Returns:
            List of JSON-serialisable dicts (Avro records matching date_filter).
        """
        try:
            from confluent_kafka import Consumer, TopicPartition  # type: ignore[import-untyped]
            from confluent_kafka import OFFSET_BEGINNING  # type: ignore[import-untyped]
        except ImportError as exc:
            raise RuntimeError("confluent_kafka is required for KafkaBatchConsumeOperator") from exc

        safe_run_id = (run_id or str(uuid.uuid4())).replace(":", "_").replace("+", "_")
        group_id = f"airflow-{self.task_id}-{safe_run_id}"

        consumer = Consumer(
            {
                "bootstrap.servers": self.bootstrap_servers,
                "group.id": group_id,
                "auto.offset.reset": "earliest",
                "enable.auto.commit": False,
            }
        )

        schema = self._load_schema()
        records: list[dict[str, Any]] = []

        try:
            meta = consumer.list_topics(self.topic, timeout=10)
            partitions = [
                TopicPartition(self.topic, p, OFFSET_BEGINNING)
                for p in meta.topics[self.topic].partitions
            ]
            consumer.assign(partitions)

            empty_polls = 0
            while empty_polls < _MAX_EMPTY_POLLS:
                msg = consumer.poll(timeout=_POLL_TIMEOUT_S)
                if msg is None:
                    empty_polls += 1
                    continue
                if msg.error():
                    logger.warning("Kafka error on %s: %s", self.topic, msg.error())
                    empty_polls += 1
                    continue
                empty_polls = 0
                try:
                    record = self._deserialize(msg.value(), schema)
                    if self._matches_date(record):
                        records.append(record)
                except Exception:
                    logger.exception("Failed to deserialize message from %s", self.topic)

        finally:
            consumer.close()

        logger.info(
            "Consumed %d records for date=%s from topic=%s",
            len(records),
            self.date_filter,
            self.topic,
        )
        return records

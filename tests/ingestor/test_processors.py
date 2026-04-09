import json
import unittest

from iot_platform.contracts import ValidationError
from services.ingestor.app.processors import build_operations


class ProcessorTests(unittest.TestCase):
    def test_builds_measurement_insert(self) -> None:
        operations = build_operations(
            "raw.telemetry",
            {
                "eventId": "evt-001",
                "siteId": "site-alpha",
                "assetId": "crusher-01",
                "signalId": "motor_current",
                "quality": "good",
                "ts_source": "2026-04-09T08:00:00Z",
                "ts_ingest": "2026-04-09T08:00:01Z",
                "seq": 101,
                "unit": "A",
                "value": 42.8,
                "tags": {"area": "processing"},
                "traceId": "trace-001",
            },
        )
        self.assertEqual(len(operations), 1)
        self.assertIn("INSERT INTO measurements", operations[0].sql)
        self.assertEqual(operations[0].params[2], "evt-001")
        self.assertEqual(operations[0].params[9], 42.8)

    def test_builds_alarm_insert(self) -> None:
        operations = build_operations(
            "raw.alarms",
            {
                "eventId": "alm-001",
                "siteId": "site-alpha",
                "assetId": "crusher-01",
                "signalId": "bearing_temp",
                "quality": "bad",
                "ts_source": "2026-04-09T08:00:00Z",
                "ts_ingest": "2026-04-09T08:00:01Z",
                "seq": 102,
                "unit": "C",
                "value": 88.1,
                "tags": {"severity": "high", "message": "bearing temperature high"},
                "traceId": "trace-002",
            },
        )
        self.assertIn("INSERT INTO alarms", operations[0].sql)
        self.assertEqual(operations[0].params[1], "alm-001")
        self.assertEqual(operations[0].params[4], "high")

    def test_builds_model_score_insert(self) -> None:
        operations = build_operations(
            "analytics.inference",
            {
                "modelId": "vibration-anomaly",
                "siteId": "site-alpha",
                "assetId": "crusher-01",
                "signalId": "vibration_rms",
                "score": 0.82,
                "anomalous": True,
                "timestamp": "2026-04-09T08:05:00Z",
            },
        )
        self.assertIn("INSERT INTO model_scores", operations[0].sql)
        self.assertTrue(operations[0].params[6])

    def test_rejects_non_numeric_measurement(self) -> None:
        with self.assertRaises(ValidationError):
            build_operations(
                "raw.telemetry",
                {
                    "eventId": "evt-002",
                    "siteId": "site-alpha",
                    "assetId": "crusher-01",
                    "signalId": "status_text",
                    "quality": "good",
                    "ts_source": "2026-04-09T08:00:00Z",
                    "ts_ingest": "2026-04-09T08:00:01Z",
                    "seq": 103,
                    "unit": "",
                    "value": "running",
                    "tags": {},
                    "traceId": "trace-003",
                },
            )

    def test_builds_generic_event_insert(self) -> None:
        operations = build_operations(
            "raw.events",
            {
                "eventId": "evt-maint-01",
                "siteId": "site-alpha",
                "assetId": "pump-07",
                "eventType": "maintenance",
                "timestamp": "2026-04-09T08:10:00Z",
                "payload": {"workOrder": "WO-1"},
            },
        )
        self.assertIn("INSERT INTO events", operations[0].sql)
        self.assertEqual(json.loads(operations[0].params[5])["eventType"], "maintenance")


if __name__ == "__main__":
    unittest.main()

import json
import pathlib
import unittest

from iot_platform.contracts import (
    CommandRequest,
    DeviceRegistration,
    ModelDeployment,
    TelemetryEnvelope,
    ValidationError,
)


FIXTURES = pathlib.Path(__file__).resolve().parents[1] / "fixtures"


class ContractTests(unittest.TestCase):
    def test_telemetry_fixture_is_valid(self) -> None:
        payload = json.loads((FIXTURES / "sample_telemetry.json").read_text())
        envelope = TelemetryEnvelope.from_dict(payload)
        self.assertEqual(envelope.dedupe_key(), "site-alpha:motor_current:2026-04-09T08:00:00Z:101")

    def test_command_requires_known_priority(self) -> None:
        with self.assertRaises(ValidationError):
            CommandRequest.from_dict(
                {
                    "commandId": "cmd-001",
                    "siteId": "site-alpha",
                    "assetId": "pump-01",
                    "targetSignal": "speed_setpoint",
                    "requestedValue": 1400,
                    "requestedBy": "operator-7",
                    "priority": "urgent",
                    "expiresAt": "2026-04-09T09:00:00Z",
                }
            )

    def test_device_registration_requires_signal_map(self) -> None:
        with self.assertRaises(ValidationError):
            DeviceRegistration.from_dict(
                {
                    "siteId": "site-alpha",
                    "assetId": "tank-01",
                    "deviceId": "tank-gateway-1",
                    "protocol": "modbus-tcp",
                    "signalMap": {},
                    "units": {},
                    "samplingClass": "60s",
                }
            )

    def test_model_deployment_accepts_approved_state(self) -> None:
        deployment = ModelDeployment.from_dict(
            {
                "modelId": "vibration-anomaly",
                "version": "2026.04.09",
                "checksum": "sha256:abc123",
                "inputSchema": "telemetry-envelope-v1",
                "approvalState": "approved",
                "targetScope": "site-alpha",
            }
        )
        self.assertEqual(deployment.approval_state, "approved")


if __name__ == "__main__":
    unittest.main()

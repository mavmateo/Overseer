import unittest

from iot_platform.topics import TopicError, build_mqtt_topic, parse_mqtt_topic


class TopicTests(unittest.TestCase):
    def test_build_canonical_topic(self) -> None:
        topic = build_mqtt_topic("site-alpha", "processing", "crusher-01", "telemetry")
        self.assertEqual(topic, "site/site-alpha/area/processing/asset/crusher-01/telemetry")

    def test_parse_canonical_topic(self) -> None:
        parsed = parse_mqtt_topic("site/site-alpha/area/processing/asset/crusher-01/command/request")
        self.assertEqual(parsed.site_id, "site-alpha")
        self.assertEqual(parsed.channel, "command/request")

    def test_reject_invalid_channel(self) -> None:
        with self.assertRaises(TopicError):
            build_mqtt_topic("site-alpha", "processing", "crusher-01", "write")


if __name__ == "__main__":
    unittest.main()


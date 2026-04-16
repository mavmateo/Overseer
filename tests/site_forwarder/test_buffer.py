import pathlib
import sys
import tempfile
import threading
import unittest


SITE_FORWARDER_ROOT = pathlib.Path(__file__).resolve().parents[2] / "services" / "site-forwarder"
if str(SITE_FORWARDER_ROOT) not in sys.path:
    sys.path.insert(0, str(SITE_FORWARDER_ROOT))

from app.buffer import SpoolBuffer  # noqa: E402


class SpoolBufferTests(unittest.TestCase):
    def test_concurrent_enqueue_and_read_is_safe(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            buffer = SpoolBuffer(str(pathlib.Path(temp_dir) / "buffer.db"))
            errors: list[Exception] = []

            def writer(start: int) -> None:
                try:
                    for index in range(100):
                        offset = start + index
                        buffer.enqueue("raw.telemetry", f"key-{offset}", '{"value":1}')
                except Exception as exc:  # pragma: no cover - failure capture
                    errors.append(exc)

            def reader() -> None:
                try:
                    for _ in range(100):
                        buffer.pending(50)
                        buffer.depth()
                except Exception as exc:  # pragma: no cover - failure capture
                    errors.append(exc)

            threads = [
                threading.Thread(target=writer, args=(0,)),
                threading.Thread(target=writer, args=(1000,)),
                threading.Thread(target=reader),
            ]

            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()

            self.assertEqual(errors, [])
            self.assertEqual(buffer.depth(), 200)


if __name__ == "__main__":
    unittest.main()

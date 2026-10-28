import tempfile
import unittest
from pathlib import Path

from mt_agent.preview import preview_key


class PreviewSpeedTest(unittest.TestCase):
    def test_cle_vitesse(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "a.mp4"
            f.write_bytes(b"x")
            base = preview_key(f, 0.0, 3.0, 480)
            self.assertEqual(base, preview_key(f, 0.0, 3.0, 480, speed=1.0))
            ks = {base, preview_key(f, 0.0, 3.0, 480, speed=2.0), preview_key(f, 0.0, 3.0, 480, speed=0.5)}
            self.assertEqual(len(ks), 3)


if __name__ == "__main__":
    unittest.main()

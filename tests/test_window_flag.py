import unittest
from mt_agent.fit import window_flag

class WindowFlagTest(unittest.TestCase):
    def test_cas_connus(self) -> None:
        for d, want in [(2.99, "▼"), (2.996, ""), (3.0, ""), (5.0, ""), (5.004, ""), (5.01, "▲"), (9.9, "▲")]:
            with self.subTest(d=d):
                self.assertEqual(window_flag(d, 3.0, 5.0), want)

import random, unittest
from mt_agent.selection import parse_selection, spec_from_flags

class SpecFromFlagsTest(unittest.TestCase):
    def test_cas_connus(self) -> None:
        self.assertEqual(spec_from_flags([True, False, True, True, True]), "1,3-5")
        self.assertEqual(spec_from_flags([False, False]), "")
        self.assertEqual(spec_from_flags([]), "")
        self.assertEqual(spec_from_flags([True]), "1")

    def test_aller_retour(self) -> None:
        rng = random.Random(7)
        for _ in range(500):
            n = rng.randint(1, 60)
            flags = [rng.random() < 0.4 for _ in range(n)]
            spec = spec_from_flags(flags)
            if spec:
                self.assertEqual(parse_selection(spec, n), {i + 1 for i, f in enumerate(flags) if f})
            else:
                self.assertFalse(any(flags))

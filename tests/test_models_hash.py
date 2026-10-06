import unittest
from mt_agent.models import Options, Plan, Scene, Source

HASH_REF = "0b807715596e72b5c2ea77e71f36374ba06b87e35df1b1f1c0ea1945fbf8fdd5"  # calculé avant max_scene_seconds

def _plan(opt: Options | None = None) -> Plan:
    return Plan(options=opt or Options(), sources=[Source(id="a", path="inbox/a.mp4", duration=10.0)],
                scenes=[Scene(source_id="a", start=0.0, end=5.0, score=0.5, selected=True)])

class HashTest(unittest.TestCase):
    def test_hash_inchange_sans_max(self) -> None:
        self.assertEqual(_plan().content_hash(), HASH_REF)

    def test_hash_change_avec_max(self) -> None:
        self.assertNotEqual(_plan(Options(max_scene_seconds=5.0)).content_hash(), HASH_REF)

if __name__ == "__main__":
    unittest.main()

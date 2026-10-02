import json
import tempfile
import unittest
from pathlib import Path
from mt_agent import editor

class EditorTests(unittest.TestCase):
    def test_highlight_keeps_all_scenes_and_selects_requested_count(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original_root = editor.ROOT
            editor.ROOT = root
            (root / "projects").mkdir()
            source = root / "source.json"
            scenes = [{"id": f"scene-{i}", "start_seconds": float(i * 2), "end_seconds": float(i * 2 + 1.5), "selected": True} for i in range(12)]
            source.write_text(json.dumps({"plan_id": "base", "status": "pending_human_review", "human_validation": {"approved": False}, "scenes": scenes, "exports": [{"profile": "youtube"}]}))
            result = editor.propose_highlight(source, 4)
            plan = json.loads(result.read_text())
            self.assertEqual(len(plan["scenes"]), 12)
            self.assertEqual(sum(scene["selected"] for scene in plan["scenes"]), 4)
            self.assertFalse(plan["human_validation"]["approved"])
            editor.ROOT = original_root

if __name__ == "__main__":
    unittest.main()

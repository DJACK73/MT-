import json,unittest,tempfile,pathlib
from mt_agent.renderer import render
from pathlib import Path
class Contracts(unittest.TestCase):
 def test_profiles_and_schema(self):
  r=Path(__file__).resolve().parents[1]; c=json.loads((r/'config/config.json').read_text()); self.assertEqual(c['profiles']['youtube'],{'width':1920,'height':1080}); self.assertEqual(c['profiles']['vertical'],{'width':1080,'height':1920}); self.assertIn('pending_human_review',(r/'docs/PLAN_SCHEMA_V1.md').read_text())
 def test_render_refuses_unapproved_plan(self):
  with tempfile.NamedTemporaryFile(mode='w',suffix='.json') as f:
   json.dump({'status':'pending_human_review','human_validation':{'approved':False}},f); f.flush()
   with self.assertRaisesRegex(ValueError,'Validation humaine obligatoire'): render(f.name)
 def test_renderer_protects_existing_export(self):
  from mt_agent.renderer import render
  with tempfile.TemporaryDirectory() as directory:
   root = pathlib.Path(directory)
   plan = root / "plan.json"
   existing = root / "existing.mp4"
   existing.write_bytes(b"protected")
   plan.write_text(json.dumps({"status":"approved","human_validation":{"approved":True},"scenes":[{"selected":True}],"exports":[{"output":str(existing),"profile":"youtube"}],"source":{"path":"missing"},"plan_id":"test"}))
   with self.assertRaises(FileExistsError): render(plan)
if __name__=='__main__': unittest.main()




from pathlib import Path
import json
ROOT=Path('/app') if Path('/app/config/config.json').exists() else Path(__file__).resolve().parents[2]
def cfg(): return json.loads((ROOT/'config/config.json').read_text())

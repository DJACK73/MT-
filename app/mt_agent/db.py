from .config import ROOT
import sqlite3
def connect():
 p=ROOT/'data/mt.sqlite'; p.parent.mkdir(exist_ok=True); c=sqlite3.connect(p); c.execute('CREATE TABLE IF NOT EXISTS sources (sha256 TEXT PRIMARY KEY, path TEXT NOT NULL, plan_id TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP)'); return c
def known(sha): return connect().execute('SELECT 1 FROM sources WHERE sha256=?',(sha,)).fetchone() is not None
def add(sha,path,plan):
 c=connect(); c.execute('INSERT INTO sources VALUES (?,?,?,CURRENT_TIMESTAMP)',(sha,path,plan)); c.commit()

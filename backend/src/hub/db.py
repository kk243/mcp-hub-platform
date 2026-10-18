import json
import os
import sqlite3
from pathlib import Path

DB_PATH = Path(os.getenv("DB_PATH", "./data/hub.db"))
STORAGE_DIR = Path(os.getenv("STORAGE_DIR", "./storage"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS workflows (
  key TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT,
  family TEXT NOT NULL,
  team TEXT, owner TEXT,
  derived_from TEXT,
  tags TEXT DEFAULT '[]',
  biz_steps TEXT NOT NULL,
  code_nodes TEXT NOT NULL,
  code_edges TEXT NOT NULL,
  deprecated INTEGER DEFAULT 0,
  replaced_by TEXT,
  created_at TEXT
);

CREATE TABLE IF NOT EXISTS items (
  key TEXT PRIMARY KEY,
  type TEXT NOT NULL,
  name TEXT NOT NULL,
  description TEXT,
  team TEXT, owner TEXT,
  tags TEXT DEFAULT '[]',
  spec TEXT NOT NULL,
  entrypoint TEXT,
  code_hash TEXT,
  code_visibility TEXT DEFAULT 'private',
  allowlist TEXT DEFAULT '[]',
  deprecated INTEGER DEFAULT 0,
  replaced_by TEXT,
  created_at TEXT
);
"""

JSON_COLS = {"tags", "biz_steps", "code_nodes", "code_edges", "spec", "allowlist"}


def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with connect() as conn:
        conn.executescript(SCHEMA)


def to_dict(row):
    """sqlite Row → dict. JSON 컬럼은 파싱해서 돌려준다."""
    d = dict(row)
    for col in JSON_COLS & d.keys():
        d[col] = json.loads(d[col]) if d[col] else []
    return d


def fetch_all(sql, params=()):
    with connect() as conn:
        return [to_dict(r) for r in conn.execute(sql, params)]


def fetch_one(sql, params=()):
    with connect() as conn:
        row = conn.execute(sql, params).fetchone()
    return to_dict(row) if row else None

"""Apply UnoWord's checked-in Supabase migration through the transaction pooler."""

import os
from pathlib import Path
from urllib.parse import urlparse

import psycopg2
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BACKEND_DIR.parent
load_dotenv(BACKEND_DIR / ".env")

db_url = os.environ.get("SUPABASE_DB_URL", "")
parsed = urlparse(db_url)
if parsed.port != 6543 or not (parsed.hostname or "").endswith(".pooler.supabase.com"):
    raise RuntimeError("SUPABASE_DB_URL must be a Supabase Transaction Pooler URI on port 6543")

migration = ROOT_DIR / "supabase" / "migrations" / "20260929010000_ai_writing_coach_foundation.sql"
sql = migration.read_text(encoding="utf-8")

with psycopg2.connect(db_url, connect_timeout=20) as connection:
    with connection.cursor() as cursor:
        cursor.execute(sql)

print("Supabase AI foundation migration applied")
from pathlib import Path
import os
import psycopg

DSN = os.getenv("DATABASE_URL", "").replace("+psycopg", "")  # psycopg DSN

SCHEMA_PATH = Path(__file__).parent / "db" / "schema.sql"
SCHEMA = SCHEMA_PATH.read_text(encoding="utf-8")

def init_db():
    if not DSN:
        return
    with psycopg.connect(DSN) as conn:
        with conn.cursor() as cur:
            cur.execute(SCHEMA)
        conn.commit()

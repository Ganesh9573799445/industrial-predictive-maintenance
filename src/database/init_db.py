
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]

DB_DIR = BASE_DIR / "data" / "raw"
DB_PATH = DB_DIR / "predictive_maintenance.db"

SCHEMA_PATH = (
    BASE_DIR / "src" / "database" / "schema.sql"
)


def initialize_database():

    DB_DIR.mkdir(parents=True, exist_ok=True)

    schema = SCHEMA_PATH.read_text(encoding="utf-8")

    connection = sqlite3.connect(DB_PATH)

    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(schema)
        connection.commit()

        print("Database created successfully!")
        print(f"Database location: {DB_PATH}")

        tables = connection.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            ORDER BY name
        """).fetchall()

        print("\nCreated tables:")

        for table in tables:
            print("-", table[0])

    finally:
        connection.close()


if __name__ == "__main__":
    initialize_database()

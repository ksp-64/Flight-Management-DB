from pathlib import Path
import sqlite3

BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = BASE_DIR / "DB/FlightManagement.db"
SQL_DIR = BASE_DIR / "SQL"

SCHEMA_SQL = SQL_DIR / "00_Schema.sql"
VIEWS_SQL = SQL_DIR / "01_Views.sql"
TRIGGERS_SQL = SQL_DIR / "03_Triggers.sql"

INSERT_DIR = SQL_DIR / "Inserts"
INSERT_FILES = [
    "01_Airline.sql",
    "02_Airport.sql",
    "03_Aircraft.sql",
    "04_Route.sql",
    "05_Flight.sql",
    "06_FlightInstance.sql",
    "07_Staff.sql",
    "08_Passenger.sql",
    "09_Booking.sql",
    "10_CrewAssignment.sql",
    "11_BookingItem.sql"
]

REQUIRED_TABLES = {
    "AppContext",
    "Airline",
    "Airport",
    "Aircraft",
    "Route",
    "Flight",
    "FlightInstance",
    "Staff",
    "CrewAssignment",
    "Passenger",
    "Booking",
    "BookingItem",
    "AuditLog",
}

# Reads and executes a complete SQL script file.
def run_sql_file(conn: sqlite3.Connection, path: Path) -> None:
    conn.executescript(path.read_text(encoding="utf-8"))

def is_db_initialised() -> bool:
    if not DB_PATH.exists():
        return False
    if DB_PATH.stat().st_size == 0:
        return False

    try:
        with sqlite3.connect(DB_PATH) as conn:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table';"
            ).fetchall()
    except sqlite3.Error:
        return False

    existing_tables = {row[0] for row in rows}
    return REQUIRED_TABLES.issubset(existing_tables)


def ensure_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    DB_PATH.unlink(missing_ok=True)


    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA foreign_keys = ON;")

        run_sql_file(conn, SCHEMA_SQL)

        run_sql_file(conn, VIEWS_SQL)

        run_sql_file(conn, TRIGGERS_SQL)

        conn.execute("UPDATE AppContext SET CurrentUser='CLI' WHERE ContextID=1;")

        for filename in INSERT_FILES:
            run_sql_file(conn, INSERT_DIR / filename)

        conn.execute("UPDATE AppContext SET CurrentUser='USER' WHERE ContextID=1;")
        conn.commit()

# Refresh views/triggers without resetting data.
def ensure_runtime_objects() -> None:
    if not DB_PATH.exists():
        return

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        run_sql_file(conn, VIEWS_SQL)
        run_sql_file(conn, TRIGGERS_SQL)
        conn.commit()

if __name__ == "__main__":
    ensure_db()

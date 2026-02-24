import sqlite3
from pathlib import Path
from SeedDB import ensure_db, ensure_runtime_objects, is_db_initialised

DB_PATH = Path(__file__).resolve().parent.parent / "DB" / "FlightManagement.db"

def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def fetch_one(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> tuple | None:
    return conn.execute(sql, params).fetchone()

# Keep existing data, but refresh views/triggers so SQL definitions
# stay in sync with code updates.

def initialise_db() -> None:
    if is_db_initialised():
        ensure_runtime_objects()
        print("\nUsing Existing database!")
        return
    ensure_db()
    print("\nDatabase Created and Populated Successfully.")


def main_menu() -> None:
    from UI import safe_run
    import ActionsWorkflows as actions

    def reset_database() -> None:
        ensure_db()
        print("\nDatabase Reset.")

    menu_actions = [
        ("1", "View Flights by Criteria", actions.view_flights_by_criteria),
        ("2", "Update Flight Information (Field, Assign Pilot, Delete Flight)", actions.update_flight_information),
        ("3", "View Pilot Schedule", actions.view_pilot_schedule),
        ("4", "View/Update Destination Information", actions.destination_management),
        ("5", "Add a New Flight", actions.add_new_flight),
        ("6", "Summary Reports", actions.summary_reports),
        ("7", "View Audit Log", actions.view_audit_log),
    ]
    extra_actions = [
        ("R", "Reset Database and Reseed", reset_database),
    ]
    action_map = {key: handler for key, _, handler in menu_actions + extra_actions}
    exit_key = "8"

    while True:
        print("\nFlight Management Menu")
        print("----------------------")
        for key, label, _ in menu_actions:
            print(f"{key}) {label}")
        print(f"{exit_key}) Exit")
        print("\nExtra:")
        for key, label, _ in extra_actions:
            print(f"{key}) {label}")
        while True:
            try:
                choice = input("Choose: ").strip().upper()
            except (KeyboardInterrupt, EOFError):
                print("\nDisconnected.")
                return

            if choice == exit_key:
                print("Disconnected.")
                return

            action = action_map.get(choice)
            if action:
                safe_run(action)
                break

            print("Invalid Choice.")


def main() -> None:
    initialise_db()
    main_menu()


if __name__ == "__main__":
    main()

import sqlite3
from datetime import datetime
from tabulate import tabulate
from App import get_conn

VALID_STATUSES = ["Scheduled", "Active", "Landed", "Delayed", "Cancelled", "Diverted"]


class AbortAction(Exception):
    pass


def print_rows(headers: list[str], rows: list[tuple]) -> None:
    if not rows:
        print("\nNo results.\n")
        return

    print()
    print(tabulate(rows, headers=headers, tablefmt="rounded_outline"))
    print()


def print_single_row(headers: list[str], row: tuple | None) -> None:
    print_rows(headers, [row] if row else [])

def handle_integrity_error(e: sqlite3.IntegrityError) -> None:
    print(f"\nDatabase rule failed (FK/UNIQUE/CHECK): {e}")

def safe_run(fn) -> None:
    try:
        fn()
    except (AbortAction, KeyboardInterrupt, EOFError):
        print("\nCancelled. Returning to Menu.\n")
    except ValueError as e:
        print(f"\nInvalid input: {e}\n")
    except sqlite3.IntegrityError as e:
        handle_integrity_error(e)
        print()
    except sqlite3.Error as e:
        print(f"\nDatabase error: {e}\n")
    except Exception as e:
        print(f"\nUnexpected error: {e}\n")

def is_quit(s: str) -> bool:
    return s.strip().lower() in ("-q", "q")


def read_input(prompt: str) -> str:
    try:
        return input(prompt)
    except (KeyboardInterrupt, EOFError):
        print()
        raise AbortAction()

def prompt_int(prompt: str) -> int:
    while True:
        s = read_input(prompt).strip()
        if is_quit(s):
            raise AbortAction()
        try:
            return int(s)
        except ValueError:
            print("Enter a number (or -q to cancel).")

def prompt_optional(prompt: str) -> str | None:
    s = read_input(prompt).strip()
    if is_quit(s):
        raise AbortAction()
    return s if s else None

def prompt_required(prompt: str, field_name: str) -> str:
    value = prompt_optional(prompt)
    if not value:
        raise ValueError(f"{field_name} is required.")
    return value

FIELD_FORMAT_RULES: dict[str, tuple[str, str]] = {
    "FlightDate": ("%Y-%m-%d", "YYYY-MM-DD"),
    "SchedDepUtc": ("%Y-%m-%d %H:%M:%S", "YYYY-MM-DD HH:MM:SS UTC"),
    "SchedArrUtc": ("%Y-%m-%d %H:%M:%S", "YYYY-MM-DD HH:MM:SS UTC"),
    "ActualDepUtc": ("%Y-%m-%d %H:%M:%S", "YYYY-MM-DD HH:MM:SS UTC"),
    "ActualArrUtc": ("%Y-%m-%d %H:%M:%S", "YYYY-MM-DD HH:MM:SS UTC"),
}

def is_valid_update_value(field: str, value: str) -> bool:
    rule = FIELD_FORMAT_RULES.get(field)
    if not rule:
        return True
    fmt, _ = rule
    try:
        datetime.strptime(value, fmt)
        return True
    except ValueError:
        return False

    # For UPDATE prompts: - Enter a value to set
                        # - Enter <<CLEAR>> to set NULL
                        # - Enter -q/q to cancel action

def prompt_update_value(field: str, show_non_clearable_hint: bool = False) -> str | None:
    rule = FIELD_FORMAT_RULES.get(field)
    hint = rule[1] if rule else None
    detailed_prompt = True
    while True:
        if detailed_prompt:
            if hint:
                if show_non_clearable_hint:
                    prompt = f"New {field} (format {hint}; Cannot be Cleared): "
                else:
                    prompt = f"New {field} (format {hint}, Type <<CLEAR>> to clear): "
            else:
                if show_non_clearable_hint:
                    prompt = f"New {field} (cannot be cleared): "
                else:
                    prompt = f"New {field} (Type <<CLEAR>> to clear): "
        else:
            prompt = f"New {field}: "

        s = read_input(prompt).strip()
        if is_quit(s):
            raise AbortAction()
        if s == "<<CLEAR>>":
            return None
        if is_valid_update_value(field, s):
            return s

        print("Invalid value. Use -q to cancel")
        detailed_prompt = False

def choose_from_list(title: str, options: list[str]) -> str:
    print(f"\n{title}")
    for i, opt in enumerate(options, start=1):
        print(f"{i}) {opt}")
    while True:
        raw = read_input("Choose: ").strip()
        if is_quit(raw):
            raise AbortAction()

        if raw.isdigit():
            idx = int(raw)
            if 1 <= idx <= len(options):
                return options[idx - 1]
            print(f"Choose 1–{len(options)}.")
            continue

        normalised = raw.lower()
        for opt in options:
            if normalised == opt.lower():
                return opt

        if normalised in {"y", "yes"}:
            yes_opt = next((opt for opt in options if opt.lower().startswith("yes")), None)
            if yes_opt is not None:
                return yes_opt
        if normalised in {"n", "no"}:
            no_opt = next((opt for opt in options if opt.lower().startswith("no")), None)
            if no_opt is not None:
                return no_opt

        print(f"Choose 1–{len(options)} or type the option text.")

def headers_from_description(description) -> list[str]:
    return [col[0] for col in (description or [])]


def fetch_rows_with_headers(
    conn: sqlite3.Connection, sql: str, params: tuple = ()
) -> tuple[list[str], list[tuple]]:
    cur = conn.execute(sql, params)
    return headers_from_description(cur.description), cur.fetchall()


def fetch_row_with_headers(
    conn: sqlite3.Connection, sql: str, params: tuple = ()
) -> tuple[list[str], tuple | None]:
    cur = conn.execute(sql, params)
    return headers_from_description(cur.description), cur.fetchone()


def query_rows(sql: str, params: tuple = ()) -> tuple[list[str], list[tuple]]:
    with get_conn() as conn:
        return fetch_rows_with_headers(conn, sql, params)


def preview_query(sql: str, params: tuple = ()) -> None:
    headers, rows = query_rows(sql, params)
    print_rows(headers, rows)

#Helper to check if a record exists. Returns True if found, False otherwise.
def record_exists(conn: sqlite3.Connection, sql: str, params: tuple) -> bool:
    result = conn.execute(sql, params).fetchone()
    return result is not None

# Clear all filter values by setting them to None.
def clear_filters(filters: dict) -> None:
    for key in list(filters.keys()):
        filters[key] = None


def update_whitelisted_field(
    conn: sqlite3.Connection,
    table: str,
    id_column: str,
    record_id: int,
    fields: list[str],
    status_field: str | None = None,
    status_options: list[str] | None = None,
    non_clearable_fields: set[str] | None = None,
) -> None:
    blocked_clears = non_clearable_fields or set()
    while True:
        field = choose_from_list("Field to Update:", fields)
        try:
            if status_field and status_options and field == status_field:
                new_val = choose_from_list("New Status:", status_options)
            else:
                new_val = prompt_update_value(
                    field,
                    show_non_clearable_hint=field in blocked_clears,
                )

            conn.execute(
                f"UPDATE {table} SET {field} = ? WHERE {id_column} = ?;",
                (new_val, record_id),
            )
            return
        except sqlite3.IntegrityError as e:
            conn.rollback()
            handle_integrity_error(e)
            print("Try again (or -q to cancel).\n")

def browse(
    title: str,
    build_query,
    filters: dict,
    prompt_filters=None,
    format_filters=None,
) -> None:
    while True:
        sql, params = build_query(filters)
        headers, rows = query_rows(sql, params)

        print(f"\n{title}")
        print("-" * len(title))
        print_rows(headers, rows)
        print(f"Rows: {len(rows)}")
        if format_filters:
            rendered_filters = (format_filters(filters) or "").strip()
            if not rendered_filters:
                rendered_filters = "(none)"
        else:
            active = {k: v for k, v in filters.items() if v not in ("", None)}
            rendered_filters = str(active if active else "(none)")
        print(f"Filters: {rendered_filters}")

        print("Commands: f=filter, r=reset, -q=back")
        while True:
            cmd = read_input("Command: ").strip().lower()

            if cmd in ("-q", "q"):
                return
            if cmd == "f" and prompt_filters:
                prompt_filters(filters)
                break
            if cmd == "r":
                clear_filters(filters)
                break

            print("Invalid Command. Use f, r, or -q.")

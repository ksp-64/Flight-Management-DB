import sqlite3

from App import get_conn, fetch_one
import Queries as q
from FilterSQL import init_filters, format_filters, prompt_filter
from AllFilterSpecs import (
    AIRPORT_FILTER_SPECS,
    AUDIT_LOG_FILTER_SPECS,
    FLIGHT_FILTER_SPECS,
    PILOT_SCHEDULE_FILTER_SPECS,
)
from UI import (
    AbortAction,
    VALID_STATUSES,
    browse,
    choose_from_list,
    clear_filters,
    fetch_row_with_headers,
    handle_integrity_error,
    is_quit,
    is_valid_update_value,
    preview_query,
    print_rows,
    print_single_row,
    prompt_int,
    prompt_optional,
    prompt_required,
    query_rows,
    read_input,
    record_exists,
    update_whitelisted_field,
)

PILOT_DUTY_ROLES = ["Captain", "First Officer"]

def pick_id_from_filtered_listing(
    *,
    title: str,
    build_query,
    filters: dict,
    format_filters_fn=None,
    prompt_filters=None,
    id_name: str,
    exists_sql: str,
    prompt_text: str,
    invalid_input_text: str,
    not_found_text: str,
    allow_filtering: bool = True,
) -> int:

    # Generic ID picker with filtering support.
    # Shows a filtered listing, allows user to filter/reset/select an ID.
    # Returns the selected ID once validated to exist in the database.

    if allow_filtering and prompt_filters is None:
        raise ValueError("prompt_filters is required when allow_filtering=True")

    while True:
        sql, params = build_query(filters)
        headers, rows = query_rows(sql, params)

        print(f"\n{title}")
        print("-" * len(title))
        print_rows(headers, rows)
        print(f"Rows: {len(rows)}")
        print(f"Filters: {format_filters_fn(filters) if format_filters_fn else '(none)'}")
        print(f"Commands: {'f=filter, r=reset, ' if allow_filtering else ''}<{id_name}>=select, -q=back")
        while True:
            cmd = read_input(prompt_text).strip()
            if is_quit(cmd):
                raise AbortAction()
            lowered = cmd.lower()

            if allow_filtering and lowered == "f":
                prompt_filters(filters)
                break
            if allow_filtering and lowered == "r":
                clear_filters(filters)
                break

            try:
                selected_id = int(cmd)
            except ValueError:
                print(invalid_input_text)
                continue

            with get_conn() as conn:
                if record_exists(conn, exists_sql, (selected_id,)):
                    return selected_id
            print(not_found_text)

# Show Pilot List and prompt for a valid pilot StaffID.

def prompt_valid_pilot_staff_id() -> int:
    preview_query(q.SQL_PILOTS)
    while True:
        staff_id = prompt_int("Enter Pilot StaffID (or -q): ")
        with get_conn() as conn:
            if record_exists(conn, q.SQL_PILOT_BY_ID, (staff_id,)):
                return staff_id
        print("\nPilot not found. Choose a StaffID from the list above (or -q).\n")

    # Assign a Pilot to a Flight instance with a duty role.
    # Returns True if successful, False if assignment failed (duplicate/role conflict).

def assign_pilot_to_instance(instance_id: int, staff_id: int) -> bool:
    preview_query(q.SQL_CREW_FOR_INSTANCE, (instance_id,))
    duty_role = choose_from_list("Duty Role:", PILOT_DUTY_ROLES)

    with get_conn() as conn:
        exists = fetch_one(conn, q.SQL_CREW_ASSIGNMENT_EXISTS, (instance_id, staff_id))
        if exists:
            print("\nThat Staff Member is Already Assigned to this Flight Instance.")
            return False

        role_taken = fetch_one(conn, q.SQL_ROLE_TAKEN_FOR_INSTANCE, (instance_id, duty_role))
        if role_taken:
            print(
                f"\n{duty_role} Is Already Assigned On This Flight Instance "
                f"({role_taken[0]} {role_taken[1]})."
            )
            return False

        try:
            conn.execute(q.SQL_INSERT_CREW_ASSIGNMENT, (instance_id, staff_id, duty_role))
            conn.commit()
        except sqlite3.IntegrityError as e:
            conn.rollback()
            handle_integrity_error(e)
            return False

        headers, row = fetch_row_with_headers(conn, q.SQL_LAST_CREW_ASSIGNMENT, (instance_id, staff_id))

    print("\n Successfully Assigned Pilot:\n")
    print_single_row(headers, row)
    return True

# Show all flight instances and prompt user to pick one by InstanceID.

def pick_instance_for_update() -> int:
    while True:
        sql = q.SQL_PREVIEW_FLIGHT_INSTANCES
        params: tuple = ()
        headers, rows = query_rows(sql, params)

        print("\nUpdate Flight Information")
        print("-" * len("Update Flight Information"))
        print_rows(headers, rows)
        print(f"Rows: {len(rows)}")
        print("Filters: (none)")
        print("Commands: <InstanceID>=edit, -q=back")

        cmd = read_input("Enter InstanceID to edit (or command): ").strip()
        if is_quit(cmd):
            raise AbortAction()

        if cmd == "":
            continue

        try:
            instance_id = int(cmd)
        except ValueError:
            print("Enter an InstanceID to Edit, or -q.")
            continue

        with get_conn() as conn:
            if record_exists(conn, q.SQL_INSTANCE_EXISTS, (instance_id,)):
                return instance_id
        print("\nInstance not found. Choose one from the list above (or -q).\n")



# Update whitelisted fields on a FlightInstance.

def update_instance_information_fields(instance_id: int) -> None:
    with get_conn() as conn:
        if not record_exists(conn, q.SQL_INSTANCE_EXISTS, (instance_id,)):
            print("\nInstance Not Found.\n")
            return

        update_whitelisted_field(
            conn=conn,
            table="FlightInstance",
            id_column="InstanceID",
            record_id=instance_id,
            fields=[
                "FlightDate",
                "SchedDepUtc",
                "SchedArrUtc",
                "ActualDepUtc",
                "ActualArrUtc",
                "Status",
                "Gate",
                "Terminal",
            ],
            status_field="Status",
            status_options=VALID_STATUSES,
            non_clearable_fields={"FlightDate", "SchedDepUtc", "SchedArrUtc"},
        )
        conn.commit()

    print("\nUpdated:\n")
    preview_query(q.SQL_INSTANCE_OVERVIEW_BY_ID, (instance_id,))


# Menu Option 1: Browse flights with multi-criteria filtering.

def view_flights_by_criteria() -> None:
    filters = init_filters(FLIGHT_FILTER_SPECS)

    browse(
        title="View Flights by Criteria",
        build_query=q.build_flights_by_criteria,
        filters=filters,
        prompt_filters=lambda f: prompt_filter(f, FLIGHT_FILTER_SPECS, choose_from_list, prompt_optional, VALID_STATUSES),
        format_filters=lambda f: format_filters(f, FLIGHT_FILTER_SPECS),
    )

# Menu Option 2: Update flight instance fields, assign pilots, or delete instance.

def update_flight_information() -> None:
    while True:
        instance_id = pick_instance_for_update()
        while True:
            action = choose_from_list(
                "Choose Action:",
                ["Update a Field", "Assign Pilot to This Instance", "Delete this FlightInstance"],
            )

            if action == "Update a Field":
                update_instance_information_fields(instance_id)
                continue

            if action == "Assign Pilot to This Instance":
                staff_id = prompt_valid_pilot_staff_id()
                while True:
                    if assign_pilot_to_instance(instance_id, staff_id):
                        break

                    next_step = choose_from_list(
                        "Assignment not completed. Next step:",
                        ["Try Again", "Choose Another Pilot", "Cancel"],
                    )
                    if next_step == "Try Again":
                        continue
                    if next_step == "Choose Another Pilot":
                        staff_id = prompt_valid_pilot_staff_id()
                        continue
                    print("Assignment Cancelled.")
                    break
                continue

            confirm = read_input("Type DELETE to Confirm (or -q): ").strip()
            if is_quit(confirm) or confirm.lower() != "delete":
                print("Delete Cancelled.")
                continue

            with get_conn() as conn:
                try:
                    booking_count = int(fetch_one(conn, q.SQL_BOOKING_ITEM_COUNT_BY_INSTANCE, (instance_id,))[0])

                    deleted_booking_items = 0
                    if booking_count > 0:
                        print(f"\nThis Flight Instance has {booking_count} Linked Booking item(s).")
                        try:
                            delete_mode = choose_from_list(
                                "Delete Behaviour:",
                                ["Cancel Delete", "Delete Linked Booking Items and Continue"],
                            )
                        except AbortAction:
                            print("Delete Cancelled.")
                            continue
                        if delete_mode == "Cancel Delete":
                            print("Delete Cancelled.")
                            continue
                        deleted_booking_items = conn.execute(
                            q.SQL_DELETE_BOOKING_ITEMS_BY_INSTANCE,
                            (instance_id,),
                        ).rowcount or 0

                    conn.execute(q.SQL_DELETE_FLIGHT_INSTANCE_BY_ID, (instance_id,))
                    conn.commit()
                    if deleted_booking_items > 0:
                        print(
                            "\nDeleted FlightInstance and "
                            f"{deleted_booking_items} linked booking item(s).\n"
                        )
                    else:
                        print("\nDeleted.\n")
                    break
                except sqlite3.IntegrityError as e:
                    conn.rollback()
                    handle_integrity_error(e)
                    print()

# Menu Option 3: Browse pilot schedules with filtering by pilot, role, status, dates.

def view_pilot_schedule() -> None:
    filters = init_filters(PILOT_SCHEDULE_FILTER_SPECS)

    browse(
        title="View Pilot Schedule",
        build_query=q.build_pilot_schedule,
        filters=filters,
        prompt_filters=lambda f: prompt_filter(f, PILOT_SCHEDULE_FILTER_SPECS, choose_from_list, prompt_optional, VALID_STATUSES),
        format_filters=lambda f: format_filters(f, PILOT_SCHEDULE_FILTER_SPECS),
    )

 # Menu Option 4: View/update airports (destination management).

def destination_management() -> None:
    print("\nDestination Management")
    print("----------------------")

    choice = choose_from_list("Choose:", ["View Airports", "Update an Airport"])

    if choice == "View Airports":
        filters = init_filters(AIRPORT_FILTER_SPECS)

        browse(
            title="Airports",
            build_query=q.build_airports,
            filters=filters,
            prompt_filters=lambda f: prompt_filter(f, AIRPORT_FILTER_SPECS, choose_from_list, prompt_optional, VALID_STATUSES),
            format_filters=lambda f: format_filters(f, AIRPORT_FILTER_SPECS),
        )
        return

    filters = init_filters(AIRPORT_FILTER_SPECS)
    airport_id = pick_id_from_filtered_listing(
        title="Airports",
        build_query=q.build_airports,
        filters=filters,
        format_filters_fn=lambda f: format_filters(f, AIRPORT_FILTER_SPECS),
        prompt_filters=lambda f: prompt_filter(f, AIRPORT_FILTER_SPECS, choose_from_list, prompt_optional, VALID_STATUSES),
        id_name="AirportID",
        exists_sql=q.SQL_AIRPORT_BY_ID,
        prompt_text="Enter AirportID (or Command): ",
        invalid_input_text="Enter f, r, an AirportID, or -q.",
        not_found_text="Airport not found. Choose from the list above (or -q).",
    )

    with get_conn() as conn:
        headers, current = fetch_row_with_headers(conn, q.SQL_AIRPORT_BY_ID, (airport_id,))

        if current is None:
            print("\nAirport not found.\n")
            return

        print_single_row(headers, current)

        update_whitelisted_field(
            conn=conn,
            table="Airport",
            id_column="AirportID",
            record_id=airport_id,
            fields=["Name", "City", "Country", "Timezone", "Dst"],
            non_clearable_fields={"Name"},
        )
        conn.commit()

        headers2, updated = fetch_row_with_headers(conn, q.SQL_AIRPORT_BY_ID, (airport_id,))

    print("\nUpdated:\n")
    print_single_row(headers2, updated)

 # Prompt for flight instance details and create a new instance for the given FlightID.

def add_flight_instance_for_flight(flight_id: int) -> None:
    preview_query(q.SQL_AIRCRAFT_IN_SERVICE)
    aircraft_id = prompt_int("Enter AircraftID (or -q): ")

    def prompt_required_field_value(prompt: str, field_name: str) -> str:
        while True:
            raw = prompt_optional(prompt)
            if raw is None:
                print(f"{field_name} is required. Use -q to cancel.")
                continue
            if is_valid_update_value(field_name, raw):
                return raw
            print(f"Invalid {field_name}. Use the format shown in the prompt (or -q to cancel).")

    while True:
        flight_date = prompt_required_field_value(
            "FlightDate (YYYY-MM-DD): ",
            "FlightDate",
        )
        sched_dep = prompt_required_field_value(
            "SchedDepUtc (YYYY-MM-DD HH:MM:SS): ",
            "SchedDepUtc",
        )
        sched_arr = prompt_required_field_value(
            "SchedArrUtc (YYYY-MM-DD HH:MM:SS): ",
            "SchedArrUtc",
        )

        status = prompt_optional("Status (blank = Scheduled): ") or "Scheduled"
        terminal = prompt_optional("Terminal (blank allowed): ")
        gate = prompt_optional("Gate (blank allowed): ")

        with get_conn() as conn:
            try:
                conn.execute(
                    q.SQL_INSERT_FLIGHT_INSTANCE,
                    (flight_id, flight_date, sched_dep, sched_arr, status, terminal, gate, aircraft_id),
                )
                new_id = fetch_one(conn, q.SQL_LAST_INSERT_ROWID)
                conn.commit()
            except sqlite3.IntegrityError as e:
                conn.rollback()
                handle_integrity_error(e)
                print("Try Again (or -q to cancel).\n")
                continue

        instance_id = new_id[0]
        print(f"\nInserted FlightInstance. New InstanceID = {instance_id}\n")
        preview_query(q.SQL_INSTANCE_OVERVIEW_BY_ID, (instance_id,))

        return

# Show existing flights with filtering, allow user to pick one or create new.
# Returns FlightID if existing flight selected, None if user wants to create new.

def pick_existing_flight_or_new() -> int | None:
    while True:
        sql, params = q.build_flights_for_new_instance({})
        headers, rows = query_rows(sql, params)

        print("\nExisting Flights")
        print("-" * len("Existing Flights"))
        print_rows(headers, rows)
        print(f"Rows: {len(rows)}")
        print("Filters: (none)")
        print("Commands: NEW=Create Flight, <FlightID>=select, -q=back")

        while True:
            cmd = read_input("Enter command, NEW, or FlightID: ").strip()
            if is_quit(cmd):
                raise AbortAction()
            lowered = cmd.lower()

            if lowered == "new":
                return None

            try:
                flight_id = int(cmd)
            except ValueError:
                print("Enter NEW, a FlightID, or -q.")
                continue

            with get_conn() as conn:
                existing = fetch_one(conn, q.SQL_FLIGHT_BY_FLIGHTID, (flight_id,))

            if existing:
                headers = ["FlightID", "FlightNo", "AirlineID", "Airline", "RouteID", "Origin", "Dest"]
                print("\nFlight Already Exists. Reusing Existing Flight:\n")
                print_single_row(headers, existing)
                return existing[0]

            print("\nFlight not found. Try another FlightID or enter NEW (or -q).\n")


# Menu Option 5: Add a new flight (reuse existing or create new Flight + FlightInstance).

def add_new_flight() -> None:
    print("\nAdd a New Flight")
    print("----------------")

    existing_flight_id = pick_existing_flight_or_new()
    if existing_flight_id is not None:
        flight_id = existing_flight_id
    else:
        print("\nCreate a New Flight")
        print("-------------------")

        airline_id = pick_id_from_filtered_listing(
            title="Active Airlines",
            build_query=q.build_airlines_for_new_flight,
            filters={},
            id_name="AirlineID",
            exists_sql=q.SQL_AIRLINE_BY_ID,
            prompt_text="Enter AirlineID (or -q): ",
            invalid_input_text="Enter an AirlineID or -q.",
            not_found_text="Airline not found. Choose from the list above (or -q).",
            allow_filtering=False,
        )

        flight_number = prompt_required("FlightNumber (e.g. AA123): ", "FlightNumber").upper()

        with get_conn() as conn:
            headers, duplicate = fetch_row_with_headers(
                conn,
                q.SQL_FLIGHT_BY_AIRLINE_AND_NUMBER,
                (airline_id, flight_number),
            )

        if duplicate:
            print("\nThat Airline + Flight Number Already Exists. Reusing Existing Flight:\n")
            print_single_row(headers, duplicate)
            flight_id = duplicate[0]
        else:
            route_id = pick_id_from_filtered_listing(
                title="Routes",
                build_query=q.build_routes_for_new_flight,
                filters={},
                id_name="RouteID",
                exists_sql=q.SQL_ROUTE_BY_ID,
                prompt_text="Enter RouteID (or -q): ",
                invalid_input_text="Enter a RouteID or -q.",
                not_found_text="Route not found. Choose from the list above (or -q).",
                allow_filtering=False,
            )

            with get_conn() as conn:
                try:
                    conn.execute(q.SQL_INSERT_FLIGHT, (airline_id, flight_number, route_id))
                    new_id = fetch_one(conn, q.SQL_LAST_INSERT_ROWID)
                    conn.commit()
                except sqlite3.IntegrityError as e:
                    conn.rollback()
                    handle_integrity_error(e)
                    print()
                    return

            flight_id = new_id[0]

            with get_conn() as conn:
                headers, row = fetch_row_with_headers(conn, q.SQL_FLIGHT_BY_ID, (flight_id,))

            print("\nInserted Flight:\n")
            print_single_row(headers, row)

    next_step = choose_from_list(
        "Create A Scheduled Flight Instance Now?",
        ["Yes", "No"],
    )
    if next_step == "Yes":
        print("\nAdd a New Flight Instance")
        print("-------------------------")
        print(f"Using FlightID = {flight_id}\n")
        add_flight_instance_for_flight(flight_id)

# Menu Option 6: Display summary reports (flights per destination, flights per pilot).

def summary_reports() -> None:
    reports = {
        "Flights Per Destination": q.SQL_REPORT_DESTINATION,
        "Flights Per Pilot": q.SQL_REPORT_PILOT,
    }
    report = choose_from_list("Choose Report:", list(reports))
    preview_query(reports[report])

# Menu Option 7: Browse USER audit log with filtering by operation, instance, field.

def view_audit_log() -> None:
    filters = init_filters(AUDIT_LOG_FILTER_SPECS)

    browse(
        title="Audit Log",
        build_query=q.build_audit_log,
        filters=filters,
        prompt_filters=lambda f: prompt_filter(f, AUDIT_LOG_FILTER_SPECS, choose_from_list, prompt_optional, VALID_STATUSES),
        format_filters=lambda f: format_filters(f, AUDIT_LOG_FILTER_SPECS),
    )

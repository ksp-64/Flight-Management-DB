from AllFilterSpecs import (
    AIRPORT_FILTER_SPECS,
    AUDIT_LOG_FILTER_SPECS,
    FLIGHT_FILTER_SPECS,
    PILOT_SCHEDULE_FILTER_SPECS,
)
from FilterSQL import apply_sql_filter


def compact_utc_expr(datetime_expr: str, flight_date_expr: str) -> str:
    day_offset = (
        f"CAST(julianday(date({datetime_expr})) - "
        f"julianday(date({flight_date_expr})) AS INTEGER)"
    )
    return (
        f"strftime('%H:%M', {datetime_expr}) || "
        f"CASE WHEN {day_offset} > 0 THEN ' +' || {day_offset} ELSE '' END"
    )


def build_flights_by_criteria(filters: dict):
    dep_utc = compact_utc_expr("v.SchedDepUtc", "v.FlightDate")
    arr_utc = compact_utc_expr("v.SchedArrUtc", "v.FlightDate")
    actual_dep_utc = compact_utc_expr("v.ActualDepUtc", "v.FlightDate")
    actual_arr_utc = compact_utc_expr("v.ActualArrUtc", "v.FlightDate")

    sql = f"""
        SELECT
            v.InstanceID,
            v.FlightNumber AS FlightNo,
            COALESCE(al.IcaoCode, al.IataCode, l.AirlineName) AS Airline,
            v.FlightDate   AS Date,
            {dep_utc} AS DepUTC,
            {arr_utc} AS ArrUTC,
            {actual_dep_utc} AS ActualDepUTC,
            {actual_arr_utc} AS ActualArrUTC,
            v.Status,
            v.Gate,
            v.Terminal,
            '(' || v.OriginIata || ') ' || v.OriginName AS Departure,
            '(' || v.DestIata || ') ' || v.DestinationName AS Arrival,
            v.Captain,
            v."First Officer" AS FirstOfficer
        FROM View_FlightsDetailedWithPilots v
        LEFT JOIN View_FlightLookup l ON l.FlightID = v.FlightID
        LEFT JOIN Airline al ON al.AirlineID = l.AirlineID
        WHERE 1 = 1
    """
    params: list = []

    for spec in FLIGHT_FILTER_SPECS:
        value = filters.get(spec.key)
        sql = apply_sql_filter(sql, params, spec, value)

    sql += " ORDER BY v.FlightDate DESC, v.SchedDepUtc DESC, v.FlightNumber ASC, v.InstanceID DESC;"
    return sql, tuple(params)


def build_pilot_schedule(filters: dict):
    dep_utc = compact_utc_expr("SchedDepUtc", "FlightDate")
    arr_utc = compact_utc_expr("SchedArrUtc", "FlightDate")

    sql = f"""
        SELECT
            StaffID,
            FirstName,
            LastName,
            DutyRole,
            InstanceID,
            FlightNumber AS FlightNo,
            FlightDate   AS Date,
            {dep_utc} AS DepUTC,
            {arr_utc} AS ArrUTC,
            Status
        FROM View_PilotSchedule
        WHERE 1 = 1
    """
    params: list = []

    for spec in PILOT_SCHEDULE_FILTER_SPECS:
        value = filters.get(spec.key)
        sql = apply_sql_filter(sql, params, spec, value)

    sql += " ORDER BY FlightDate DESC, SchedDepUtc DESC, FlightNumber ASC, StaffID ASC, InstanceID DESC;"
    return sql, tuple(params)


def build_airports(filters: dict):
    sql = """
        SELECT
            AirportID,
            IataCode AS IATA,
            IcaoCode AS ICAO,
            Name,
            City,
            Country,
            Timezone
        FROM Airport
        WHERE 1 = 1
    """
    params: list = []

    for spec in AIRPORT_FILTER_SPECS:
        value = filters.get(spec.key)
        sql = apply_sql_filter(sql, params, spec, value)

    sql += " ORDER BY Country, City, Name, AirportID;"
    return sql, tuple(params)


def build_flights_for_new_instance(_filters: dict):
    sql = """
        SELECT
            FlightID,
            AirlineName  AS Airline,
            FlightNumber AS FlightNo,
            OriginIata   AS OriginIATA,
            OriginName   AS OriginName,
            DestIata     AS DestIATA,
            DestName     AS DestName
        FROM View_FlightLookup
        WHERE 1 = 1
    """
    params: list = []

    sql += " ORDER BY FlightNumber, FlightID;"
    return sql, tuple(params)


def build_airlines_for_new_flight(_filters: dict):
    sql = """
        SELECT
            AirlineID,
            IataCode AS IATA,
            IcaoCode AS ICAO,
            Name
        FROM Airline
        WHERE Active = 1
    """
    params: list = []

    sql += " ORDER BY Name, AirlineID;"
    return sql, tuple(params)


def build_routes_for_new_flight(_filters: dict):
    sql = """
        SELECT
            r.RouteID,
            ao.IataCode AS Origin,
            ad.IataCode AS Dest,
            r.DistanceKm AS Km
        FROM Route r
        JOIN Airport ao ON ao.AirportID = r.OriginAirportID
        JOIN Airport ad ON ad.AirportID = r.DestinationAirportID
        WHERE 1 = 1
    """
    params: list = []

    sql += " ORDER BY Origin, Dest, r.RouteID;"
    return sql, tuple(params)


def build_audit_log(filters: dict):
    sql = """
        SELECT
            LogID,
            Operation    AS Op,
            TableName    AS 'Table',
            InstanceID,
            FlightNumber AS FlightNo,
            FlightDate   AS Date,
            FieldChanged AS Field,
            OldValue     AS Old,
            NewValue     AS New,
            ChangedAt,
            ChangedBy    AS By
        FROM View_AuditLog
        WHERE 1 = 1
    """
    params: list = []

    for spec in AUDIT_LOG_FILTER_SPECS:
        value = filters.get(spec.key)
        sql = apply_sql_filter(sql, params, spec, value)

    sql += " ORDER BY ChangedAt DESC, LogID DESC;"
    return sql, tuple(params)

dep_utc_for_instance = compact_utc_expr("v.SchedDepUtc", "v.FlightDate")
arr_utc_for_instance = compact_utc_expr("v.SchedArrUtc", "v.FlightDate")
actual_dep_utc_for_instance = compact_utc_expr("v.ActualDepUtc", "v.FlightDate")
actual_arr_utc_for_instance = compact_utc_expr("v.ActualArrUtc", "v.FlightDate")

# Shared base query for flight instance overview to avoid duplication
instance_overview_base = f"""
    SELECT
        v.InstanceID,
        v.FlightNumber AS FlightNo,
        COALESCE(al.IcaoCode, al.IataCode, l.AirlineName) AS Airline,
        v.FlightDate   AS Date,
        {dep_utc_for_instance} AS DepUTC,
        {arr_utc_for_instance} AS ArrUTC,
        {actual_dep_utc_for_instance} AS ActualDepUTC,
        {actual_arr_utc_for_instance} AS ActualArrUTC,
        v.Status,
        v.Gate,
        '(' || v.OriginIata || ') ' || v.OriginName AS Departure,
        '(' || v.DestIata || ') ' || v.DestinationName AS Arrival,
        v.Captain,
        v."First Officer" AS FirstOfficer
    FROM View_FlightsDetailedWithPilots v
    LEFT JOIN View_FlightLookup l ON l.FlightID = v.FlightID
    LEFT JOIN Airline al ON al.AirlineID = l.AirlineID
"""

SQL_PREVIEW_FLIGHT_INSTANCES = (
    instance_overview_base
    + " ORDER BY v.FlightDate DESC, v.SchedDepUtc DESC, v.FlightNumber ASC, v.InstanceID DESC;"
)

SQL_INSTANCE_OVERVIEW_BY_ID = instance_overview_base + " WHERE v.InstanceID = ?;"

SQL_PILOTS = """
    SELECT
        s.StaffID,
        s.FirstName,
        s.LastName,
        a.IataCode AS BaseIata
    FROM Staff s
    JOIN Airport a ON a.AirportID = s.BaseAirportID
    WHERE s.Role = 'Pilot'
    ORDER BY s.LastName, s.FirstName, s.StaffID;
"""

SQL_PILOT_BY_ID = """
    SELECT StaffID
    FROM Staff
    WHERE StaffID = ? AND Role = 'Pilot'
    LIMIT 1;
"""

SQL_INSTANCE_EXISTS = """
    SELECT InstanceID
    FROM FlightInstance
    WHERE InstanceID = ?
    LIMIT 1;
"""

SQL_BOOKING_ITEM_COUNT_BY_INSTANCE = """
    SELECT COUNT(*)
    FROM BookingItem
    WHERE InstanceID = ?;
"""

SQL_DELETE_BOOKING_ITEMS_BY_INSTANCE = """
    DELETE FROM BookingItem
    WHERE InstanceID = ?;
"""

SQL_DELETE_FLIGHT_INSTANCE_BY_ID = """
    DELETE FROM FlightInstance
    WHERE InstanceID = ?;
"""

SQL_CREW_FOR_INSTANCE = """
    SELECT
        ca.InstanceID,
        ca.StaffID,
        s.FirstName,
        s.LastName,
        ca.DutyRole
    FROM CrewAssignment ca
    JOIN Staff s ON s.StaffID = ca.StaffID
    WHERE ca.InstanceID = ?
    ORDER BY ca.DutyRole, s.LastName, s.FirstName, s.StaffID;
"""

SQL_CREW_ASSIGNMENT_EXISTS = """
    SELECT 1
    FROM CrewAssignment
    WHERE InstanceID = ? AND StaffID = ?;
"""

SQL_ROLE_TAKEN_FOR_INSTANCE = """
    SELECT
        s.FirstName,
        s.LastName
    FROM CrewAssignment ca
    JOIN Staff s ON s.StaffID = ca.StaffID
    WHERE ca.InstanceID = ? AND ca.DutyRole = ?
    LIMIT 1;
"""

SQL_INSERT_CREW_ASSIGNMENT = """
    INSERT INTO CrewAssignment (InstanceID, StaffID, DutyRole)
    VALUES (?, ?, ?);
"""

SQL_LAST_CREW_ASSIGNMENT = """
    SELECT
        ca.InstanceID,
        ca.StaffID,
        s.FirstName,
        s.LastName,
        ca.DutyRole
    FROM CrewAssignment ca
    JOIN Staff s ON s.StaffID = ca.StaffID
    WHERE ca.InstanceID = ? AND ca.StaffID = ?
    LIMIT 1;
"""

SQL_AIRPORT_BY_ID = """
    SELECT
        AirportID,
        IataCode AS IATA,
        IcaoCode AS ICAO,
        Name,
        City,
        Country,
        Timezone,
        Dst
    FROM Airport
    WHERE AirportID = ?;
"""

SQL_AIRLINE_BY_ID = """
    SELECT
        AirlineID,
        IataCode AS IATA,
        IcaoCode AS ICAO,
        Name
    FROM Airline
    WHERE AirlineID = ? AND Active = 1
    LIMIT 1;
"""

SQL_ROUTE_BY_ID = """
    SELECT
        r.RouteID,
        ao.IataCode AS Origin,
        ad.IataCode AS Dest,
        r.DistanceKm AS Km
    FROM Route r
    JOIN Airport ao ON ao.AirportID = r.OriginAirportID
    JOIN Airport ad ON ad.AirportID = r.DestinationAirportID
    WHERE r.RouteID = ?
    LIMIT 1;
"""

flight_lookup_base = """
    SELECT
        f.FlightID,
        f.FlightNumber AS FlightNo,
        f.AirlineID,
        al.Name AS Airline,
        f.RouteID,
        ao.IataCode AS Origin,
        ad.IataCode AS Dest
    FROM Flight f
    JOIN Airline al ON al.AirlineID = f.AirlineID
    JOIN Route r ON r.RouteID = f.RouteID
    JOIN Airport ao ON ao.AirportID = r.OriginAirportID
    JOIN Airport ad ON ad.AirportID = r.DestinationAirportID
"""

SQL_FLIGHT_BY_FLIGHTID = flight_lookup_base + " WHERE f.FlightID = ? LIMIT 1;"

SQL_FLIGHT_BY_AIRLINE_AND_NUMBER = (
    flight_lookup_base
    + " WHERE f.AirlineID = ? AND upper(f.FlightNumber) = upper(?) LIMIT 1;"
)

SQL_INSERT_FLIGHT = """
    INSERT INTO Flight (AirlineID, FlightNumber, RouteID)
    VALUES (?, ?, ?);
"""

SQL_FLIGHT_BY_ID = flight_lookup_base + " WHERE f.FlightID = ?;"

SQL_AIRCRAFT_IN_SERVICE = """
    SELECT
        AircraftID,
        TailNumber   AS Tail,
        Manufacturer,
        Model,
        SeatCapacity AS Seats
    FROM Aircraft
    WHERE InService = 1
    ORDER BY AircraftID;
"""

SQL_INSERT_FLIGHT_INSTANCE = """
    INSERT INTO FlightInstance (
        FlightID,
        FlightDate,
        SchedDepUtc,
        SchedArrUtc,
        ActualDepUtc,
        ActualArrUtc,
        Status,
        Terminal,
        Gate,
        AircraftID
    )
    VALUES (?, ?, ?, ?, NULL, NULL, ?, ?, ?, ?);
"""

SQL_LAST_INSERT_ROWID = "SELECT last_insert_rowid();"

SQL_REPORT_DESTINATION = """
    SELECT *
    FROM View_FlightsPerDestination
    ORDER BY Flights DESC, DestIata, DestinationName;
"""

SQL_REPORT_PILOT = """
    SELECT *
    FROM View_FlightsPerPilot
    ORDER BY AssignedInstances DESC, LastName, FirstName, StaffID;
"""

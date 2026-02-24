from dataclasses import dataclass
from typing import Literal

FilterUI = Literal["text", "status", "yes_no", "int"]
FilterSqL = Literal["like", "equal", "equal_ci", "presence"]


@dataclass(frozen=True)
class FilterSpec:
    key: str
    label: str
    ui_kind: FilterUI
    prompt: str | None
    sql_kind: FilterSqL
    col: str | None = None


FLIGHT_FILTER_SPECS: list[FilterSpec] = [
    FilterSpec(
        key="flight_no_like",
        label="FlightNo",
        ui_kind="text",
        prompt="FlightNo Contains: ",
        sql_kind="like",
        col="v.FlightNumber",
    ),
    FilterSpec(
        key="airline_code",
        label="Airline Code",
        ui_kind="text",
        prompt="Airline Code (ICAO or IATA): ",
        sql_kind="equal_ci",
        col="COALESCE(al.IcaoCode, al.IataCode, '')",
    ),
    FilterSpec(
        key="departure_iata",
        label="Departure Airport Code",
        ui_kind="text",
        prompt="Departure Airport IATA: ",
        sql_kind="equal_ci",
        col="v.OriginIata",
    ),
    FilterSpec(
        key="arrival_iata",
        label="Arrival Airport Code",
        ui_kind="text",
        prompt="Arrival Airport IATA: ",
        sql_kind="equal_ci",
        col="v.DestIata",
    ),
    FilterSpec(
        key="departure_date",
        label="Departure Date",
        ui_kind="text",
        prompt="Departure Date YYYY-MM-DD: ",
        sql_kind="equal",
        col="v.FlightDate",
    ),
    FilterSpec(
        key="arrival_date",
        label="Arrival Date",
        ui_kind="text",
        prompt="Arrival Date YYYY-MM-DD: ",
        sql_kind="equal",
        col="date(v.SchedArrUtc)",
    ),
    FilterSpec(
        key="status",
        label="Status",
        ui_kind="status",
        prompt="Status: ",
        sql_kind="equal",
        col="v.Status",
    ),
    FilterSpec(
        key="has_captain",
        label="Has Captain",
        ui_kind="yes_no",
        prompt="Has Captain (Y/N): ",
        sql_kind="presence",
        col="v.Captain",
    ),
    FilterSpec(
        key="has_first_officer",
        label="Has First Officer (Y/N)",
        ui_kind="yes_no",
        prompt="Has First Officer (Y/N) ",
        sql_kind="presence",
        col='v."First Officer"',
    ),
]


PILOT_SCHEDULE_FILTER_SPECS: list[FilterSpec] = [
    FilterSpec(
        key="staff_id",
        label="Pilot StaffID",
        ui_kind="int",
        prompt="Pilot StaffID: ",
        sql_kind="equal",
        col="StaffID",
    ),
    FilterSpec(
        key="flight_no_like",
        label="FlightNo",
        ui_kind="text",
        prompt="FlightNo Contains: ",
        sql_kind="like",
        col="FlightNumber",
    ),
    FilterSpec(
        key="duty_role",
        label="Duty Role",
        ui_kind="text",
        prompt="Duty Role: ",
        sql_kind="equal_ci",
        col="DutyRole",
    ),
    FilterSpec(
        key="status",
        label="Status",
        ui_kind="status",
        prompt="Status: ",
        sql_kind="equal",
        col="Status",
    ),
    FilterSpec(
        key="date",
        label="Date",
        ui_kind="text",
        prompt="Date YYYY-MM-DD: ",
        sql_kind="equal",
        col="FlightDate",
    ),
]


AUDIT_LOG_FILTER_SPECS: list[FilterSpec] = [
    FilterSpec(
        key="op",
        label="Operation",
        ui_kind="text",
        prompt="Operation (INSERT/UPDATE/DELETE): ",
        sql_kind="equal_ci",
        col="Operation",
    ),
    FilterSpec(
        key="instance_id",
        label="InstanceID",
        ui_kind="int",
        prompt="InstanceID: ",
        sql_kind="equal",
        col="InstanceID",
    ),
    FilterSpec(
        key="field",
        label="Field Changed",
        ui_kind="text",
        prompt="FieldChanged (e.g. Status, Gate): ",
        sql_kind="equal",
        col="FieldChanged",
    ),
]


AIRPORT_FILTER_SPECS: list[FilterSpec] = [
    FilterSpec(
        key="iata",
        label="Airport IATA",
        ui_kind="text",
        prompt="Airport IATA exact: ",
        sql_kind="equal_ci",
        col="IataCode",
    ),
    FilterSpec(
        key="country",
        label="Country",
        ui_kind="text",
        prompt="Country Contains: ",
        sql_kind="like",
        col="Country",
    ),
]

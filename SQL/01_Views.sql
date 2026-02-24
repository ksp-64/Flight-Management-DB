DROP VIEW IF EXISTS View_AuditLog;
DROP VIEW IF EXISTS View_FlightsDetailedWithPilots;
DROP VIEW IF EXISTS View_FlightsPerPilot;
DROP VIEW IF EXISTS View_FlightsPerDestination;
DROP VIEW IF EXISTS View_PilotSchedule;
DROP VIEW IF EXISTS View_FlightLookup;


CREATE VIEW View_FlightLookup AS
SELECT
    f.FlightID,
    a.AirlineID,
    a.Name      AS AirlineName,
    f.FlightNumber,
    r.RouteID,
    ao.IataCode AS OriginIata,
    ao.Name     AS OriginName,
    ad.IataCode AS DestIata,
    ad.Name     AS DestName
FROM Flight f
JOIN Airline a ON a.AirlineID = f.AirlineID
JOIN Route r ON r.RouteID = f.RouteID
JOIN Airport ao ON ao.AirportID = r.OriginAirportID
JOIN Airport ad ON ad.AirportID = r.DestinationAirportID;


CREATE VIEW View_FlightsDetailedWithPilots AS
SELECT
    fi.InstanceID,
    f.FlightID,
    f.FlightNumber,
    fi.FlightDate,
    fi.SchedDepUtc,
    fi.SchedArrUtc,
    fi.ActualDepUtc,
    fi.ActualArrUtc,
    fi.Status,
    fi.Terminal,
    fi.Gate,
    a1.IataCode AS OriginIata,
    a1.Name     AS OriginName,
    a2.IataCode AS DestIata,
    a2.Name     AS DestinationName,
    MAX(CASE WHEN ca.DutyRole = 'Captain' THEN s.FirstName || ' ' || s.LastName END) AS Captain,
    MAX(CASE WHEN ca.DutyRole = 'First Officer' THEN s.FirstName || ' ' || s.LastName END) AS "First Officer"
FROM FlightInstance fi
JOIN Flight f ON f.FlightID = fi.FlightID
JOIN Route r ON r.RouteID = f.RouteID
JOIN Airport a1 ON a1.AirportID = r.OriginAirportID
JOIN Airport a2 ON a2.AirportID = r.DestinationAirportID
LEFT JOIN CrewAssignment ca ON ca.InstanceID = fi.InstanceID
LEFT JOIN Staff s ON s.StaffID = ca.StaffID
GROUP BY
    fi.InstanceID,
    f.FlightID,
    f.FlightNumber,
    fi.FlightDate,
    fi.SchedDepUtc,
    fi.SchedArrUtc,
    fi.ActualDepUtc,
    fi.ActualArrUtc,
    fi.Status,
    fi.Terminal,
    fi.Gate,
    a1.IataCode,
    a1.Name,
    a2.IataCode,
    a2.Name;


CREATE VIEW View_PilotSchedule AS
SELECT
    s.StaffID,
    s.FirstName,
    s.LastName,
    ca.DutyRole,
    fi.InstanceID,
    f.FlightNumber,
    fi.FlightDate,
    fi.SchedDepUtc,
    fi.SchedArrUtc,
    fi.Status
FROM CrewAssignment ca
JOIN Staff s ON s.StaffID = ca.StaffID
JOIN FlightInstance fi ON fi.InstanceID = ca.InstanceID
JOIN Flight f ON f.FlightID = fi.FlightID
WHERE s.Role = 'Pilot';


CREATE VIEW View_FlightsPerDestination AS
SELECT
    a2.IataCode AS DestIata,
    a2.Name     AS DestinationName,
    COUNT(*)    AS Flights
FROM Flight f
JOIN Route r ON r.RouteID = f.RouteID
JOIN Airport a2 ON a2.AirportID = r.DestinationAirportID
GROUP BY a2.IataCode, a2.Name;


CREATE VIEW View_FlightsPerPilot AS
SELECT
    s.StaffID,
    s.FirstName,
    s.LastName,
    COUNT(*) AS AssignedInstances
FROM CrewAssignment ca
JOIN Staff s ON s.StaffID = ca.StaffID
WHERE s.Role = 'Pilot'
GROUP BY s.StaffID, s.FirstName, s.LastName;


CREATE VIEW View_AuditLog AS
WITH base AS (
    SELECT
        a.LogID,
        a.TableName,
        a.Operation,
        a.RecordID,
        a.OldValue,
        a.NewValue,
        a.ChangedAt,
        a.ChangedBy,
        COALESCE(fi.InstanceID, CAST(a.RecordID AS INTEGER)) AS InstanceID,
        COALESCE(
            fi.FlightID,
            CAST(json_extract(a.NewValue, '$.FlightID') AS INTEGER),
            CAST(json_extract(a.OldValue, '$.FlightID') AS INTEGER)
        ) AS FlightID,
        COALESCE(
            fi.FlightDate,
            json_extract(a.NewValue, '$.Date'),
            json_extract(a.OldValue, '$.Date')
        ) AS FlightDate
    FROM AuditLog a
    LEFT JOIN FlightInstance fi ON fi.InstanceID = CAST(a.RecordID AS INTEGER)
    WHERE a.TableName IN ('FlightInstance', 'CrewAssignment')
      AND a.ChangedBy = 'USER'
),
all_keys AS (
    SELECT b.LogID, je.key AS FieldChanged
    FROM base b
    JOIN json_each(COALESCE(b.OldValue, '{}')) AS je
    UNION
    SELECT b.LogID, je.key AS FieldChanged
    FROM base b
    JOIN json_each(COALESCE(b.NewValue, '{}')) AS je
)
SELECT
    b.LogID,
    b.TableName,
    b.Operation,
    b.RecordID,
    b.InstanceID,
    f.FlightNumber,
    b.FlightID,
    b.FlightDate,
    k.FieldChanged,
    json_extract(b.OldValue, '$.' || k.FieldChanged) AS OldValue,
    json_extract(b.NewValue, '$.' || k.FieldChanged) AS NewValue,
    b.ChangedAt,
    b.ChangedBy
FROM base b
JOIN all_keys k ON k.LogID = b.LogID
LEFT JOIN Flight f ON f.FlightID = b.FlightID
WHERE
    json_extract(b.OldValue, '$.' || k.FieldChanged)
    IS NOT
    json_extract(b.NewValue, '$.' || k.FieldChanged);

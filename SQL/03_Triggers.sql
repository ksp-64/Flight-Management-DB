DROP TRIGGER IF EXISTS Log_FlightInstance_Insert;
DROP TRIGGER IF EXISTS Log_FlightInstance_Update;
DROP TRIGGER IF EXISTS Log_FlightInstance_Delete;
DROP TRIGGER IF EXISTS Log_CrewAssignment_Insert;
DROP TRIGGER IF EXISTS Log_CrewAssignment_Update;
DROP TRIGGER IF EXISTS Log_CrewAssignment_Delete;
DROP TRIGGER IF EXISTS Validate_FlightInstance_Insert_StatusVsActualArrUtc;
DROP TRIGGER IF EXISTS Validate_FlightInstance_Update_StatusVsActualArrUtc;

UPDATE FlightInstance
SET Status = 'Landed'
WHERE ActualArrUtc IS NOT NULL
  AND Status = 'Delayed';

CREATE TRIGGER Validate_FlightInstance_Insert_StatusVsActualArrUtc
BEFORE INSERT
ON FlightInstance
WHEN NEW.ActualArrUtc IS NOT NULL
 AND NEW.Status = 'Delayed'
BEGIN
    SELECT RAISE(ABORT, 'Status cannot be Delayed when ActualArrUtc is set. Use Landed.');
END;

CREATE TRIGGER Validate_FlightInstance_Update_StatusVsActualArrUtc
BEFORE UPDATE OF Status, ActualArrUtc
ON FlightInstance
WHEN NEW.ActualArrUtc IS NOT NULL
 AND NEW.Status = 'Delayed'
BEGIN
    SELECT RAISE(ABORT, 'Status cannot be Delayed when ActualArrUtc is set. Use Landed.');
END;

CREATE TRIGGER Log_FlightInstance_Insert
AFTER INSERT
ON FlightInstance
BEGIN
    INSERT INTO AuditLog (TableName, Operation, RecordID, NewValue, ChangedBy)
    VALUES ('FlightInstance',
            'INSERT',
            NEW.InstanceID,
            json_object(
                    'FlightID', NEW.FlightID,
                    'Date', NEW.FlightDate,
                    'SchedDepUtc', NEW.SchedDepUtc,
                    'SchedArrUtc', NEW.SchedArrUtc,
                    'Status', NEW.Status,
                    'Terminal', NEW.Terminal,
                    'Gate', NEW.Gate,
                    'AircraftID', NEW.AircraftID
            ),
            (SELECT CurrentUser FROM AppContext WHERE ContextID = 1));
END;

CREATE TRIGGER Log_FlightInstance_Update
AFTER UPDATE OF
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
    ON FlightInstance
    WHEN
        OLD.FlightID IS NOT NEW.FlightID OR
        OLD.FlightDate IS NOT NEW.FlightDate OR
        OLD.SchedDepUtc IS NOT NEW.SchedDepUtc OR
        OLD.SchedArrUtc IS NOT NEW.SchedArrUtc OR
        OLD.ActualDepUtc IS NOT NEW.ActualDepUtc OR
        OLD.ActualArrUtc IS NOT NEW.ActualArrUtc OR
        OLD.Status IS NOT NEW.Status OR
        OLD.Terminal IS NOT NEW.Terminal OR
        OLD.Gate IS NOT NEW.Gate OR
        OLD.AircraftID IS NOT NEW.AircraftID
BEGIN
INSERT INTO AuditLog (TableName, Operation, RecordID, OldValue, NewValue, ChangedBy)
VALUES ('FlightInstance',
        'UPDATE',
        OLD.InstanceID,
        json_object(
                  'FlightID', OLD.FlightID,
                  'Date', OLD.FlightDate,
                  'SchedDepUtc', OLD.SchedDepUtc,
                  'SchedArrUtc', OLD.SchedArrUtc,
                  'ActualDepUtc', OLD.ActualDepUtc,
                  'ActualArrUtc', OLD.ActualArrUtc,
                  'Status', OLD.Status,
                  'Terminal', OLD.Terminal,
                  'Gate', OLD.Gate,
                  'AircraftID', OLD.AircraftID),
        json_object(
                  'FlightID', NEW.FlightID,
                  'Date', NEW.FlightDate,
                  'SchedDepUtc', NEW.SchedDepUtc,
                  'SchedArrUtc', NEW.SchedArrUtc,
                  'ActualDepUtc', NEW.ActualDepUtc,
                  'ActualArrUtc', NEW.ActualArrUtc,
                  'Status', NEW.Status,
                  'Terminal', NEW.Terminal,
                  'Gate', NEW.Gate,
                  'AircraftID', NEW.AircraftID),
            (SELECT CurrentUser FROM AppContext WHERE ContextID = 1));
END;

CREATE TRIGGER Log_FlightInstance_Delete
AFTER DELETE
ON FlightInstance
BEGIN
    INSERT INTO AuditLog (TableName, Operation, RecordID, OldValue, ChangedBy)
    VALUES ('FlightInstance',
            'DELETE',
            OLD.InstanceID,
            json_object(
                    'FlightID', OLD.FlightID,
                    'Date', OLD.FlightDate,
                    'SchedDepUtc', OLD.SchedDepUtc,
                    'SchedArrUtc', OLD.SchedArrUtc,
                    'ActualDepUtc', OLD.ActualDepUtc,
                    'ActualArrUtc', OLD.ActualArrUtc,
                    'Status', OLD.Status,
                    'Terminal', OLD.Terminal,
                    'Gate', OLD.Gate,
                    'AircraftID', OLD.AircraftID
            ),
            (SELECT CurrentUser FROM AppContext WHERE ContextID = 1));
END;

CREATE TRIGGER Log_CrewAssignment_Insert
AFTER INSERT ON CrewAssignment
BEGIN
    INSERT INTO AuditLog (TableName, Operation, RecordID, NewValue, ChangedBy)
    VALUES (
        'CrewAssignment',
        'INSERT',
        NEW.InstanceID,
        json_object('StaffID', NEW.StaffID, 'DutyRole', NEW.DutyRole),
        (SELECT CurrentUser FROM AppContext WHERE ContextID = 1)
    );
END;

CREATE TRIGGER Log_CrewAssignment_Update
AFTER UPDATE ON CrewAssignment
BEGIN
    INSERT INTO AuditLog (TableName, Operation, RecordID, OldValue, NewValue, ChangedBy)
    VALUES (
        'CrewAssignment',
        'UPDATE',
        NEW.InstanceID,
        json_object('StaffID', OLD.StaffID, 'DutyRole', OLD.DutyRole),
        json_object('StaffID', NEW.StaffID, 'DutyRole', NEW.DutyRole),
        (SELECT CurrentUser FROM AppContext WHERE ContextID = 1)
    );
END;

CREATE TRIGGER Log_CrewAssignment_Delete
AFTER DELETE ON CrewAssignment
BEGIN
    INSERT INTO AuditLog (TableName, Operation, RecordID, OldValue, ChangedBy)
    VALUES (
        'CrewAssignment',
        'DELETE',
        OLD.InstanceID,
        json_object('StaffID', OLD.StaffID, 'DutyRole', OLD.DutyRole),
        (SELECT CurrentUser FROM AppContext WHERE ContextID = 1)
    );
END;

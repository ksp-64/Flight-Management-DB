PRAGMA foreign_keys = ON;

-- Dropping order from children to parents

DROP TABLE IF EXISTS BookingItem;
DROP TABLE IF EXISTS Booking;
DROP TABLE IF EXISTS CrewAssignment;
DROP TABLE IF EXISTS Passenger;
DROP TABLE IF EXISTS Staff;
DROP TABLE IF EXISTS FlightInstance;
DROP TABLE IF EXISTS Flight;
DROP TABLE IF EXISTS Aircraft;
DROP TABLE IF EXISTS Route;
DROP TABLE IF EXISTS Airport;
DROP TABLE IF EXISTS Airline;
DROP TABLE IF EXISTS AuditLog;
DROP TABLE IF EXISTS AppContext;

-------------------------------------
CREATE TABLE AppContext
(
    ContextID   INTEGER PRIMARY KEY CHECK (ContextID = 1),
    CurrentUser TEXT NOT NULL
);

INSERT OR IGNORE INTO AppContext (ContextID, CurrentUser)
VALUES (1, 'CLI');


-- Operations (Ops)
------------------
CREATE TABLE Airline
(
    AirlineID INTEGER PRIMARY KEY,
    IataCode  TEXT CHECK (length(IataCode) = 2),
    IcaoCode  TEXT CHECK (length(IcaoCode) = 3),
    Name      TEXT NOT NULL,
    Active    INTEGER NOT NULL DEFAULT 1 CHECK (Active IN (0, 1))
);

CREATE TABLE Airport
(
    AirportID INTEGER PRIMARY KEY,
    IataCode  TEXT CHECK (length(IataCode) = 3),
    IcaoCode  TEXT CHECK (length(IcaoCode) = 4),
    Name      TEXT NOT NULL,
    City      TEXT,
    Country   TEXT,
    Timezone  TEXT,
    Dst       TEXT
);

CREATE TABLE Aircraft
(
    AircraftID   INTEGER PRIMARY KEY,
    TailNumber   TEXT,
    Manufacturer TEXT,
    Model        TEXT,
    SeatCapacity INTEGER CHECK (SeatCapacity > 0),
    InService    INTEGER NOT NULL DEFAULT 1 CHECK (InService IN (0, 1))
);

CREATE TABLE Route
(
    RouteID              INTEGER PRIMARY KEY,
    OriginAirportID      INTEGER NOT NULL,
    DestinationAirportID INTEGER NOT NULL,
    DistanceKm           INTEGER CHECK (DistanceKm > 0),
    FOREIGN KEY(OriginAirportID) REFERENCES Airport(AirportID)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY(DestinationAirportID) REFERENCES Airport(AirportID)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CHECK (OriginAirportID <> DestinationAirportID)
);

CREATE TABLE Flight
(
    FlightID     INTEGER PRIMARY KEY,
    AirlineID    INTEGER NOT NULL,
    FlightNumber TEXT    NOT NULL,
    RouteID      INTEGER NOT NULL,
    FOREIGN KEY(AirlineID) REFERENCES Airline(AirlineID)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY(RouteID) REFERENCES Route(RouteID)
        ON UPDATE CASCADE ON DELETE RESTRICT,

    UNIQUE (AirlineID, FlightNumber)
);

CREATE TABLE FlightInstance
(
    InstanceID   INTEGER PRIMARY KEY,
    FlightID     INTEGER NOT NULL,
    FlightDate   TEXT    NOT NULL
        CHECK (date(FlightDate) IS NOT NULL)
        CHECK (strftime('%Y-%m-%d', FlightDate) = FlightDate),
    SchedDepUtc  TEXT    NOT NULL
        CHECK (datetime(SchedDepUtc) IS NOT NULL)
        CHECK (strftime('%Y-%m-%d %H:%M:%S', SchedDepUtc) = SchedDepUtc),
    SchedArrUtc  TEXT    NOT NULL
        CHECK (datetime(SchedArrUtc) IS NOT NULL)
        CHECK (strftime('%Y-%m-%d %H:%M:%S', SchedArrUtc) = SchedArrUtc),
    ActualDepUtc TEXT
        CHECK (ActualDepUtc IS NULL OR (
            datetime(ActualDepUtc) IS NOT NULL AND
            strftime('%Y-%m-%d %H:%M:%S', ActualDepUtc) = ActualDepUtc
            )),
    ActualArrUtc TEXT
        CHECK (ActualArrUtc IS NULL OR (
            datetime(ActualArrUtc) IS NOT NULL AND
            strftime('%Y-%m-%d %H:%M:%S', ActualArrUtc) = ActualArrUtc
            )),
    Status       TEXT NOT NULL CHECK (Status IN ('Scheduled', 'Active', 'Landed', 'Delayed', 'Cancelled', 'Diverted')),
    Terminal     TEXT,
    Gate         TEXT,
    AircraftID   INTEGER NOT NULL,
    FOREIGN KEY(FlightID) REFERENCES Flight(FlightID)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY(AircraftID) REFERENCES Aircraft(AircraftID)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CHECK (SchedArrUtc > SchedDepUtc),
    CHECK (ActualArrUtc IS NULL OR ActualDepUtc IS NULL OR ActualArrUtc > ActualDepUtc),
    CHECK (ActualArrUtc IS NULL OR Status <> 'Delayed')
);

-- Human Resources (HR)
----------------------

CREATE TABLE Staff
(
    StaffID       INTEGER PRIMARY KEY,
    FirstName     TEXT    NOT NULL,
    LastName      TEXT    NOT NULL,
    Role          TEXT    NOT NULL CHECK (Role IN ('Pilot', 'Ground Staff', 'Cabin Crew', 'Dispatcher')),
    BaseAirportID INTEGER NOT NULL,
    FOREIGN KEY(BaseAirportID) REFERENCES Airport(AirportID)
        ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE CrewAssignment
(
    CrewAssignmentID INTEGER PRIMARY KEY,
    InstanceID       INTEGER NOT NULL,
    StaffID          INTEGER NOT NULL,
    DutyRole         TEXT NOT NULL CHECK (DutyRole IN ('Cabin Crew', 'Standby', 'First Officer', 'Purser', 'Captain', 'Ops', 'Crew')),
    FOREIGN KEY(InstanceID) REFERENCES FlightInstance(InstanceID)
        ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY(StaffID) REFERENCES Staff(StaffID)
        ON UPDATE CASCADE ON DELETE CASCADE,
    UNIQUE(InstanceID, StaffID)
);


-- Customer (CRM)
-----------------
-- These tables are intentionally retained even though the current CLI menus
-- focus on operations/HR workflows. Keeping CRM entities supports discussion
-- of normalisation and future extension (manifests, bookings, check-in).

CREATE TABLE Passenger
(
    PassportNo  TEXT NOT NULL,
    Nationality TEXT NOT NULL,
    FirstName   TEXT NOT NULL,
    LastName    TEXT NOT NULL,
    Dob         TEXT
        CHECK (
            Dob IS NULL OR (
            date(Dob) IS NOT NULL
            AND strftime('%Y-%m-%d', Dob) = Dob
              )
            ),
    Email TEXT,
    Phone TEXT,
    PRIMARY KEY (PassportNo, Nationality)
);

CREATE TABLE Booking
(
    BookingID INTEGER PRIMARY KEY,
    Pnr       TEXT NOT NULL UNIQUE,
    BookedAt  TEXT NOT NULL
        CHECK ( datetime(BookedAt) IS NOT NULL AND strftime('%Y-%m-%d %H:%M:%S', BookedAt) = BookedAt),
    Status TEXT NOT NULL CHECK (Status IN ('Confirmed', 'Pending', 'Cancelled'))
);

CREATE TABLE BookingItem
(
    BookingItemID INTEGER PRIMARY KEY,
    BookingID     INTEGER NOT NULL,
    InstanceID    INTEGER NOT NULL,
    PassportNo    TEXT    NOT NULL,
    Nationality   TEXT    NOT NULL,
    SeatNo        TEXT,
    CabinClass    TEXT CHECK (CabinClass IN ('Premium Economy', 'Economy', 'Business', 'First')),
    ItemStatus    TEXT CHECK (ItemStatus IN ('Boarded', 'Confirmed', 'CheckedIn', 'Cancelled')),
    FOREIGN KEY(BookingID) REFERENCES Booking(BookingID)
        ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY(InstanceID) REFERENCES FlightInstance(InstanceID)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY(PassportNo, Nationality)
        REFERENCES Passenger(PassportNo, Nationality)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    UNIQUE (InstanceID, SeatNo)
);

-- Audit
-------

CREATE TABLE AuditLog
(
    LogID     TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    TableName TEXT NOT NULL,
    Operation TEXT NOT NULL CHECK (Operation IN ('INSERT', 'UPDATE', 'DELETE')),
    RecordID  TEXT NOT NULL,
    OldValue  TEXT,
    NewValue  TEXT,
    ChangedAt TEXT DEFAULT CURRENT_TIMESTAMP,
    ChangedBy TEXT DEFAULT 'CLI'
);

-- Indexes
----------

CREATE INDEX IdxInstanceDate ON FlightInstance (FlightDate);
CREATE INDEX IdxBookingItemBooking ON BookingItem (BookingID);
CREATE INDEX IdxPassengerName ON Passenger (LastName);
CREATE INDEX IdxRouteOrigin ON Route (OriginAirportID);
CREATE INDEX IdxRouteDest ON Route (DestinationAirportID);
CREATE INDEX IdxFlightRoute ON Flight (RouteID);
CREATE INDEX IdxInstanceFlight ON FlightInstance (FlightID);
CREATE INDEX IdxBookingItemInstance ON BookingItem (InstanceID);
CREATE INDEX IdxCrewStaff ON CrewAssignment (StaffID);

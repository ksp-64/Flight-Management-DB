# Flight Management DB

Simple command-line app for managing flight operations data with SQLite and Python.

## Requirements
- GitHub account with Codespaces enabled
- Or local Python 3.10+ with `pip`

## GitHub Codespaces
1. In GitHub, open this repository. in `Codespaces`
2. Wait for the container to finish setup (dependencies install automatically from `requirements.txt` via `.devcontainer/devcontainer.json`).
3.Run:
```bash
python3 src/App.py
```

## Local Setup (Fallback)
If Codespaces/devcontainer is not available:
1. Check Python:
```bash
python3 --version
```
2. Create a virtual environment:
```bash
python3 -m venv .venv
```
3. Activate it:
```bash
source .venv/bin/activate
```
4. Upgrade pip:
```bash
pip install --upgrade pip
```
5. Install dependencies:
```bash
pip install -r requirements.txt
```
  Or
```bash
pip install tabulate
```
6. Run the app:
```bash
python3 src/App.py
```

## What the App Does
```text
Flight Management Menu
----------------------
1) View Flights by Criteria
2) Update Flight Information (Field, Assign Pilot, Delete Flight)
3) View Pilot Schedule
4) View/Update Destination Information
5) Add a New Flight
6) Summary Reports
7) View Audit Log
8) Exit

Extra:
R) Reset Database and Reseed
Choose:
```

## Database Behaviour
- Database file: `DB/FlightManagement.db`
- First run: creates schema, views, triggers, and seed data from `SQL/`
- Later runs: keeps existing data and refreshes views/triggers
- Use menu option `R` to reset and reseed the database

## Project Structure
```text
Flight-Management-DB/
├── DB/
│   └── FlightManagement.db
├── Data/
├── SQL/
│   ├── 00_Schema.sql
│   ├── 01_Views.sql
│   ├── 03_Triggers.sql
│   └── Inserts/
│       ├── 01_Airline.sql
│       ├── 02_Airport.sql
│       ├── 03_Aircraft.sql
│       ├── 04_Route.sql
│       ├── 05_Flight.sql
│       ├── 06_FlightInstance.sql
│       ├── 07_Staff.sql
│       ├── 08_Passenger.sql
│       ├── 09_Booking.sql
│       ├── 10_CrewAssignment.sql
│       └── 11_BookingItem.sql
├── src/
│   ├── ActionsWorkflows.py
│   ├── AllFilterSpecs.py
│   ├── App.py
│   ├── FilterSQL.py
│   ├── Queries.py
│   ├── SeedDB.py
│   └── UI.py
├── requirements.txt
└── README.md
```

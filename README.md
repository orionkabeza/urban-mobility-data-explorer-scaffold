# Urban Mobility Data Explorer — MoMo SMS ETL & Dashboard

Week 1-2 deliverables for the Enterprise Web Development summative. This
project ingests Mobile Money (MoMo) SMS data (XML), cleans and categorizes
it into a relational database, and serves it through a frontend dashboard.

## Team Name

_TBD_

## Project Description

This project is built around processing MoMo SMS transaction data that comes in XML format.

The data goes through an ETL pipeline where it is parsed, cleaned, normalized, and sorted into different transaction categories before being stored in a relational database.

Once the data is ready, a lightweight frontend dashboard is used to display and visualize it in a meaningful way. This serves as the foundation for the larger **Urban Mobility Data Explorer project.**

## Team Members

| Name | Role | GitHub |
| --- | --- | --- |
| Orion Kabeza | Team Lead & ETL (parsing) | [orionkabeza](https://github.com/orionkabeza) |
| Mpamira Ntwali Djibril | ETL (cleaning & categorization) | [dmpamira-debug](https://github.com/dmpamira-debug) |
| Emmanuel Happy Rangira | Database & Backend API | [erangira-005](https://github.com/erangira-005) |
| kmaster-alt | Frontend Dashboard | [kmaster-alt](https://github.com/kmaster-alt) |
| aubin_00 | Architecture & Scrum Board | [zotyall](https://github.com/zotyall) |

## Week 1 Task Assignments

| Task | Owner | Status |
| --- | --- | --- |
| Repo setup & invite collaborators | Orion Kabeza | Done |
| Project directory scaffold | Orion Kabeza | Done |
| README (team, description, links) | Orion Kabeza | In Progress |
| System architecture diagram (draw.io/Miro) | aubin_00 | To Do |
| Scrum board setup (GitHub Projects/Trello/Jira) | aubin_00 | Done |
| XML parsing (`etl/parse_xml.py`, `tests/test_parse_xml.py`) | Orion Kabeza | To Do |
| Cleaning & normalization (`etl/clean_normalize.py`, `tests/test_clean_normalize.py`) | Mpamira Ntwali Djibril | To Do |
| Categorization rules (`etl/categorize.py`, `tests/test_categorize.py`) | Mpamira Ntwali Djibril | To Do |
| DB schema & loader (`etl/load_db.py`) | Emmanuel Happy Rangira | To Do |
| Backend API (`api/app.py`, `api/db.py`, `api/schemas.py`) | Emmanuel Happy Rangira | To Do |
| Frontend dashboard (`index.html`, `web/`) | kmaster-alt | To Do |

## Week 2 Task Assignments

Orion drafted a full working schema (`database/database_setup.sql`,
`docs/erd_diagram.drawio`, `examples/json_schemas.json`) as a starting point
so the team could see the whole design at once. **That draft is currently
all committed under one author** — per the grading rule that individual
marks come strictly from technical contributions visible in `git log`/`git
blame`, each owner below needs to re-commit their section themselves
(edit, extend, or at minimum re-save-and-commit their block) before
submission, not just leave Orion's draft as-is:

| Task | Owner | Status |
| --- | --- | --- |
| `sms_messages` table (DDL, indexes, sample data) | Orion Kabeza | Committed by Orion |
| ERD render, design doc, MySQL 8.0 verification screenshots, final integration commit merging all table blocks into one working script | Orion Kabeza | Committed by Orion; integration pending until others commit their sections |
| `transactions` + `transaction_participants` tables (hub + M:N junction, FK/CHECK constraints) | Emmanuel Happy Rangira | Drafted by Orion — needs Emmanuel's own commit |
| `users` table (DDL/DML) | Kenneth Master | Drafted by Orion — needs Kenneth's own commit |
| `examples/json_schemas.json` (JSON serialization modeling) | Kenneth Master | Drafted by Orion — needs Kenneth's own commit |
| `transaction_categories` table (DDL/DML) | Mfura Axel Aubin | Drafted by Orion — needs Mfura's own commit |
| `docs/erd_diagram.drawio` (editable ERD source) | Mfura Axel Aubin | Drafted by Orion — needs Mfura's own commit |
| Sample-query section of the design doc, run against MySQL 8.0 | Mfura Axel Aubin | Drafted by Orion — needs Mfura's own commit |
| `system_logs` table (DDL/DML, ETL audit trail) | Mpamira Ntwali Djibril | Drafted by Orion — needs Djibril's own commit |

## Database Design (Week 2)

The database schema was reverse-engineered directly from `data/raw/momo.xml`
(11 distinct SMS message shapes: incoming money, payment to code holder,
bank deposit, transfer to mobile number, airtime/cash power/bundle bill
payments, third-party debits, agent withdrawals, failures, and reversals).

- **ERD**: [`docs/erd_diagram.png`](docs/erd_diagram.png) (image) /
  [`docs/erd_diagram.drawio`](docs/erd_diagram.drawio) (editable source —
  open at [app.diagrams.net](https://app.diagrams.net))
- **SQL schema**: [`database/database_setup.sql`](database/database_setup.sql)
  — MySQL 8.0 DDL (6 tables, FK/CHECK constraints, indexes) + sample DML
- **JSON serialization examples**: [`examples/json_schemas.json`](examples/json_schemas.json)
- **Full design doc** (rationale, data dictionary, verified queries,
  constraint-violation screenshots run against real MySQL 8.0):
  [`docs/database_design.md`](docs/database_design.md)

Six entities: `users`, `transaction_categories`, `sms_messages`,
`transactions`, `transaction_participants` (the many-to-many junction
resolving `users` ↔ `transactions`), and `system_logs` (ETL audit trail).

## Setup & Run Instructions

```bash
# 1. Clone the repo and enter it
git clone https://github.com/orionkabeza/urban-mobility-data-explorer.git
cd urban-mobility-data-explorer

# 2. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy the environment template and fill in real values
cp .env.example .env

# 5. Run the ETL pipeline
./scripts/run_etl.sh

# 6. Serve the frontend dashboard
./scripts/serve_frontend.sh
```

_Instructions will be filled in as each stage (ETL, API, frontend) is
implemented._

## Architecture Diagram

![System architecture diagram](docs/architecture.png)

The pipeline: `MoMo SMS XML` -> ETL (`parse -> clean -> categorize -> load`) -> `SQLite DB`, with invalid records routed to a dead-letter log. The API layer (FastAPI) is optional/bonus; the frontend dashboard reads either from the API or directly from the processed data if the API is skipped.

## Scrum Board

[Trello board](https://trello.com/invite/b/6a9b871ca635a4268f44d10d/ATTIeac71249d169effb450ef9518f18446385DF072A/my-trello-board)

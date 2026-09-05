# Urban Mobility Data Explorer — MoMo SMS ETL & Dashboard

Week 1 deliverable: team setup and project planning for the Enterprise Web
Development summative. This project ingests Mobile Money (MoMo) SMS data
(XML), cleans and categorizes it into a relational database, and serves it
through a frontend dashboard.

## Team Name

_TBD_

## Project Description

This project builds an ETL pipeline and dashboard for MoMo SMS transaction
data as the foundation for the **Urban Mobility Data Explorer** summative
project. Raw XML SMS exports are parsed, cleaned/normalized, categorized by
transaction type, and loaded into a relational database. A lightweight
frontend dashboard visualizes the processed data.

## Team Members

| Name | Role | GitHub |
| --- | --- | --- |
| _TBD_ | _TBD_ | _TBD_ |
| _TBD_ | _TBD_ | _TBD_ |
| _TBD_ | _TBD_ | _TBD_ |

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

_Link to the architecture diagram: TBD_

## Scrum Board

_Link to the Scrum board (e.g. GitHub Projects / Trello / Jira): TBD_

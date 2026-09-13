# Systematic Review Tool

> **Portfolio / Demo Version** — the `demo` branch is prepared specifically as a safe, low-friction portfolio showcase.

A collaborative web application for managing the study-selection stages of a systematic review. It replaces scattered spreadsheets with one workflow for importing references, independent screening, conflict resolution, full-text review and export.

## What you can try

- Open the preloaded fictional review, **Urban green spaces and wellbeing**.
- Select **Alex Morgan** in both “Log in as” fields.
- Screen pending titles and abstracts.
- Inspect and resolve reviewer conflicts.
- Define hierarchical exclusion reasons.
- Explore progress and reviewer-contribution dashboards.
- Import the included Web of Science or Scopus samples.
- Export study lists and final decisions to Excel.

> Screenshot: add the final public-demo screenshot at `docs/demo-overview.png` after deployment.

## Recommended experience: online demo

The repository is deployment-ready for Render. Once the service has been created, place its URL here:

**Live demo:** _deployment URL pending_

Free Render services can take about a minute to wake after a period of inactivity. Demo data is fictional and the free deployment uses disposable storage, so it may reset when the service restarts.

## Run locally

### Windows

Requirements: Git and Python 3.11–3.13.

```powershell
git clone --branch demo --single-branch https://github.com/DiegoJSN/syst_rev_tool.git
cd syst_rev_tool
powershell -ExecutionPolicy Bypass -File .\run_demo.ps1
```

Open <http://127.0.0.1:5000>. No PostgreSQL, Tailscale, credentials or environment-file setup is required.

### macOS / Linux

```bash
git clone --branch demo --single-branch https://github.com/DiegoJSN/syst_rev_tool.git
cd syst_rev_tool
sh ./run_demo.sh
```

### Docker

```bash
docker build -t syst-rev-demo .
docker run --rm -p 5000:5000 syst-rev-demo
```

Then open <http://127.0.0.1:5000>.

## Deploy on Render

1. Create a Render account and choose **New → Blueprint**.
2. Connect this GitHub repository and select the `demo` branch.
3. Render detects `render.yaml`; confirm the free service.
4. Copy the resulting URL into the “Live demo” section above and into your CV.

The blueprint generates the session secret. No personal keys or database credentials are committed.

## Technology

- Python and Flask
- Jinja2 templates, Bootstrap and DataTables
- SQLite for the zero-configuration demo
- PostgreSQL via Psycopg for the original collaborative deployment
- OpenPyXL and Python Calamine for spreadsheet import/export
- Gunicorn and Docker for deployment

## Project structure

```text
app.py                    Flask routes and review workflow
db.py                     SQLite/PostgreSQL access, schema and demo fixtures
templates/                Server-rendered interface
static/                   CSS and browser-side behaviour
example_studies_list/     Sample WoS and Scopus imports
tests/                    Demo smoke tests
Dockerfile                Reproducible production image
render.yaml               One-click Render blueprint
```

## Configuration

The demo defaults to:

```text
DEMO_MODE=true
DATABASE_URL=sqlite:///instance/demo.db
```

For a durable multi-user installation, copy `.env.example`, set `DEMO_MODE=false`, provide a PostgreSQL `DATABASE_URL`, and set a strong random `SECRET_KEY`.

## Verification

```bash
python -m unittest discover -s tests -v
```

The smoke tests cover the health endpoint, seeded home page, review dashboard, review creation and Excel export.

## Demo limitations

- Data is fictional and intended only to demonstrate the workflow.
- The free hosted filesystem is disposable; it is not a production datastore.
- Reviewer selection is workflow identification, not secure authentication.
- The demo is not intended for sensitive, personal or unpublished research data.
- The browser UI loads Bootstrap and DataTables from public CDNs.
- Included sample PDFs are not required by the demo and should be reviewed for redistribution rights before a public release.

## Differences from the original project

The original deployment expected a manually configured PostgreSQL server exposed to reviewers through Tailscale. This branch adds a seeded SQLite mode, portable launch scripts, health checks, Docker/Render deployment and portfolio-focused documentation while retaining PostgreSQL support and the original review workflow.

## Portfolio note

This branch is deliberately optimized as a **Portfolio / Demo Version**. The production-style architecture, dual database support, reference-import pipeline, consensus workflow, exports and containerized deployment are the most relevant technical points to highlight in a CV or interview.

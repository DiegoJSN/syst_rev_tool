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

## Run the demo on your computer

You only need to follow **one** of the two options below:

- **Option 1 — Python:** recommended if Python is already installed.
- **Option 2 — Docker:** recommended if Docker Desktop is already installed.

You do not need PostgreSQL, Tailscale, passwords or an `.env` file.

### Option 1 — Run with Python

#### Windows

1. Install [Git for Windows](https://git-scm.com/download/win).
2. Install [Python 3.13](https://www.python.org/downloads/). On the first installer screen, select **Add python.exe to PATH**, then choose **Install Now**.
3. Open the Start menu, type **PowerShell**, and open **Windows PowerShell**.
4. Copy the entire block below, paste it into PowerShell, and press Enter:

```powershell
git clone --branch demo --single-branch https://github.com/DiegoJSN/syst_rev_tool.git
cd syst_rev_tool
powershell -ExecutionPolicy Bypass -File .\run_demo.ps1
```

The first run downloads the required packages and may take a few minutes. Keep the PowerShell window open while using the demo.

5. When the terminal shows `Running on http://127.0.0.1:5000`, click or copy this address into Chrome, Edge or Firefox: <http://127.0.0.1:5000>.
6. To stop the application, return to PowerShell and press **Ctrl+C**.

#### macOS

1. Install [Python 3.13](https://www.python.org/downloads/macos/).
2. Open **Terminal** from Applications → Utilities.
3. Copy the entire block below, paste it into Terminal, and press Return:

```bash
git clone --branch demo --single-branch https://github.com/DiegoJSN/syst_rev_tool.git
cd syst_rev_tool
sh ./run_demo.sh
```

4. Wait until the terminal shows `Running on http://127.0.0.1:5000`, then open <http://127.0.0.1:5000>.
5. Keep Terminal open. Press **Control+C** there when you want to stop the demo.

If Terminal says `git: command not found`, run `xcode-select --install`, finish the installation, and repeat step 3.

#### Linux

Install Git, Python 3 and the Python virtual-environment package using your distribution's software manager. For Ubuntu or Debian:

```bash
sudo apt update
sudo apt install -y git python3 python3-venv
git clone --branch demo --single-branch https://github.com/DiegoJSN/syst_rev_tool.git
cd syst_rev_tool
sh ./run_demo.sh
```

When the terminal shows the local address, open <http://127.0.0.1:5000>. Press **Ctrl+C** to stop the demo.

### Option 2 — Run with Docker Desktop

Docker packages the application and its dependencies together. You do not need to install Python separately.

1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) for Windows, macOS or Linux.
2. Open Docker Desktop and wait until it reports that Docker is running.
3. Download this repository:
   - Open the [`demo` branch on GitHub](https://github.com/DiegoJSN/syst_rev_tool/tree/demo).
   - Select **Code → Download ZIP**.
   - Extract the downloaded ZIP.
4. Open a terminal inside the extracted folder:
   - **Windows:** open the folder in File Explorer, right-click an empty area and select **Open in Terminal**.
   - **macOS:** open Terminal, type `cd ` including the final space, drag the extracted folder into Terminal, and press Return.
5. Copy and run these commands one at a time:

```bash
docker build -t syst-rev-demo .
docker run --rm -p 5000:5000 syst-rev-demo
```

The first command may take several minutes. When the second command is running, open <http://127.0.0.1:5000>.

To stop the demo, return to the terminal and press **Ctrl+C**. Docker removes the temporary container automatically; the downloaded project folder remains untouched.

### Common problems

- **“python”, “python3” or “git” is not recognized:** close and reopen the terminal after installation. On Windows, reinstall Python and select **Add python.exe to PATH**.
- **Docker says it cannot connect to the daemon:** open Docker Desktop and wait until it has finished starting.
- **Port 5000 is already in use:** stop the other application using that port. With Docker, you can instead run `docker run --rm -p 8080:5000 syst-rev-demo` and open <http://127.0.0.1:8080>.
- **The page does not open:** confirm the terminal is still open and that the application has not displayed an error.
- **You want a clean starting point:** use the **Reset demo** button in the blue banner.

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
- The **Reset demo** control restores the original fixture after experimentation.
- The free hosted filesystem is disposable; it is not a production datastore.
- Reviewer selection is workflow identification, not secure authentication.
- The demo is not intended for sensitive, personal or unpublished research data.
- The browser UI loads Bootstrap and DataTables from public CDNs.
- Included sample PDFs are not required by the demo and should be reviewed for redistribution rights before a public release.

## Differences from the original project

The original deployment expected a manually configured PostgreSQL server exposed to reviewers through Tailscale. This branch adds a seeded SQLite mode, portable launch scripts, health checks, Docker/Render deployment and portfolio-focused documentation while retaining PostgreSQL support and the original review workflow.

## Portfolio note

This branch is deliberately optimized as a **Portfolio / Demo Version**. The production-style architecture, dual database support, reference-import pipeline, consensus workflow, exports and containerized deployment are the most relevant technical points to highlight in a CV or interview.


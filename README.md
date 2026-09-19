# SystRev Tool

> **Portfolio / Demo version**  
> A collaborative web application for managing systematic literature reviews, developed through specification-driven AI coding.

SystRev Tool supports the main workflow of a systematic review, from bibliographic import and duplicate handling to multi-reviewer screening, conflict resolution, full-text management, exclusion criteria, progress tracking, and Excel export.

**The application code for this project was generated entirely using AI.**

The goal of this project is to demonstrate the ability to **design a software system, translate domain knowledge into precise technical specifications, and use AI effectively to turn those specifications into a working product**.

## Demo preview

![SystRev Tool demo](images/systrev-demo.gif)

## Try the demo

The fastest way to test SystRev Tool on Windows:

1. Open the [latest release](https://github.com/DiegoJSN/syst_rev_tool/releases/latest).
2. Under **Assets**, download `SystRevTool-Demo-Windows.zip`.
3. Extract the ZIP file.
4. Run `SystRevTool-Demo.exe`.

No Python, PostgreSQL, Docker, Tailscale, passwords, or API keys are required.

For Python and Docker options, see [Running the demo](#running-the-demo).

### What to look for

A simple way to explore the workflow is to make screening decisions as different reviewers, generate a disagreement, resolve the resulting conflict, and then check how the review progress is updated.

## Project purpose

The application was originally conceived to support the specific needs of a real systematic review project.

The goal was to replace fragmented manual processes with a centralized workflow in which several reviewers could work on the same review, record independent decisions, identify disagreements, resolve conflicts, manage exclusion reasons, attach full-text PDFs, and export the resulting data.

This `demo` branch was prepared specifically for portfolio use. It contains fictional data and a simplified local database so the main workflow can be tested without access to the private production infrastructure.

## How this project was built

**The application code for this project was generated entirely using AI.**

My role was to define and direct the system rather than manually write the application code. I designed the concept, requirements, workflows, relational data structure, business rules, interface behavior, and logical processes, and then guided the AI through their implementation, validation, correction, and refinement.

The project therefore demonstrates my ability to translate domain knowledge into precise technical specifications that an AI coding system can implement effectively.

My previous experience with **relational databases** and **systematic review workflows** was central to this process. It allowed me to reason in advance about how the backend should work, how the entities should relate to each other, how decisions should be stored and consolidated, and how the different review stages should interact.

This made it possible to provide the AI with a clear structural model from the beginning and reduce unnecessary trial-and-error during development.

### My contribution

- System conceptualization and requirements definition
- Systematic review workflow modeling
- Relational database and data relationship design
- Backend logic and business-rule definition
- Multi-reviewer screening and consensus logic
- Conflict-detection and conflict-resolution workflow design
- Definition of exclusion criteria and review-stage transitions
- Prompt design and iterative AI guidance
- Evaluation and validation of AI-generated implementations
- Identification and correction of logical and functional issues
- Definition of the demo, packaging, deployment, and portfolio strategy

### AI contribution

- Generation of the application code from the provided specifications
- Implementation of backend and frontend components
- Implementation of database operations and review workflows
- Code modification and refactoring following iterative instructions
- Assistance with testing, packaging, deployment, and documentation

## Main features

- Import bibliographic records from **Scopus** and **Web of Science**
- Detect and handle duplicate study records
- Manage multiple systematic review projects
- Register and manage multiple reviewers
- First-stage title and abstract screening
- Second-stage full-text screening
- Independent reviewer decisions
- Automated consolidation of reviewer decisions
- Detection of reviewer disagreements
- Dedicated conflict-resolution workflows
- Configurable exclusion reasons
- Full-text PDF upload and viewing
- Reviewer notes
- Progress and contribution tracking
- Study filtering and sorting
- Export of review data and screening decisions to Excel
- Local demo reset to restore the initial fictional dataset

## System logic

The application was designed around the relationships between the main entities involved in a systematic review:

```text
Review
│
├── Reviewers
│
├── Studies
│   │
│   ├── Bibliographic metadata
│   ├── Full-text PDF
│   ├── First-screening decisions
│   ├── Second-screening decisions
│   ├── Notes
│   └── Exclusion reason
│
├── First-screening conflicts
├── Second-screening conflicts
└── Exclusion criteria
```

The screening workflow is based on independent reviewer decisions that are subsequently consolidated according to predefined rules.

When decisions are compatible, the application automatically determines the screening outcome. When reviewers disagree, the study is moved to a dedicated conflict-resolution workflow where the final decision can be recorded explicitly.

This logic was defined before implementation so that the AI could generate the backend around a consistent relational model and a clearly specified set of business rules.

## Technology stack

### Backend

- **Python**
- **Flask**
- **PostgreSQL**
- **SQLite**
- **Psycopg**

### Frontend

- **Jinja2**
- **Bootstrap**
- **DataTables**

### Data import and export

- **OpenPyXL**
- **Python Calamine**
- Scopus CSV import
- Web of Science XLS import
- Excel export

### Deployment and packaging

- **Docker**
- **Gunicorn**
- **Tailscale**
- **GitHub Actions**
- Windows executable packaging

## Engineering highlights

Although the implementation code was AI-generated, the project required defining and validating several non-trivial software behaviors:

- Relational modeling of reviews, studies, reviewers, decisions, and conflicts
- Support for multiple review projects within the same application
- Multi-reviewer decision logic
- Automated consensus rules
- Conflict persistence and resolution
- Separate first- and second-screening workflows
- Exclusion-reason hierarchies
- Bibliographic ingestion from heterogeneous external formats
- Full-text PDF storage and retrieval
- SQLite/PostgreSQL compatibility for demo and production environments
- Automated testing
- Dockerized execution
- GitHub Actions workflows
- Automated Windows executable builds

These elements were progressively specified, tested, and refined through AI-assisted development.

## Demo version vs. full version

### Demo branch

The `demo` branch is designed for portfolio and evaluation purposes.

It uses:

- **SQLite** for zero-configuration local storage
- Fictional example studies
- Fictional reviewer data
- Local persistent screening progress
- Reset functionality
- No production credentials
- No private infrastructure

It can be run using a Windows executable, Python, or Docker.

### Full version

The complete version in the `main` branch uses:

- **PostgreSQL** as the central relational database
- **Tailscale** for private access between authorized devices
- A shared multi-user workflow
- Centralized review data
- Persistent full-text documents and reviewer decisions

The full version was designed for actual collaborative use in a systematic review project.

## What you can test

The demo allows you to:

- Review titles and abstracts as different reviewers
- Record inclusion, exclusion, and intermediate screening decisions
- Add reviewer notes
- Create conflicts by making different reviewer decisions
- Resolve screening conflicts
- Create and manage exclusion reasons
- View each reviewer's contribution
- Track review progress
- Import the included Web of Science and Scopus example files
- Upload and open full-text PDFs
- Export study data and screening decisions to Excel
- Close the demo and continue later with the locally stored state
- Restore the fictional initial dataset with **Reset demo**

## Running the demo

No PostgreSQL server, Tailscale network, passwords, or API keys are required.

Choose one of the following options.

### Option 1: Windows executable

This is the simplest option and does not require Python, Git, or Docker.

1. Open the [latest release](https://github.com/DiegoJSN/syst_rev_tool/releases/latest).
2. Under **Assets**, download `SystRevTool-Demo-Windows.zip`.
3. Extract the ZIP file.
4. Open the extracted folder.
5. Run `SystRevTool-Demo.exe`.
6. Keep the terminal window open while using the application.

The browser should open automatically.

To stop the application, close the terminal window.

### Option 2: Run with Python

Requires:

- [Git](https://git-scm.com/downloads)
- [Python 3.11+](https://www.python.org/downloads/)

#### Windows PowerShell

```powershell
git clone --branch demo --single-branch https://github.com/DiegoJSN/syst_rev_tool.git
cd syst_rev_tool
powershell -ExecutionPolicy Bypass -File .\run_demo.ps1
```

#### macOS or Linux

```bash
git clone --branch demo --single-branch https://github.com/DiegoJSN/syst_rev_tool.git
cd syst_rev_tool
sh ./run_demo.sh
```

Then open:

```text
http://127.0.0.1:5000
```

To stop the application, return to the terminal and press `Ctrl+C`.

### Option 3: Run with Docker

Requires [Docker Desktop](https://www.docker.com/products/docker-desktop/).

Clone or download the `demo` branch, open a terminal in the project folder, and run:

```bash
docker build -t syst-rev-demo .
docker run --rm -p 5000:5000 syst-rev-demo
```

Then open:

```text
http://127.0.0.1:5000
```

To stop the application, press `Ctrl+C`.

## Limitations of the demo

The demo is intended only for portfolio and evaluation purposes.

- All included study and reviewer data are fictional.
- Reviewer selection is not intended as secure authentication.
- SQLite is used for convenience rather than as the production database.
- The local demo should not be used to store sensitive or real research data.
- The demo reproduces the main review workflow but simplifies the private infrastructure used by the full version.

## Branches

- [`demo`](https://github.com/DiegoJSN/syst_rev_tool/tree/demo): portfolio-ready version with fictional data and simplified local infrastructure
- [`main`](https://github.com/DiegoJSN/syst_rev_tool/tree/main): complete project using PostgreSQL and private multi-device access

## Disclaimer

This project is presented as a portfolio example of **AI-assisted software development**.

The software implementation was generated using AI under my direction. The system concept, domain model, workflows, requirements, relational structure, business logic, validation criteria, and iterative development decisions were defined and supervised by me.

The demo is not intended to replace established systematic review platforms or to be used without appropriate validation in production research environments.

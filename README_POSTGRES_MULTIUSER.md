# Multi-user setup (PostgreSQL + Tailscale)

This project was originally using SQLite (a local file). For several reviewers working at the same time, use a shared PostgreSQL database and let each reviewer run the Flask app locally.

## 1) Set the database connection string

Set an environment variable called `DATABASE_URL` before running the app.

Examples:

- Server machine (PostgreSQL running locally):
  - `postgresql://review_user:YOUR_PASSWORD@127.0.0.1:5432/systrev_db`

- Remote reviewer (connects to the server via Tailscale):
  - `postgresql://review_user:YOUR_PASSWORD@100.x.y.z:5432/systrev_db`

## 2) Run the app

```bash
python -m venv venv
# Windows:
venv\Scripts\activate

pip install -r requirements.txt
python app.py
```

## 3) One-time migration from SQLite to PostgreSQL

Run the migration script once (typically on the server machine):

```bash
python migrate_sqlite_to_postgres.py --sqlite path\to\review.db --pg "%DATABASE_URL%" --wipe
```

Notes:
- `--wipe` truncates the PostgreSQL tables before importing.
- Make a backup copy of your SQLite file before migrating.

import os
import sys
import sqlite3
from pathlib import Path
from flask import g

APP_NAME = "syst_rev_tool"
DB_FILENAME = "review.db"


def data_dir() -> Path:
    """
    Carpeta escribible por usuario para guardar DB y archivos persistentes.
    - Windows: %APPDATA%/syst_rev_tool
    - macOS: ~/Library/Application Support/syst_rev_tool
    - Linux:  ~/.local/share/syst_rev_tool  (o $XDG_DATA_HOME)
    """
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))

    p = base / APP_NAME
    p.mkdir(parents=True, exist_ok=True)
    return p


def db_path(app=None) -> str:
    # Mantengo la firma db_path(app) para no tocar tu app.py,
    # pero ya no dependemos de instance_path.
    return str(data_dir() / DB_FILENAME)


def get_db():
    if "db" not in g:
        conn = sqlite3.connect(g._database_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        g.db = conn
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(app):
    path = db_path(app)

    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")

    conn.executescript(
        '''
        CREATE TABLE IF NOT EXISTS review (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            review_name TEXT NOT NULL,
            participants_number INTEGER NOT NULL DEFAULT 0,
            participants_name TEXT NOT NULL DEFAULT '',
            first_screening_progress INTEGER NOT NULL DEFAULT 0,
            second_screening_progress INTEGER NOT NULL DEFAULT 0,
            duplicates_removed INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS reviewers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_review INTEGER NOT NULL,
            reviewer_name TEXT NOT NULL,
            first_screening_contribution INTEGER NOT NULL DEFAULT 0,
            second_screening_contribution INTEGER NOT NULL DEFAULT 0,
            UNIQUE(id_review, reviewer_name),
            FOREIGN KEY (id_review) REFERENCES review(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS studies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_review INTEGER NOT NULL,
            document_type TEXT,
            doi TEXT,
            title TEXT,
            authors TEXT,
            year INTEGER,
            abstract TEXT,
            source_title TEXT,
            first_screening_included TEXT CHECK (first_screening_included IN ('yes','no','conflict') OR first_screening_included IS NULL),
            first_screening_notes TEXT,
            second_screening_included TEXT CHECK (second_screening_included IN ('yes','no','conflict') OR second_screening_included IS NULL),
            second_screening_notes TEXT,
            exclusion_reason INTEGER,
            UNIQUE(id_review, doi),
            UNIQUE(id_review, title, authors, year),
            FOREIGN KEY (id_review) REFERENCES review(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS first_screening (
            id_review INTEGER NOT NULL,
            id_reviewer INTEGER NOT NULL,
            id_study INTEGER NOT NULL,
            decision TEXT NOT NULL CHECK(decision IN ('yes','no','maybe')),
            UNIQUE(id_review, id_reviewer, id_study),
            FOREIGN KEY (id_review) REFERENCES review(id) ON DELETE CASCADE,
            FOREIGN KEY (id_reviewer) REFERENCES reviewers(id) ON DELETE CASCADE,
            FOREIGN KEY (id_study) REFERENCES studies(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS first_screening_conflicts (
            id_review INTEGER NOT NULL,
            id_reviewer INTEGER NOT NULL,
            id_study INTEGER NOT NULL,
            decision TEXT NOT NULL CHECK(decision IN ('yes','no','maybe')),
            UNIQUE(id_review, id_reviewer, id_study),
            FOREIGN KEY (id_review) REFERENCES review(id) ON DELETE CASCADE,
            FOREIGN KEY (id_reviewer) REFERENCES reviewers(id) ON DELETE CASCADE,
            FOREIGN KEY (id_study) REFERENCES studies(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS exclusion_reasons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_review INTEGER NOT NULL,
            hierarchy INTEGER NOT NULL,
            reason TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            UNIQUE(id_review, id, hierarchy),
            FOREIGN KEY (id_review) REFERENCES review(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS second_screening (
            id_review INTEGER NOT NULL,
            id_reviewer INTEGER NOT NULL,
            id_study INTEGER NOT NULL,
            decision TEXT NOT NULL CHECK(decision IN ('yes','no')),
            reason INTEGER,
            UNIQUE(id_review, id_reviewer, id_study),
            FOREIGN KEY (id_review) REFERENCES review(id) ON DELETE CASCADE,
            FOREIGN KEY (id_reviewer) REFERENCES reviewers(id) ON DELETE CASCADE,
            FOREIGN KEY (id_study) REFERENCES studies(id) ON DELETE CASCADE,
            FOREIGN KEY (reason) REFERENCES exclusion_reasons(id)
        );

        CREATE TABLE IF NOT EXISTS second_screening_conflicts (
            id_review INTEGER NOT NULL,
            id_reviewer INTEGER NOT NULL,
            id_study INTEGER NOT NULL,
            decision TEXT NOT NULL CHECK(decision IN ('yes','no')),
            reason INTEGER,
            UNIQUE(id_review, id_reviewer, id_study),
            FOREIGN KEY (id_review) REFERENCES review(id) ON DELETE CASCADE,
            FOREIGN KEY (id_reviewer) REFERENCES reviewers(id) ON DELETE CASCADE,
            FOREIGN KEY (id_study) REFERENCES studies(id) ON DELETE CASCADE,
            FOREIGN KEY (reason) REFERENCES exclusion_reasons(id)
        );

        CREATE INDEX IF NOT EXISTS idx_studies_review ON studies(id_review);
        CREATE INDEX IF NOT EXISTS idx_first_screening_study ON first_screening(id_review, id_study);
        CREATE INDEX IF NOT EXISTS idx_second_screening_study ON second_screening(id_review, id_study);
        '''
    )

    columns = {row["name"] for row in conn.execute("PRAGMA table_info(review);").fetchall()}
    if "duplicates_removed" not in columns:
        conn.execute("ALTER TABLE review ADD COLUMN duplicates_removed INTEGER NOT NULL DEFAULT 0;")

    conn.commit()
    conn.close()
    return path

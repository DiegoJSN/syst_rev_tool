import os
import sqlite3
from flask import g

DB_FILENAME = "review.db"

def db_path(app) -> str:
    return os.path.join(app.instance_path, DB_FILENAME)

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
    os.makedirs(app.instance_path, exist_ok=True)
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
            second_screening_progress INTEGER NOT NULL DEFAULT 0
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
    conn.commit()
    conn.close()
    return path

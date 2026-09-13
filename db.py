from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Optional

from flask import current_app, g

DATABASE_URL_ENV = "DATABASE_URL"


class SQLiteConnection:
    """Adapt PostgreSQL-style parameter markers to Python's built-in SQLite."""

    def __init__(self, path: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")

    def execute(self, statement: str, parameters=()):
        return self.connection.execute(statement.replace("%s", "?"), parameters)

    def commit(self):
        self.connection.commit()

    def rollback(self):
        self.connection.rollback()

    def close(self):
        self.connection.close()


def _database_url(app=None) -> str:
    return (app.config.get("DATABASE_URL") if app else None) or os.environ.get(DATABASE_URL_ENV, "")


def _sqlite_path(url: str, root_path: str) -> str:
    if url == "sqlite:///:memory:":
        return ":memory:"
    raw = url.removeprefix("sqlite:///")
    path = Path(raw)
    return str((path if path.is_absolute() else Path(root_path) / path).resolve())


def get_db():
    if "db" not in g:
        dsn = _database_url(current_app)
        if not dsn:
            raise RuntimeError(f"Missing database DSN. Set {DATABASE_URL_ENV}.")
        g.db = (
            SQLiteConnection(_sqlite_path(dsn, current_app.root_path))
            if dsn.startswith("sqlite:///")
            else _connect_postgres(dsn)
        )
    return g.db


def _connect_postgres(dsn: str):
    import psycopg
    from psycopg.rows import dict_row

    return psycopg.connect(dsn, row_factory=dict_row)


def close_db(e: Optional[BaseException] = None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS review (
 id INTEGER PRIMARY KEY AUTOINCREMENT, review_name TEXT NOT NULL,
 participants_number INTEGER NOT NULL DEFAULT 0, participants_name TEXT NOT NULL DEFAULT '',
 first_screening_progress INTEGER NOT NULL DEFAULT 0, second_screening_progress INTEGER NOT NULL DEFAULT 0,
 duplicates_removed INTEGER NOT NULL DEFAULT 0, two_reviewer_consensus TEXT NOT NULL DEFAULT 'yes',
 password TEXT NOT NULL DEFAULT '');
CREATE TABLE IF NOT EXISTS reviewers (
 id INTEGER PRIMARY KEY AUTOINCREMENT, id_review INTEGER NOT NULL, reviewer_name TEXT NOT NULL,
 first_screening_contribution INTEGER NOT NULL DEFAULT 0, second_screening_contribution INTEGER NOT NULL DEFAULT 0,
 UNIQUE(id_review, reviewer_name), FOREIGN KEY(id_review) REFERENCES review(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS studies (
 id INTEGER PRIMARY KEY AUTOINCREMENT, id_review INTEGER NOT NULL, document_type TEXT, doi TEXT,
 title TEXT, authors TEXT, year INTEGER, abstract TEXT, source_title TEXT, file_name TEXT, file_data BLOB,
 first_screening_included TEXT CHECK(first_screening_included IN ('yes','no','conflict') OR first_screening_included IS NULL),
 first_screening_notes TEXT,
 second_screening_included TEXT CHECK(second_screening_included IN ('yes','no','conflict') OR second_screening_included IS NULL),
 second_screening_notes TEXT, exclusion_reason INTEGER,
 UNIQUE(id_review, doi), UNIQUE(id_review, title, authors, year),
 FOREIGN KEY(id_review) REFERENCES review(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS first_screening (
 id_review INTEGER NOT NULL, id_reviewer INTEGER NOT NULL, id_study INTEGER NOT NULL,
 decision TEXT NOT NULL CHECK(decision IN ('yes','no','maybe')),
 FOREIGN KEY(id_review) REFERENCES review(id) ON DELETE CASCADE,
 FOREIGN KEY(id_reviewer) REFERENCES reviewers(id) ON DELETE CASCADE,
 FOREIGN KEY(id_study) REFERENCES studies(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS first_screening_conflicts (
 id_review INTEGER NOT NULL, id_reviewer INTEGER NOT NULL, id_study INTEGER NOT NULL,
 decision TEXT NOT NULL CHECK(decision IN ('yes','no','maybe')), UNIQUE(id_review,id_reviewer,id_study),
 FOREIGN KEY(id_review) REFERENCES review(id) ON DELETE CASCADE,
 FOREIGN KEY(id_reviewer) REFERENCES reviewers(id) ON DELETE CASCADE,
 FOREIGN KEY(id_study) REFERENCES studies(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS exclusion_reasons (
 id INTEGER PRIMARY KEY AUTOINCREMENT, id_review INTEGER NOT NULL, hierarchy INTEGER NOT NULL,
 reason TEXT NOT NULL, is_active INTEGER NOT NULL DEFAULT 1,
 FOREIGN KEY(id_review) REFERENCES review(id) ON DELETE CASCADE);
CREATE UNIQUE INDEX IF NOT EXISTS idx_exclusion_reasons_active_hierarchy_unique
 ON exclusion_reasons(id_review,hierarchy) WHERE is_active=1;
CREATE TABLE IF NOT EXISTS second_screening (
 id_review INTEGER NOT NULL, id_reviewer INTEGER NOT NULL, id_study INTEGER NOT NULL,
 decision TEXT NOT NULL CHECK(decision IN ('yes','no')), reason INTEGER,
 FOREIGN KEY(id_review) REFERENCES review(id) ON DELETE CASCADE,
 FOREIGN KEY(id_reviewer) REFERENCES reviewers(id) ON DELETE CASCADE,
 FOREIGN KEY(id_study) REFERENCES studies(id) ON DELETE CASCADE,
 FOREIGN KEY(reason) REFERENCES exclusion_reasons(id));
CREATE TABLE IF NOT EXISTS second_screening_conflicts (
 id_review INTEGER NOT NULL, id_reviewer INTEGER NOT NULL, id_study INTEGER NOT NULL,
 decision TEXT NOT NULL CHECK(decision IN ('yes','no')), reason INTEGER,
 UNIQUE(id_review,id_reviewer,id_study),
 FOREIGN KEY(id_review) REFERENCES review(id) ON DELETE CASCADE,
 FOREIGN KEY(id_reviewer) REFERENCES reviewers(id) ON DELETE CASCADE,
 FOREIGN KEY(id_study) REFERENCES studies(id) ON DELETE CASCADE,
 FOREIGN KEY(reason) REFERENCES exclusion_reasons(id));
CREATE INDEX IF NOT EXISTS idx_studies_review ON studies(id_review);
CREATE INDEX IF NOT EXISTS idx_first_screening_study ON first_screening(id_review,id_study);
CREATE INDEX IF NOT EXISTS idx_second_screening_study ON second_screening(id_review,id_study);
"""

POSTGRES_SCHEMA = """
CREATE TABLE IF NOT EXISTS review (id INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY, review_name TEXT NOT NULL, participants_number INTEGER NOT NULL DEFAULT 0, participants_name TEXT NOT NULL DEFAULT '', first_screening_progress INTEGER NOT NULL DEFAULT 0, second_screening_progress INTEGER NOT NULL DEFAULT 0, duplicates_removed INTEGER NOT NULL DEFAULT 0, two_reviewer_consensus TEXT NOT NULL DEFAULT 'yes', password TEXT NOT NULL DEFAULT '');
CREATE TABLE IF NOT EXISTS reviewers (id INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY, id_review INTEGER NOT NULL REFERENCES review(id) ON DELETE CASCADE, reviewer_name TEXT NOT NULL, first_screening_contribution INTEGER NOT NULL DEFAULT 0, second_screening_contribution INTEGER NOT NULL DEFAULT 0, UNIQUE(id_review,reviewer_name));
CREATE TABLE IF NOT EXISTS studies (id INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY, id_review INTEGER NOT NULL REFERENCES review(id) ON DELETE CASCADE, document_type TEXT, doi TEXT, title TEXT, authors TEXT, year INTEGER, abstract TEXT, source_title TEXT, file_name TEXT, file_data BYTEA, first_screening_included TEXT CHECK(first_screening_included IN ('yes','no','conflict') OR first_screening_included IS NULL), first_screening_notes TEXT, second_screening_included TEXT CHECK(second_screening_included IN ('yes','no','conflict') OR second_screening_included IS NULL), second_screening_notes TEXT, exclusion_reason INTEGER, UNIQUE(id_review,doi), UNIQUE(id_review,title,authors,year));
CREATE TABLE IF NOT EXISTS first_screening (id_review INTEGER NOT NULL REFERENCES review(id) ON DELETE CASCADE, id_reviewer INTEGER NOT NULL REFERENCES reviewers(id) ON DELETE CASCADE, id_study INTEGER NOT NULL REFERENCES studies(id) ON DELETE CASCADE, decision TEXT NOT NULL CHECK(decision IN ('yes','no','maybe')));
CREATE TABLE IF NOT EXISTS first_screening_conflicts (id_review INTEGER NOT NULL REFERENCES review(id) ON DELETE CASCADE, id_reviewer INTEGER NOT NULL REFERENCES reviewers(id) ON DELETE CASCADE, id_study INTEGER NOT NULL REFERENCES studies(id) ON DELETE CASCADE, decision TEXT NOT NULL CHECK(decision IN ('yes','no','maybe')), UNIQUE(id_review,id_reviewer,id_study));
CREATE TABLE IF NOT EXISTS exclusion_reasons (id INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY, id_review INTEGER NOT NULL REFERENCES review(id) ON DELETE CASCADE, hierarchy INTEGER NOT NULL, reason TEXT NOT NULL, is_active INTEGER NOT NULL DEFAULT 1);
CREATE UNIQUE INDEX IF NOT EXISTS idx_exclusion_reasons_active_hierarchy_unique ON exclusion_reasons(id_review,hierarchy) WHERE is_active=1;
CREATE TABLE IF NOT EXISTS second_screening (id_review INTEGER NOT NULL REFERENCES review(id) ON DELETE CASCADE, id_reviewer INTEGER NOT NULL REFERENCES reviewers(id) ON DELETE CASCADE, id_study INTEGER NOT NULL REFERENCES studies(id) ON DELETE CASCADE, decision TEXT NOT NULL CHECK(decision IN ('yes','no')), reason INTEGER REFERENCES exclusion_reasons(id));
CREATE TABLE IF NOT EXISTS second_screening_conflicts (id_review INTEGER NOT NULL REFERENCES review(id) ON DELETE CASCADE, id_reviewer INTEGER NOT NULL REFERENCES reviewers(id) ON DELETE CASCADE, id_study INTEGER NOT NULL REFERENCES studies(id) ON DELETE CASCADE, decision TEXT NOT NULL CHECK(decision IN ('yes','no')), reason INTEGER REFERENCES exclusion_reasons(id), UNIQUE(id_review,id_reviewer,id_study));
CREATE INDEX IF NOT EXISTS idx_studies_review ON studies(id_review);
CREATE INDEX IF NOT EXISTS idx_first_screening_study ON first_screening(id_review,id_study);
CREATE INDEX IF NOT EXISTS idx_second_screening_study ON second_screening(id_review,id_study);
"""


def init_db(app):
    dsn = _database_url(app)
    if dsn.startswith("sqlite:///"):
        path = _sqlite_path(dsn, app.root_path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(path)
        connection.executescript(SQLITE_SCHEMA)
        connection.close()
    elif dsn:
        import psycopg

        with psycopg.connect(dsn) as connection:
            for statement in POSTGRES_SCHEMA.split(";"):
                if statement.strip():
                    connection.execute(statement)
            connection.commit()


def seed_demo(app):
    """Seed a fictional review so the first page is useful immediately."""
    if not app.config.get("DEMO_MODE"):
        return
    with app.app_context():
        db = get_db()
        if db.execute("SELECT COUNT(*) AS c FROM review").fetchone()["c"]:
            return
        review_id = db.execute(
            "INSERT INTO review (review_name,participants_number,participants_name,two_reviewer_consensus,password) VALUES (%s,%s,%s,%s,%s) RETURNING id",
            ("Urban green spaces and wellbeing", 2, "Alex Morgan; Sam Rivera", "yes", "demo"),
        ).fetchone()["id"]
        reviewer_ids = [
            db.execute("INSERT INTO reviewers (id_review,reviewer_name) VALUES (%s,%s) RETURNING id", (review_id, name)).fetchone()["id"]
            for name in ("Alex Morgan", "Sam Rivera")
        ]
        reason_ids = [
            db.execute("INSERT INTO exclusion_reasons (id_review,hierarchy,reason) VALUES (%s,%s,%s) RETURNING id", (review_id, n, reason)).fetchone()["id"]
            for n, reason in ((1, "Wrong population"), (2, "Wrong intervention"), (3, "No relevant outcome"))
        ]
        rows = [
            ("10.1000/demo.001", "Urban parks and adult wellbeing", "Taylor et al.", 2023, "A longitudinal study of park access and wellbeing.", "yes", "yes", None),
            ("10.1000/demo.002", "Green corridors and community health", "Lee and Silva", 2022, "Mixed-method evidence from three European cities.", "yes", "no", reason_ids[2]),
            ("10.1000/demo.003", "Nature exposure: a systematic review", "Okafor et al.", 2021, "A synthesis of nature exposure interventions.", "yes", None, None),
            ("10.1000/demo.004", "Playgrounds and childhood activity", "García et al.", 2020, "Physical activity outcomes after playground renovations.", "conflict", None, None),
            ("10.1000/demo.005", "Rural forests and biodiversity", "Nielsen", 2019, "Biodiversity outcomes in managed rural forests.", "no", None, None),
            ("10.1000/demo.006", "Pocket parks in dense neighbourhoods", "Chen et al.", 2024, "A quasi-experimental evaluation of pocket parks.", None, None, None),
        ]
        study_ids = [
            db.execute(
                "INSERT INTO studies (id_review,document_type,doi,title,authors,year,abstract,source_title,first_screening_included,second_screening_included,exclusion_reason) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                (review_id, "Article", doi, title, authors, year, abstract, "Demo Research Journal", first, second, reason),
            ).fetchone()["id"]
            for doi, title, authors, year, abstract, first, second, reason in rows
        ]
        for reviewer, decision in zip(reviewer_ids, ("yes", "no")):
            db.execute("INSERT INTO first_screening (id_review,id_reviewer,id_study,decision) VALUES (%s,%s,%s,%s)", (review_id, reviewer, study_ids[3], decision))
            db.execute("INSERT INTO first_screening_conflicts (id_review,id_reviewer,id_study,decision) VALUES (%s,%s,%s,%s)", (review_id, reviewer, study_ids[3], decision))
        db.commit()


def reset_demo(app):
    """Clear disposable demo content and restore the original fixture."""
    if not app.config.get("DEMO_MODE"):
        raise RuntimeError("Demo reset is disabled.")
    with app.app_context():
        db = get_db()
        for table in (
            "second_screening_conflicts", "second_screening",
            "first_screening_conflicts", "first_screening",
            "studies", "exclusion_reasons", "reviewers", "review",
        ):
            db.execute(f"DELETE FROM {table}")
        db.commit()
    seed_demo(app)


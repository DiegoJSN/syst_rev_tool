from __future__ import annotations

import json
import os
import re
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


DEMO_REVIEW_NAME = "Example 1: Degrowth in agricultural systems"
DEMO_PARTICIPANTS = (
    "Alex Morgan",
    "Sam Rivera",
    "Priya Shah",
    "Daniel Kim",
    "Lucía Torres",
    "Jordan Blake",
)

# Records with complete exported metadata are used in the two interactive
# screening queues. Studies with an exported exclusion reason remain visible
# in the second-screening exclusions view.
FIRST_SCREENING_IDS = {97, 98, 99, 104, 112, 113, 116}
SECOND_SCREENING_IDS = {121, 126, 128, 129, 130, 143, 165}
EXTRACTION_IDS = {6, 7, 9, 10, 168, 190}
EXCLUDED_IDS = {
    102, 106, 117, 118, 119, 120, 131, 134, 147,
    151, 153, 154, 155, 161, 166, 169, 175, 177,
}
EXPECTED_EXAMPLE_IDS = (
    FIRST_SCREENING_IDS
    | SECOND_SCREENING_IDS
    | EXTRACTION_IDS
    | EXCLUDED_IDS
)


def _clear_demo_tables(db):
    for table in (
        "second_screening_conflicts", "second_screening",
        "first_screening_conflicts", "first_screening",
        "studies", "exclusion_reasons", "reviewers", "review",
    ):
        db.execute(f"DELETE FROM {table}")
    if isinstance(db, SQLiteConnection):
        db.execute(
            "DELETE FROM sqlite_sequence WHERE name IN "
            "('review','reviewers','studies','exclusion_reasons')"
        )


def _example_pdf_metadata(filename: str):
    label = Path(filename).stem.split("_", 1)[1]
    match = re.match(
        r"^(?P<authors>.+?)\s+(?P<year>(?:19|20)\d{2})\s+-\s+(?P<title>.+)$",
        label,
    )
    if match:
        return (
            match.group("authors"),
            int(match.group("year")),
            match.group("title"),
        )
    return ("Metadata unavailable in source export", None, label.replace("-", " "))


def _numbered_example_pdfs(app):
    pdf_directory = Path(app.root_path) / "example_pdfs"
    pdfs = {}
    if pdf_directory.is_dir():
        for pdf_path in pdf_directory.glob("*.pdf"):
            prefix = pdf_path.name.split("_", 1)[0]
            if prefix.isdigit():
                pdfs[int(prefix)] = pdf_path

    missing = sorted(EXPECTED_EXAMPLE_IDS - set(pdfs))
    if missing:
        raise RuntimeError(
            "The portfolio demo is missing example PDFs for study IDs: "
            + ", ".join(str(study_id) for study_id in missing)
        )
    return pdfs


def _load_demo_fixture(app):
    fixture_directory = Path(app.root_path) / "example_data"
    with (fixture_directory / "studies.json").open(encoding="utf-8") as handle:
        study_payload = json.load(handle)
    with (fixture_directory / "exclusion_reasons.json").open(encoding="utf-8") as handle:
        reason_payload = json.load(handle)

    studies = {
        int(item["study_id"]): item
        for item in study_payload["studies"]
    }
    reasons = [
        item
        for item in reason_payload["exclusion_reasons"]
        if item.get("is_active", True)
    ]
    return studies, reasons


def seed_demo(app):
    """Seed a collaborative review backed by exported metadata and included PDFs."""
    if not app.config.get("DEMO_MODE"):
        return

    with app.app_context():
        db = get_db()
        existing_reviews = db.execute(
            "SELECT id, review_name FROM review ORDER BY id"
        ).fetchall()
        if existing_reviews:
            replace_old_fixture = False
            if len(existing_reviews) == 1:
                existing_review = existing_reviews[0]
                study_summary = db.execute(
                    """
                    SELECT COUNT(*) AS total,
                           SUM(CASE WHEN source_title = %s THEN 1 ELSE 0 END) AS generic_sources
                    FROM studies
                    WHERE id_review = %s
                    """,
                    ("Included example PDF collection", existing_review["id"]),
                ).fetchone()
                replace_old_fixture = (
                    (
                        existing_review["review_name"] == "Urban green spaces and wellbeing"
                        and study_summary["total"] == 6
                    )
                    or (
                        existing_review["review_name"] == DEMO_REVIEW_NAME
                        and study_summary["total"] == len(EXPECTED_EXAMPLE_IDS)
                        and study_summary["generic_sources"] == study_summary["total"]
                    )
                )

            if replace_old_fixture:
                _clear_demo_tables(db)
            else:
                return

        pdfs = _numbered_example_pdfs(app)
        fixture_studies, fixture_reasons = _load_demo_fixture(app)

        resolved_first = len(SECOND_SCREENING_IDS | EXTRACTION_IDS | EXCLUDED_IDS)
        first_progress = int((resolved_first * 100) / len(EXPECTED_EXAMPLE_IDS))
        second_total = resolved_first
        resolved_second = len(EXTRACTION_IDS | EXCLUDED_IDS)
        second_progress = int((resolved_second * 100) / second_total)

        review_id = db.execute(
            """
            INSERT INTO review (
                review_name, participants_number, participants_name,
                first_screening_progress, second_screening_progress,
                two_reviewer_consensus, password
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s)
            RETURNING id
            """,
            (
                DEMO_REVIEW_NAME,
                len(DEMO_PARTICIPANTS),
                "; ".join(DEMO_PARTICIPANTS),
                first_progress,
                second_progress,
                "yes",
                "demo",
            ),
        ).fetchone()["id"]

        reviewer_ids = [
            db.execute(
                "INSERT INTO reviewers (id_review,reviewer_name) VALUES (%s,%s) RETURNING id",
                (review_id, name),
            ).fetchone()["id"]
            for name in DEMO_PARTICIPANTS
        ]

        reason_ids = {}
        for item in sorted(fixture_reasons, key=lambda value: value["hierarchy"]):
            reason_ids[int(item["hierarchy"])] = db.execute(
                """
                INSERT INTO exclusion_reasons (id_review,hierarchy,reason,is_active)
                VALUES (%s,%s,%s,%s)
                RETURNING id
                """,
                (
                    review_id,
                    int(item["hierarchy"]),
                    item["reason"],
                    1,
                ),
            ).fetchone()["id"]

        excluded_reason_by_study = {}
        for study_id in sorted(EXPECTED_EXAMPLE_IDS):
            pdf_path = pdfs[study_id]
            metadata = fixture_studies.get(study_id)
            if metadata:
                doi = metadata.get("doi")
                title = metadata.get("title")
                authors = metadata.get("authors")
                year = metadata.get("year")
                abstract = metadata.get("abstract")
                source_title = metadata.get("journal")
                reason_hierarchy = metadata.get("exclusion_reason_hierarchy")
            else:
                authors, year, title = _example_pdf_metadata(pdf_path.name)
                doi = None
                abstract = (
                    "This included PDF is retained as a full-text extraction example. "
                    "Its metadata was not present in the supplied study export."
                )
                source_title = "Included example PDF"
                reason_hierarchy = None

            if study_id in FIRST_SCREENING_IDS:
                first_decision = None
                second_decision = None
                exclusion_reason = None
            elif study_id in SECOND_SCREENING_IDS:
                first_decision = "yes"
                second_decision = None
                exclusion_reason = None
            elif study_id in EXTRACTION_IDS:
                first_decision = "yes"
                second_decision = "yes"
                exclusion_reason = None
            else:
                first_decision = "yes"
                second_decision = "no"
                exclusion_reason = reason_ids[int(reason_hierarchy)]
                excluded_reason_by_study[study_id] = exclusion_reason

            db.execute(
                """
                INSERT INTO studies (
                    id, id_review, document_type, doi, title, authors, year,
                    abstract, source_title, file_name, file_data,
                    first_screening_included, second_screening_included,
                    exclusion_reason
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    study_id,
                    review_id,
                    "Article",
                    doi,
                    title,
                    authors,
                    year,
                    abstract,
                    source_title,
                    pdf_path.name,
                    pdf_path.read_bytes(),
                    first_decision,
                    second_decision,
                    exclusion_reason,
                ),
            )

        first_contributions = [0] * len(reviewer_ids)
        completed_first_ids = SECOND_SCREENING_IDS | EXTRACTION_IDS | EXCLUDED_IDS
        for position, study_id in enumerate(sorted(completed_first_ids)):
            for reviewer_position in (
                position % len(reviewer_ids),
                (position + 1) % len(reviewer_ids),
            ):
                db.execute(
                    """
                    INSERT INTO first_screening (id_review,id_reviewer,id_study,decision)
                    VALUES (%s,%s,%s,%s)
                    """,
                    (review_id, reviewer_ids[reviewer_position], study_id, "yes"),
                )
                first_contributions[reviewer_position] += 1

        second_contributions = [0] * len(reviewer_ids)
        completed_second_ids = EXTRACTION_IDS | EXCLUDED_IDS
        for position, study_id in enumerate(sorted(completed_second_ids)):
            decision = "no" if study_id in EXCLUDED_IDS else "yes"
            reason = excluded_reason_by_study.get(study_id)
            for reviewer_position in (
                position % len(reviewer_ids),
                (position + 1) % len(reviewer_ids),
            ):
                db.execute(
                    """
                    INSERT INTO second_screening (
                        id_review,id_reviewer,id_study,decision,reason
                    )
                    VALUES (%s,%s,%s,%s,%s)
                    """,
                    (
                        review_id,
                        reviewer_ids[reviewer_position],
                        study_id,
                        decision,
                        reason,
                    ),
                )
                second_contributions[reviewer_position] += 1

        for position, reviewer_id in enumerate(reviewer_ids):
            db.execute(
                """
                UPDATE reviewers
                SET first_screening_contribution = %s,
                    second_screening_contribution = %s
                WHERE id = %s
                """,
                (
                    first_contributions[position],
                    second_contributions[position],
                    reviewer_id,
                ),
            )

        if not _database_url(app).startswith("sqlite:///"):
            db.execute(
                "SELECT setval(pg_get_serial_sequence('studies','id'), "
                "(SELECT MAX(id) FROM studies))"
            )
        db.commit()


def reset_demo(app):
    """Clear disposable demo content and restore the original fixture."""
    if not app.config.get("DEMO_MODE"):
        raise RuntimeError("Demo reset is disabled.")
    with app.app_context():
        db = get_db()
        _clear_demo_tables(db)
        db.commit()
    seed_demo(app)

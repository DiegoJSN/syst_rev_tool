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
CREATE TABLE IF NOT EXISTS screening_events (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 id_review INTEGER NOT NULL,
 id_study INTEGER NOT NULL,
 id_reviewer INTEGER,
 phase TEXT NOT NULL CHECK(phase IN ('first','second')),
 event_type TEXT NOT NULL CHECK(event_type IN ('decision','conflict','resolution')),
 decision TEXT,
 reason INTEGER,
 note TEXT,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(id_review) REFERENCES review(id) ON DELETE CASCADE,
 FOREIGN KEY(id_study) REFERENCES studies(id) ON DELETE CASCADE,
 FOREIGN KEY(id_reviewer) REFERENCES reviewers(id) ON DELETE SET NULL,
 FOREIGN KEY(reason) REFERENCES exclusion_reasons(id));
DELETE FROM first_screening
 WHERE rowid NOT IN (
   SELECT MIN(rowid) FROM first_screening
   GROUP BY id_review,id_reviewer,id_study
 );
DELETE FROM second_screening
 WHERE rowid NOT IN (
   SELECT MIN(rowid) FROM second_screening
   GROUP BY id_review,id_reviewer,id_study
 );
CREATE UNIQUE INDEX IF NOT EXISTS idx_first_screening_reviewer_study
 ON first_screening(id_review,id_reviewer,id_study);
CREATE UNIQUE INDEX IF NOT EXISTS idx_second_screening_reviewer_study
 ON second_screening(id_review,id_reviewer,id_study);
CREATE INDEX IF NOT EXISTS idx_screening_events_review_study
 ON screening_events(id_review,id_study,phase);
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
CREATE TABLE IF NOT EXISTS screening_events (id INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY, id_review INTEGER NOT NULL REFERENCES review(id) ON DELETE CASCADE, id_study INTEGER NOT NULL REFERENCES studies(id) ON DELETE CASCADE, id_reviewer INTEGER REFERENCES reviewers(id) ON DELETE SET NULL, phase TEXT NOT NULL CHECK(phase IN ('first','second')), event_type TEXT NOT NULL CHECK(event_type IN ('decision','conflict','resolution')), decision TEXT, reason INTEGER REFERENCES exclusion_reasons(id), note TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE UNIQUE INDEX IF NOT EXISTS idx_first_screening_reviewer_study ON first_screening(id_review,id_reviewer,id_study);
CREATE UNIQUE INDEX IF NOT EXISTS idx_second_screening_reviewer_study ON second_screening(id_review,id_reviewer,id_study);
CREATE INDEX IF NOT EXISTS idx_screening_events_review_study ON screening_events(id_review,id_study,phase);
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

# These four PDFs predate the exported study spreadsheet. They remain useful
# as full-text extraction examples, but are never shown without their PDF.
PDF_ONLY_EXTRACTION_IDS = {6, 7, 9, 10}
EXPORTED_EXTRACTION_IDS = {168, 190}
EXTRACTION_IDS = PDF_ONLY_EXTRACTION_IDS | EXPORTED_EXTRACTION_IDS

PDF_ONLY_STUDY_METADATA = {
    6: {
        "title": "Degrowth as a plausible pathway for food systems transformation",
        "authors": (
            "Matthew Gibson; Costanza Conti; Daniel Mason-D’Croz; Anna Norberg; "
            "Maria Boa Alvarado; Mario Herrero"
        ),
        "year": 2025,
        "doi": "10.1038/s43016-024-01108-5",
        "journal": "NATURE FOOD",
        "abstract": (
            "Food systems require urgent transformation towards social and ecological "
            "sustainability. Degrowth posits a radical pathway of transformation to "
            "reduce ecological impacts while increasing well-being and reducing "
            "inequality. Here we highlight that degrowth and food systems—albeit both "
            "linked to transformation—are not well integrated. We conduct a conceptual "
            "exploration of the potential alignment between key food systems and "
            "degrowth transformation measures, arguing for complementary and reciprocal "
            "perspectives to theorize and enact transformation. Finally, we offer "
            "concrete practical actions to integrate degrowth and food systems, thereby "
            "widening the narrative and analytical lens of social–ecological transformation."
        ),
    },
    7: {
        "title": "Sustainable agrifood systems for a post-growth world",
        "authors": (
            "Steven R. McGreevy; Christoph D. D. Rupprecht; Daniel Niles; Arnim Wiek; "
            "Michael Carolan; Giorgos Kallis; Petr Jehlička; Kanang Kantamaturapoj; "
            "Astrid Mangnus; Oliver Taherzadeh; Marlyne Sahakian; Ilan Chabay; "
            "Jose-Luis Vivero-Pol; Rajat Chaudhuri; Ashley Colby; Maximilian Spiegelberg; "
            "Mai Kobayashi; Bálint Balázs; Kazuaki Tsuchiya; Motoki Akitsu; Hein Mallee; "
            "Clara Nicholls; Keiko Tanaka; Joost Vervoort; Kazuhiko Ota; Rika Shinkai; "
            "Ashlesha Khadse; Norie Tamura; Ken-ichi Abe; Miguel Altieri; Yo-Ichiro Sato; "
            "Masashi Tachikawa"
        ),
        "year": 2022,
        "doi": "10.1038/s41893-022-00933-5",
        "journal": "NATURE SUSTAINABILITY",
        "abstract": (
            "Sustainable agrifood systems are critical to averting climate-driven social "
            "and ecological disasters, overcoming the growth paradigm and redefining the "
            "interactions of humanity and nature in the twenty-first century. This "
            "Perspective describes an agenda and examples for comprehensive agrifood "
            "system redesign according to principles of sufficiency, regeneration, "
            "distribution, commons and care. This redesign should be supported by "
            "coordinated education and research efforts that do not simply replicate "
            "dominant discourses on food system sustainability but point towards a "
            "post-growth world in which agroecological life processes support healthy "
            "communities rather than serving as inputs for the relentless pursuit of "
            "economic growth."
        ),
    },
    9: {
        "title": "Evaluation of Local Food Systems Based on De-growth",
        "authors": "Judit Dombi; Zoltán Elekes",
        "year": 2014,
        "doi": None,
        "journal": "CERS",
        "abstract": (
            "In this paper we argue that the purpose of local economic development "
            "formulated on the basis of de-growth differs from the conventional "
            "competitiveness-based approach significantly and meaningfully. Local food "
            "systems are often considered alternative local economic development "
            "initiatives and are prime candidates as means to the ends of local economic "
            "development based on de-growth. In this initial step of research we attempt "
            "to differentiate de-growth oriented local economic development from the "
            "conventional competitiveness oriented approach."
        ),
    },
    10: {
        "title": (
            "Integrating degrowth and efficiency perspectives enables an "
            "emission-neutral food system by 2100"
        ),
        "authors": (
            "Benjamin Leon Bodirsky; David Meng-Chuen Chen; Isabelle Weindl; "
            "Felicitas Beier; Edna J. Molina Bacca; Franziska Gaupp; Alexander Popp; "
            "Bjoern Soergel; Hermann Lotze-Campen"
        ),
        "year": 2022,
        "doi": "10.1038/s43016-022-00500-3",
        "journal": "NATURE FOOD",
        "abstract": (
            "Degrowth proponents advocate reducing ecologically destructive forms of "
            "production and resource throughput in wealthy economies to achieve "
            "environmental goals, while transforming production to focus on human "
            "well-being. Here we present a quantitative model to test degrowth principles "
            "in the food and land system. Our results confirm that reducing and "
            "redistributing income alone, within current development paradigms, leads to "
            "limited greenhouse gas (GHG) emission mitigation from agriculture and "
            "land-use change, as the nutrition transition towards unsustainable diets "
            "already occurs at relatively low income levels. Instead, we show that a "
            "structural, qualitative food system transformation can achieve a steady-state "
            "food system economy that is net GHG-neutral by 2100 while improving "
            "nutritional outcomes. This sustainable transformation reduces material "
            "throughput via a convergence towards a needs-based food system, is enabled "
            "by a more equitable income distribution and includes efficient resource "
            "allocation through the pricing of GHG emissions as a complementary strategy. "
            "It thereby integrates degrowth and efficiency perspectives."
        ),
    },
}


def _clear_demo_tables(db):
    for table in (
        "screening_events",
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

    missing = sorted(EXTRACTION_IDS - set(pdfs))
    if missing:
        raise RuntimeError(
            "The portfolio demo is missing extraction PDFs for study IDs: "
            + ", ".join(str(study_id) for study_id in missing)
        )
    return pdfs


def _load_demo_fixture(app):
    fixture_directory = Path(app.root_path) / "example_data"
    with (fixture_directory / "studies.json").open(encoding="utf-8") as handle:
        study_manifest = json.load(handle)
    with (fixture_directory / "exclusion_reasons.json").open(encoding="utf-8") as handle:
        reason_payload = json.load(handle)

    studies = {}
    for part_name in study_manifest["parts"]:
        with (fixture_directory / part_name).open(encoding="utf-8") as handle:
            part_payload = json.load(handle)
        for item in part_payload["studies"]:
            study_id = int(item["study_id"])
            if study_id in studies:
                raise RuntimeError(f"Duplicate study ID in demo fixture: {study_id}")
            studies[study_id] = item

    if len(studies) != int(study_manifest["row_count"]):
        raise RuntimeError(
            "The portfolio demo study fixture is incomplete: "
            f"expected {study_manifest['row_count']}, found {len(studies)}"
        )

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
                study_total = db.execute(
                    "SELECT COUNT(*) AS total FROM studies WHERE id_review = %s",
                    (existing_review["id"],),
                ).fetchone()["total"]
                legacy_pdf_metadata = False
                if (
                    existing_review["review_name"] == DEMO_REVIEW_NAME
                    and study_total == 258
                ):
                    study_six = db.execute(
                        "SELECT doi FROM studies WHERE id_review = %s AND id = 6",
                        (existing_review["id"],),
                    ).fetchone()
                    legacy_pdf_metadata = (
                        not study_six
                        or study_six["doi"] != "10.1038/s43016-024-01108-5"
                    )

                replace_old_fixture = (
                    (
                        existing_review["review_name"] == "Urban green spaces and wellbeing"
                        and study_total == 6
                    )
                    or (
                        existing_review["review_name"] == DEMO_REVIEW_NAME
                        and study_total == 38
                    )
                    or legacy_pdf_metadata
                )

            if replace_old_fixture:
                _clear_demo_tables(db)
            else:
                return

        pdfs = _numbered_example_pdfs(app)
        fixture_studies, fixture_reasons = _load_demo_fixture(app)
        fixture_ids = set(fixture_studies)
        pdf_ids = set(pdfs)
        all_study_ids = fixture_ids | PDF_ONLY_EXTRACTION_IDS

        exported_with_pdf_ids = fixture_ids & pdf_ids
        second_excluded_ids = {
            study_id
            for study_id in exported_with_pdf_ids
            if fixture_studies[study_id].get("exclusion_reason_hierarchy")
        }
        second_pending_ids = (
            exported_with_pdf_ids
            - second_excluded_ids
            - EXPORTED_EXTRACTION_IDS
        )
        first_rejected_ids = {
            study_id
            for study_id in fixture_ids - pdf_ids
            if fixture_studies[study_id].get("exclusion_reason_hierarchy")
        }
        first_pending_ids = (
            fixture_ids
            - pdf_ids
            - first_rejected_ids
        )
        first_conflict_ids = sorted(first_pending_ids)[:2]
        second_conflict_ids = sorted(second_pending_ids)[:2]
        if len(first_conflict_ids) != 2 or len(second_conflict_ids) != 2:
            raise RuntimeError("The portfolio fixture needs two conflicts per screening phase.")

        first_conflict_notes = {
            first_conflict_ids[0]: (
                "Alex Morgan : The title explicitly links degrowth with agricultural systems.;$] "
                "Sam Rivera : The abstract does not clearly describe an agricultural intervention.;$] "
            ),
            first_conflict_ids[1]: (
                "Priya Shah : Relevant food-system transformation study; keep for full-text review.;$] "
                "Daniel Kim : Population and outcomes appear outside the review protocol.;$] "
            ),
        }
        second_conflict_notes = {
            second_conflict_ids[0]: (
                "Alex Morgan : The full text applies degrowth to an agrifood-system question.;$] "
                "Sam Rivera : The agricultural connection may be too indirect for the protocol.;$] "
            ),
            second_conflict_ids[1]: (
                "Priya Shah : The paper uses an explicit post-growth or degrowth framing.;$] "
                "Daniel Kim : Degrowth is mentioned but may not be the analytical framework.;$] "
            ),
        }

        # Second screening is intentionally PDF-only.
        if any(study_id not in pdf_ids for study_id in second_pending_ids):
            raise RuntimeError("A second-screening demo study is missing its PDF.")

        resolved_first = (
            len(first_rejected_ids)
            + len(second_pending_ids)
            + len(EXTRACTION_IDS)
            + len(second_excluded_ids)
        )
        first_progress = int((resolved_first * 100) / len(all_study_ids))
        second_total = len(second_pending_ids | EXTRACTION_IDS | second_excluded_ids)
        resolved_second = len(EXTRACTION_IDS | second_excluded_ids)
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
        reason_text_by_hierarchy = {}
        for item in sorted(fixture_reasons, key=lambda value: value["hierarchy"]):
            hierarchy = int(item["hierarchy"])
            reason_text_by_hierarchy[hierarchy] = item["reason"]
            reason_ids[hierarchy] = db.execute(
                """
                INSERT INTO exclusion_reasons (id_review,hierarchy,reason,is_active)
                VALUES (%s,%s,%s,%s)
                RETURNING id
                """,
                (review_id, hierarchy, item["reason"], 1),
            ).fetchone()["id"]

        excluded_reason_by_study = {}
        for study_id in sorted(all_study_ids):
            metadata = (
                fixture_studies.get(study_id)
                or PDF_ONLY_STUDY_METADATA.get(study_id)
            )
            if metadata:
                doi = metadata.get("doi")
                title = metadata.get("title")
                authors = metadata.get("authors")
                year = metadata.get("year")
                abstract = metadata.get("abstract")
                source_title = metadata.get("journal")
                reason_hierarchy = metadata.get("exclusion_reason_hierarchy")
            else:
                authors, year, title = _example_pdf_metadata(pdfs[study_id].name)
                doi = None
                abstract = (
                    "This included PDF is retained as a full-text extraction example. "
                    "Its metadata was not present in the supplied study export."
                )
                source_title = "Included example PDF"
                reason_hierarchy = None

            pdf_path = pdfs.get(study_id)
            file_name = pdf_path.name if pdf_path else None
            file_data = pdf_path.read_bytes() if pdf_path else None
            first_notes = None
            second_notes = None

            if study_id in first_conflict_ids:
                first_decision = "conflict"
                second_decision = None
                exclusion_reason = None
                first_notes = first_conflict_notes[study_id]
            elif study_id in first_pending_ids:
                first_decision = None
                second_decision = None
                exclusion_reason = None
            elif study_id in first_rejected_ids:
                first_decision = "no"
                second_decision = None
                exclusion_reason = None
                first_notes = (
                    "Demo exclusion: "
                    + reason_text_by_hierarchy[int(reason_hierarchy)]
                )
            elif study_id in second_conflict_ids:
                first_decision = "yes"
                second_decision = "conflict"
                exclusion_reason = None
                second_notes = second_conflict_notes[study_id]
            elif study_id in second_pending_ids:
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
                    first_screening_included, first_screening_notes,
                    second_screening_included, second_screening_notes,
                    exclusion_reason
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
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
                    file_name,
                    file_data,
                    first_decision,
                    first_notes,
                    second_decision,
                    second_notes,
                    exclusion_reason,
                ),
            )

        first_contributions = [0] * len(reviewer_ids)
        completed_first_ids = all_study_ids - first_pending_ids
        for position, study_id in enumerate(sorted(completed_first_ids)):
            decision = "no" if study_id in first_rejected_ids else "yes"
            for reviewer_position in (
                position % len(reviewer_ids),
                (position + 1) % len(reviewer_ids),
            ):
                db.execute(
                    """
                    INSERT INTO first_screening (id_review,id_reviewer,id_study,decision)
                    VALUES (%s,%s,%s,%s)
                    """,
                    (review_id, reviewer_ids[reviewer_position], study_id, decision),
                )
                first_contributions[reviewer_position] += 1

        first_conflict_reviewers = ((0, 1), (2, 3))
        for position, study_id in enumerate(first_conflict_ids):
            reviewer_pair = first_conflict_reviewers[position]
            for reviewer_position, decision in zip(reviewer_pair, ("yes", "no")):
                reviewer_id = reviewer_ids[reviewer_position]
                db.execute(
                    """
                    INSERT INTO first_screening (
                        id_review,id_reviewer,id_study,decision
                    ) VALUES (%s,%s,%s,%s)
                    """,
                    (review_id, reviewer_id, study_id, decision),
                )
                db.execute(
                    """
                    INSERT INTO first_screening_conflicts (
                        id_review,id_reviewer,id_study,decision
                    ) VALUES (%s,%s,%s,%s)
                    """,
                    (review_id, reviewer_id, study_id, decision),
                )
                db.execute(
                    """
                    INSERT INTO screening_events (
                        id_review,id_study,id_reviewer,phase,event_type,decision,note
                    ) VALUES (%s,%s,%s,'first','decision',%s,%s)
                    """,
                    (
                        review_id,
                        study_id,
                        reviewer_id,
                        decision,
                        first_conflict_notes[study_id],
                    ),
                )
                first_contributions[reviewer_position] += 1
            db.execute(
                """
                INSERT INTO screening_events (
                    id_review,id_study,phase,event_type,decision,note
                ) VALUES (%s,%s,'first','conflict','conflict',%s)
                """,
                (review_id, study_id, first_conflict_notes[study_id]),
            )

        second_contributions = [0] * len(reviewer_ids)
        completed_second_ids = EXTRACTION_IDS | second_excluded_ids
        for position, study_id in enumerate(sorted(completed_second_ids)):
            decision = "no" if study_id in second_excluded_ids else "yes"
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

        second_conflict_reviewers = ((0, 1), (2, 3))
        second_conflict_reason_hierarchies = (3, 4)
        for position, study_id in enumerate(second_conflict_ids):
            reviewer_pair = second_conflict_reviewers[position]
            reason_id = reason_ids[second_conflict_reason_hierarchies[position]]
            for reviewer_position, decision in zip(reviewer_pair, ("yes", "no")):
                reviewer_id = reviewer_ids[reviewer_position]
                decision_reason = reason_id if decision == "no" else None
                db.execute(
                    """
                    INSERT INTO second_screening (
                        id_review,id_reviewer,id_study,decision,reason
                    ) VALUES (%s,%s,%s,%s,%s)
                    """,
                    (
                        review_id,
                        reviewer_id,
                        study_id,
                        decision,
                        decision_reason,
                    ),
                )
                db.execute(
                    """
                    INSERT INTO second_screening_conflicts (
                        id_review,id_reviewer,id_study,decision,reason
                    ) VALUES (%s,%s,%s,%s,%s)
                    """,
                    (
                        review_id,
                        reviewer_id,
                        study_id,
                        decision,
                        decision_reason,
                    ),
                )
                db.execute(
                    """
                    INSERT INTO screening_events (
                        id_review,id_study,id_reviewer,phase,event_type,
                        decision,reason,note
                    ) VALUES (%s,%s,%s,'second','decision',%s,%s,%s)
                    """,
                    (
                        review_id,
                        study_id,
                        reviewer_id,
                        decision,
                        decision_reason,
                        second_conflict_notes[study_id],
                    ),
                )
                second_contributions[reviewer_position] += 1
            db.execute(
                """
                INSERT INTO screening_events (
                    id_review,id_study,phase,event_type,decision,reason,note
                ) VALUES (%s,%s,'second','conflict','conflict',%s,%s)
                """,
                (
                    review_id,
                    study_id,
                    reason_id,
                    second_conflict_notes[study_id],
                ),
            )

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

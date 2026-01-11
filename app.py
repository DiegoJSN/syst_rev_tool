from dotenv import load_dotenv
load_dotenv()  # carga .env automáticamente desde la carpeta actual. Asi te evitas escribir en la terminal lo de "DATABASE_URL=f"postgresql://review_user:[PASSWORD]@[IP]:5432/systrev_db"

import os
import csv
import math
import random
from io import BytesIO
from typing import Optional, Tuple, List

from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, session, send_file, abort
)

from openpyxl import Workbook

# Web of Science .xls reader
from python_calamine import CalamineWorkbook

from db import init_db, get_db, close_db


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    app.config["DATABASE_URL"] = os.environ.get("DATABASE_URL")
    app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50MB

    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(os.path.join(app.root_path, "uploads"), exist_ok=True)

    # Initialize DB if missing
    init_db(app)

    app.teardown_appcontext(close_db)

    # ---------- helpers ----------

    def normalize_doi(value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        v = str(value).strip()
        if not v:
            return None
        v = v.replace("https://doi.org/", "").replace("http://doi.org/", "").strip()
        return v or None

    def doi_url(doi: Optional[str]) -> str:
        if not doi:
            return ""
        if doi.startswith("http://") or doi.startswith("https://"):
            return doi
        return f"https://doi.org/{doi}"

    app.jinja_env.globals["doi_url"] = doi_url

    def append_note(existing: Optional[str], reviewer_name: str, note: str) -> str:
        note = (note or "").strip()
        if not note:
            return existing or ""
        new_piece = f"{reviewer_name} : {note}"
        delimiter = ";$]"
        suffix = f"{delimiter} "
        if not existing:
            return f"{new_piece}{suffix}"
        parts = [p.strip() for p in existing.split(delimiter) if p.strip()]
        if new_piece in parts:
            return existing
        base_existing = existing
        if not base_existing.endswith(suffix):
            base_existing = base_existing.rstrip() + suffix
        return f"{base_existing}{new_piece}{suffix}"

    def parse_positive_int(value: Optional[str], default: int) -> int:
        if value and value.isdigit():
            parsed = int(value)
            if parsed > 0:
                return parsed
        return default

    def parse_pagination_args() -> Tuple[int, int, str]:
        allowed_per_page = {25, 50, 100}
        per_page = parse_positive_int(request.args.get("per_page"), 25)
        if per_page not in allowed_per_page:
            per_page = 25
        page = parse_positive_int(request.args.get("page"), 1)
        sort = request.args.get("sort", "random")
        if sort not in {"random", "id", "authors", "title"}:
            sort = "random"
        return per_page, page, sort

    def sort_clause(sort: str) -> str:
        if sort == "id":
            return "id ASC"
        if sort == "authors":
            return "CASE WHEN authors IS NULL OR authors = '' THEN 1 ELSE 0 END, lower(authors) ASC, id ASC"
        if sort == "title":
            return "CASE WHEN title IS NULL OR title = '' THEN 1 ELSE 0 END, lower(title) ASC, id ASC"
        return "RANDOM()"

    def clamp_page(page: int, total: int, per_page: int) -> Tuple[int, int]:
        total_pages = max(1, math.ceil(total / per_page)) if total else 1
        if page > total_pages:
            page = total_pages
        return page, total_pages

    def refresh_cached_metrics(review_id: int):
        db = get_db()

        # contributions
        db.execute(
            """
            UPDATE reviewers
            SET first_screening_contribution = (
                SELECT COUNT(*) FROM first_screening fs
                WHERE fs.id_review = %s AND fs.id_reviewer = reviewers.id
            )
            WHERE id_review = %s;
            """,
            (review_id, review_id),
        )
        db.execute(
            """
            UPDATE reviewers
            SET second_screening_contribution = (
                SELECT COUNT(*) FROM second_screening ss
                WHERE ss.id_review = %s AND ss.id_reviewer = reviewers.id
            )
            WHERE id_review = %s;
            """,
            (review_id, review_id),
        )

        total = db.execute(
            "SELECT COUNT(*) AS c FROM studies WHERE id_review = %s;",
            (review_id,),
        ).fetchone()["c"]
        resolved_first = db.execute(
            """
            SELECT COUNT(*) AS c FROM studies
            WHERE id_review = %s
              AND first_screening_included IS NOT NULL
              AND first_screening_included != 'conflict';
            """,
            (review_id,),
        ).fetchone()["c"]

        first_progress = int((resolved_first * 100) / total) if total else 0

        second_total = db.execute(
            "SELECT COUNT(*) AS c FROM studies WHERE id_review = %s AND first_screening_included = 'yes';",
            (review_id,),
        ).fetchone()["c"]
        resolved_second = db.execute(
            """
            SELECT COUNT(*) AS c FROM studies
            WHERE id_review = %s
              AND first_screening_included = 'yes'
              AND second_screening_included IS NOT NULL
              AND second_screening_included != 'conflict';
            """,
            (review_id,),
        ).fetchone()["c"]

        second_progress = int((resolved_second * 100) / second_total) if second_total else 0

        db.execute(
            "UPDATE review SET first_screening_progress = %s, second_screening_progress = %s WHERE id = %s;",
            (first_progress, second_progress, review_id),
        )
        db.commit()

    def require_login(review_id: int) -> Tuple[int, str]:
        login = session.get("login")
        if not login or login.get("review_id") != review_id:
            raise PermissionError("Please select your name (double verification) in the main page.")
        return int(login["reviewer_id"]), str(login["reviewer_name"])

    def split_participants(text: str) -> List[str]:
        if not text:
            return []
        t = text.replace(",", ";")
        out = []
        for chunk in t.split(";"):
            name = chunk.strip()
            if name and name not in out:
                out.append(name)
        return out

    def safe_filename(name: str) -> str:
        # minimal filename sanitizer
        keep = []
        for c in name:
            if c.isalnum() or c in ("-", "_", ".", " "):
                keep.append(c)
        cleaned = "".join(keep).strip()
        if not cleaned:
            cleaned = f"upload_{random.randint(1000, 9999)}"
        return cleaned

    def save_upload(file_storage) -> str:
        upload_dir = os.path.join(app.root_path, "uploads")
        os.makedirs(upload_dir, exist_ok=True)
        fname = safe_filename(file_storage.filename or "upload")
        path = os.path.join(upload_dir, fname)
        file_storage.save(path)
        return path

    def review_studies_dir(review_id: int) -> str:
        return os.path.join(app.root_path, "reviews", str(review_id), "studies")
    def pick_two_distinct_decisions_first(review_id: int, study_id: int):
        db = get_db()
        rows = db.execute(
            """
            SELECT fs.id_reviewer, fs.decision
            FROM first_screening fs
            WHERE fs.id_review = %s AND fs.id_study = %s;
            """,
            (review_id, study_id),
        ).fetchall()

        # Keep first decision per reviewer
        uniq = {}
        for r in rows:
            rid = r["id_reviewer"]
            if rid not in uniq:
                uniq[rid] = r["decision"]

        if len(uniq) < 2:
            return None

        reviewers = list(uniq.items())  # [(reviewer_id, decision)]
        return random.sample(reviewers, 2)


    def consolidate_first(review_id: int, study_id: int):
        db = get_db()
        pair = pick_two_distinct_decisions_first(review_id, study_id)
        if not pair:
            return

        for rid, dec in pair:
            db.execute(
                """
                INSERT INTO first_screening_conflicts (id_review, id_reviewer, id_study, decision)
                VALUES (%s, %s, %s, %s)
                    ON CONFLICT DO NOTHING;
                """,
                (review_id, rid, study_id, dec),
            )

        d1, d2 = pair[0][1], pair[1][1]
        outcome = None
        if d1 == d2 == "yes":
            outcome = "yes"
        elif d1 == d2 == "no":
            outcome = "no"
        elif d1 == d2 == "maybe":
            outcome = "yes"
        elif set([d1, d2]) == set(["yes", "maybe"]):
            outcome = "yes"
        elif set([d1, d2]) == set(["no", "maybe"]):
            outcome = "conflict"
        elif set([d1, d2]) == set(["yes", "no"]):
            outcome = "conflict"

        if outcome:
            db.execute(
                "UPDATE studies SET first_screening_included = %s WHERE id_review = %s AND id = %s;",
                (outcome, review_id, study_id),
            )
        db.commit()
    def pick_two_distinct_decisions_second(review_id: int, study_id: int):
        db = get_db()
        rows = db.execute(
            """
            SELECT ss.id_reviewer, ss.decision, ss.reason
            FROM second_screening ss
            WHERE ss.id_review = %s AND ss.id_study = %s;
            """,
            (review_id, study_id),
        ).fetchall()

        uniq = {}
        for r in rows:
            rid = r["id_reviewer"]
            if rid not in uniq:
                uniq[rid] = (r["decision"], r["reason"])

        if len(uniq) < 2:
            return None

        reviewers = list(uniq.items())  # [(reviewer_id, (decision, reason))]
        return random.sample(reviewers, 2)


    def consolidate_second(review_id: int, study_id: int):
        db = get_db()
        pair = pick_two_distinct_decisions_second(review_id, study_id)
        if not pair:
            return

        for rid, (dec, reason) in pair:
            db.execute(
                """
                INSERT INTO second_screening_conflicts (id_review, id_reviewer, id_study, decision, reason)
                VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING;
                """,
                (review_id, rid, study_id, dec, reason),
            )

        d1, r1 = pair[0][1]
        d2, r2 = pair[1][1]

        outcome = None
        exclusion_reason = None

        if d1 == d2 == "yes":
            outcome = "yes"
        elif d1 == d2 == "no":
            if r1 != r2:
                outcome = "conflict"
            else:
                outcome = "no"
                candidates = [r for r in [r1, r2] if r is not None]
                if candidates:
                    q = ",".join("%s" for _ in candidates)
                    rows = db.execute(
                        f"SELECT id, hierarchy FROM exclusion_reasons WHERE id IN ({q});",
                        tuple(candidates),
                    ).fetchall()
                    if rows:
                        exclusion_reason = sorted(rows, key=lambda x: x["hierarchy"])[0]["id"]
                    else:
                        exclusion_reason = candidates[0]
        elif set([d1, d2]) == set(["yes", "no"]):
            outcome = "conflict"

        if outcome:
            db.execute(
                "UPDATE studies SET second_screening_included = %s, exclusion_reason = %s WHERE id_review = %s AND id = %s;",
                (outcome, exclusion_reason, review_id, study_id),
            )
        db.commit()

    def import_wos_xls(review_id: int, path: str) -> tuple[int, int]:
        db = get_db()
        wb = CalamineWorkbook.from_path(path)
        sheet = wb.get_sheet_by_index(0)
        rows = sheet.to_python()
        if not rows:
            return 0, 0

        headers = [str(h).strip() for h in rows[0]]
        idx = {h: i for i, h in enumerate(headers)}

        def get(row, col):
            i = idx.get(col)
            if i is None or i >= len(row):
                return None
            val = row[i]
            if val is None:
                return None
            s = str(val).strip()
            return s if s else None

        inserted = 0
        duplicates = 0
        for row in rows[1:]:
            doc_type = get(row, "Document Type")
            doi = normalize_doi(get(row, "DOI"))
            title = get(row, "Article Title")
            authors = get(row, "Authors")
            year = get(row, "Publication Year")
            abstract = get(row, "Abstract")
            source = get(row, "Source Title")

            year_int = None
            if year:
                try:
                    year_int = int(float(year))
                except Exception:
                    year_int = None

            try:
                cur = db.execute(
                    """
                    INSERT INTO studies
                    (id_review, document_type, doi, title, authors, year, abstract, source_title)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING;
                    """,
                    (review_id, doc_type, doi, title, authors, year_int, abstract, source),
                )
                if cur.rowcount == 1:
                    inserted += 1
                else:
                    duplicates += 1
            except Exception:
                continue

        db.commit()
        return inserted, duplicates

    def import_scopus_csv(review_id: int, path: str) -> tuple[int, int]:
        db = get_db()
        inserted = 0
        duplicates = 0
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for r in reader:
                doc_type = (r.get("Document Type") or "").strip() or None
                doi = normalize_doi(r.get("DOI"))
                title = (r.get("Title") or "").strip() or None
                authors = (r.get("Authors") or "").strip() or None
                year = (r.get("Year") or "").strip() or None
                abstract = (r.get("Abstract") or "").strip() or None
                source = (r.get("Source title") or r.get("Source Title") or "").strip() or None

                year_int = None
                if year:
                    try:
                        year_int = int(float(year))
                    except Exception:
                        year_int = None

                try:
                    cur = db.execute(
                        """
                        INSERT INTO studies
                        (id_review, document_type, doi, title, authors, year, abstract, source_title)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING;
                        """,
                        (review_id, doc_type, doi, title, authors, year_int, abstract, source),
                    )
                    if cur.rowcount == 1:
                        inserted += 1
                    else:
                        duplicates += 1
                except Exception:
                    continue

        db.commit()
        return inserted, duplicates

    def delete_empty_studies(review_id: int) -> int:
        db = get_db()
        cur = db.execute(
            """
            DELETE FROM studies
            WHERE id_review = %s
              AND document_type IS NULL
              AND doi IS NULL
              AND title IS NULL
              AND authors IS NULL
              AND year IS NULL
              AND abstract IS NULL
              AND source_title IS NULL
              AND first_screening_included IS NULL
              AND first_screening_notes IS NULL
              AND second_screening_included IS NULL
              AND second_screening_notes IS NULL
              AND exclusion_reason IS NULL;
            """,
            (review_id,),
        )
        db.commit()
        return cur.rowcount

    # ---------- routes ----------

    @app.route("/")
    def index():
        return redirect(url_for("home"))

    @app.route("/0_home.html", methods=["GET", "POST"])
    def home():
        db = get_db()

        if request.method == "POST":
            if request.form.get("action") == "create":
                review_name = (request.form.get("review_name") or "").strip()
                participants_raw = (request.form.get("participants") or "").strip()
                if not review_name:
                    flash("Please provide a review name.", "error")
                    return redirect(url_for("home"))

                participants = split_participants(participants_raw)
                participants_name = "; ".join(participants)
                participants_number = len(participants)

                cur = db.execute(
                    """
                    INSERT INTO review (review_name, participants_number, participants_name)
                    VALUES (%s, %s, %s)
                    RETURNING id;
                    """,
                    (review_name, participants_number, participants_name),
                )
                review_id = cur.fetchone()["id"]

                for name in participants:
                    db.execute(
                        "INSERT INTO reviewers (id_review, reviewer_name) VALUES (%s, %s);",
                        (review_id, name),
                    )
                db.commit()
                refresh_cached_metrics(review_id)
                flash(f"Review created (id: {review_id}).", "success")
                return redirect(url_for("home"))

        reviews = db.execute("SELECT * FROM review ORDER BY id DESC;").fetchall()
        delete_password = (os.environ.get("DELETE_PASSWORD") or "").strip()
        return render_template("0_home.html", reviews=reviews, delete_password=delete_password)

    @app.route("/review/<int:review_id>/delete", methods=["POST"])
    def delete_review(review_id: int):
        db = get_db()
        db.execute("DELETE FROM review WHERE id = %s;", (review_id,))
        db.commit()
        if session.get("login", {}).get("review_id") == review_id:
            session.pop("login", None)
        flash("Review deleted.", "success")
        return redirect(url_for("home"))

    @app.route("/<int:review_id>_main.html", methods=["GET", "POST"])
    def review_main(review_id: int):
        db = get_db()
        review = db.execute("SELECT * FROM review WHERE id = %s;", (review_id,)).fetchone()
        if not review:
            abort(404)

        reviewers = db.execute(
            "SELECT * FROM reviewers WHERE id_review = %s ORDER BY lower(reviewer_name);",
            (review_id,),
        ).fetchall()

        # Random order for both login dropdowns
        names = [r["reviewer_name"] for r in reviewers]
        names1 = names[:]
        names2 = names[:]
        random.shuffle(names1)
        random.shuffle(names2)

        if request.method == "POST":
            action = request.form.get("action")

            if action == "login":
                name1 = (request.form.get("login_name_1") or "").strip()
                name2 = (request.form.get("login_name_2") or "").strip()
                if not name1 or not name2 or name1 != name2:
                    flash("Login failed: select your name twice, and both must match.", "error")
                    return redirect(url_for("review_main", review_id=review_id))

                row = db.execute(
                    "SELECT id, reviewer_name FROM reviewers WHERE id_review = %s AND reviewer_name = %s;",
                    (review_id, name1),
                ).fetchone()
                if not row:
                    flash("Login failed: reviewer not found.", "error")
                    return redirect(url_for("review_main", review_id=review_id))

                session["login"] = {
                    "review_id": review_id,
                    "reviewer_id": int(row["id"]),
                    "reviewer_name": row["reviewer_name"],
                }
                flash(f"Logged in as {row['reviewer_name']}.", "success")
                return redirect(url_for("review_main", review_id=review_id))

            if action == "logout":
                session.pop("login", None)
                flash("Logged out.", "success")
                return redirect(url_for("review_main", review_id=review_id))

            if action == "change_title":
                new_title = (request.form.get("new_title") or "").strip()
                if not new_title:
                    flash("Title cannot be empty.", "error")
                    return redirect(url_for("review_main", review_id=review_id))
                db.execute("UPDATE review SET review_name = %s WHERE id = %s;", (new_title, review_id))
                db.commit()
                flash("Title updated.", "success")
                return redirect(url_for("review_main", review_id=review_id))

            if action == "rename_reviewer":
                reviewer_id = int(request.form.get("reviewer_id"))
                new_name = (request.form.get("new_name") or "").strip()
                if not new_name:
                    flash("Name cannot be empty.", "error")
                    return redirect(url_for("review_main", review_id=review_id))

                try:
                    db.execute(
                        "UPDATE reviewers SET reviewer_name = %s WHERE id = %s AND id_review = %s;",
                        (new_name, reviewer_id, review_id),
                    )
                    db.commit()
                except Exception:
                    db.rollback()
                    flash("Rename failed (maybe duplicate name).", "error")
                    return redirect(url_for("review_main", review_id=review_id))

                # update review participants from reviewers
                rows = db.execute(
                    "SELECT reviewer_name FROM reviewers WHERE id_review = %s ORDER BY id;",
                    (review_id,),
                ).fetchall()
                participants_name = "; ".join([r["reviewer_name"] for r in rows])
                db.execute(
                    "UPDATE review SET participants_name = %s, participants_number = %s WHERE id = %s;",
                    (participants_name, len(rows), review_id),
                )
                db.commit()

                # update session if needed
                login = session.get("login")
                if login and login.get("review_id") == review_id and login.get("reviewer_id") == reviewer_id:
                    login["reviewer_name"] = new_name
                    session["login"] = login

                flash("Reviewer renamed.", "success")
                return redirect(url_for("review_main", review_id=review_id))

            if action == "import_studies":
                wos = request.files.get("wos_file")
                scopus = request.files.get("scopus_file")
                inserted = 0
                duplicates = 0
                deleted = 0
                errors = []

                if wos and wos.filename:
                    if not wos.filename.lower().endswith(".xls"):
                        errors.append("Only .xls format is admitted for WoS!")
                    else:
                        path = save_upload(wos)
                        try:
                            wos_inserted, wos_duplicates = import_wos_xls(review_id, path)
                            inserted += wos_inserted
                            duplicates += wos_duplicates
                        except Exception as e:
                            errors.append(f"WoS import failed: {e}")

                if scopus and scopus.filename:
                    if not scopus.filename.lower().endswith(".csv"):
                        errors.append("Only .csv format is admitted for Scopus!")
                    else:
                        path = save_upload(scopus)
                        try:
                            scopus_inserted, scopus_duplicates = import_scopus_csv(review_id, path)
                            inserted += scopus_inserted
                            duplicates += scopus_duplicates
                        except Exception as e:
                            errors.append(f"Scopus import failed: {e}")

                deleted = delete_empty_studies(review_id)
                removed = duplicates + deleted
                if removed:
                    db.execute(
                        "UPDATE review SET duplicates_removed = duplicates_removed + %s WHERE id = %s;",
                        (removed, review_id),
                    )
                    db.commit()
                refresh_cached_metrics(review_id)
                for e in errors:
                    flash(e, "error")
                flash(
                    f"Imported {inserted} studies in total. "
                    f"{removed} duplicate studies were detected and removed.",
                    "success",
                )
                return redirect(url_for("review_main", review_id=review_id))

        refresh_cached_metrics(review_id)
        review = db.execute("SELECT * FROM review WHERE id = %s;", (review_id,)).fetchone()

        total = db.execute("SELECT COUNT(*) AS c FROM studies WHERE id_review = %s;", (review_id,)).fetchone()["c"]

        first_pending = db.execute(
            "SELECT COUNT(*) AS c FROM studies WHERE id_review = %s AND first_screening_included IS NULL;",
            (review_id,),
        ).fetchone()["c"]
        first_conflicts = db.execute(
            "SELECT COUNT(*) AS c FROM studies WHERE id_review = %s AND first_screening_included = 'conflict';",
            (review_id,),
        ).fetchone()["c"]
        first_done = db.execute(
            "SELECT COUNT(*) AS c FROM studies WHERE id_review = %s AND first_screening_included IN ('yes','no');",
            (review_id,),
        ).fetchone()["c"]
        first_irrelevant = db.execute(
            "SELECT COUNT(*) AS c FROM studies WHERE id_review = %s AND first_screening_included = 'no';",
            (review_id,),
        ).fetchone()["c"]

        second_pending = db.execute(
            """
            SELECT COUNT(*) AS c FROM studies
            WHERE id_review = %s AND first_screening_included='yes' AND second_screening_included IS NULL;
            """,
            (review_id,),
        ).fetchone()["c"]
        second_conflicts = db.execute(
            "SELECT COUNT(*) AS c FROM studies WHERE id_review = %s AND second_screening_included = 'conflict';",
            (review_id,),
        ).fetchone()["c"]
        second_done = db.execute(
            "SELECT COUNT(*) AS c FROM studies WHERE id_review = %s AND second_screening_included IN ('yes','no');",
            (review_id,),
        ).fetchone()["c"]
        second_excluded = db.execute(
            "SELECT COUNT(*) AS c FROM studies WHERE id_review = %s AND second_screening_included = 'no';",
            (review_id,),
        ).fetchone()["c"]

        to_extract = db.execute(
            "SELECT COUNT(*) AS c FROM studies WHERE id_review = %s AND second_screening_included = 'yes';",
            (review_id,),
        ).fetchone()["c"]

        logged = session.get("login") if session.get("login", {}).get("review_id") == review_id else None
        duplicates_removed = review["duplicates_removed"] or 0
        total_loaded = total + duplicates_removed

        return render_template(
            "review_main.html",
            review=review,
            reviewers=reviewers,
            names1=names1,
            names2=names2,
            total=total,
            duplicates_removed=duplicates_removed,
            total_loaded=total_loaded,
            first_pending=first_pending,
            first_conflicts=first_conflicts,
            first_done=first_done,
            first_irrelevant=first_irrelevant,
            second_pending=second_pending,
            second_conflicts=second_conflicts,
            second_done=second_done,
            second_excluded=second_excluded,
            to_extract=to_extract,
            logged=logged,
        )

    @app.route("/<int:review_id>_first_screening.html", methods=["GET", "POST"])
    def first_screening(review_id: int):
        db = get_db()
        review = db.execute("SELECT * FROM review WHERE id = %s;", (review_id,)).fetchone()
        if not review:
            abort(404)

        try:
            reviewer_id, reviewer_name = require_login(review_id)
        except PermissionError as e:
            flash(str(e), "error")
            return redirect(url_for("review_main", review_id=review_id))

        per_page, page, sort = parse_pagination_args()

        if request.method == "POST":
            study_id = int(request.form.get("study_id"))
            decision_btn = request.form.get("decision")
            notes = request.form.get("notes") or ""

            if decision_btn not in ("no", "maybe", "yes"):
                flash("Invalid decision.", "error")
                return redirect(url_for("first_screening", review_id=review_id))

            try:
                db.execute(
                    """
                    INSERT INTO first_screening (id_review, id_reviewer, id_study, decision)
                    VALUES (%s, %s, %s, %s);
                    """,
                    (review_id, reviewer_id, study_id, decision_btn),
                )
                db.commit()
            except Exception:
                db.rollback()
                flash("You already screened this study.", "error")
                return redirect(url_for("first_screening", review_id=review_id))

            row = db.execute(
                "SELECT first_screening_notes FROM studies WHERE id_review = %s AND id = %s;",
                (review_id, study_id),
            ).fetchone()
            new_notes = append_note(row["first_screening_notes"], reviewer_name, notes)
            db.execute(
                "UPDATE studies SET first_screening_notes = %s WHERE id_review = %s AND id = %s;",
                (new_notes, review_id, study_id),
            )
            db.commit()

            consolidate_first(review_id, study_id)
            refresh_cached_metrics(review_id)
            return redirect(url_for("first_screening", review_id=review_id, page=page, per_page=per_page, sort=sort))

        total = db.execute(
            """
            SELECT COUNT(*) AS c FROM studies
            WHERE id_review = %s
              AND first_screening_included IS NULL
              AND id NOT IN (
                SELECT id_study FROM first_screening
                WHERE id_review = %s AND id_reviewer = %s
              );
            """,
            (review_id, review_id, reviewer_id),
        ).fetchone()["c"]
        page, total_pages = clamp_page(page, total, per_page)
        offset = (page - 1) * per_page

        studies = db.execute(
            """
            SELECT * FROM studies
            WHERE id_review = %s
              AND first_screening_included IS NULL
              AND id NOT IN (
                SELECT id_study FROM first_screening
                WHERE id_review = %s AND id_reviewer = %s
              )
            ORDER BY """
            + sort_clause(sort)
            + """
            LIMIT %s OFFSET %s;
            """,
            (review_id, review_id, reviewer_id, per_page, offset),
        ).fetchall()

        return render_template(
            "first_screening.html",
            review=review,
            studies=studies,
            reviewer_name=reviewer_name,
            page=page,
            per_page=per_page,
            sort=sort,
            total=total,
            total_pages=total_pages,
        )

    @app.route("/<int:review_id>_first_screening_conflicts.html", methods=["GET", "POST"])
    def first_screening_conflicts(review_id: int):
        db = get_db()
        review = db.execute("SELECT * FROM review WHERE id = %s;", (review_id,)).fetchone()
        if not review:
            abort(404)

        try:
            _, reviewer_name = require_login(review_id)
        except PermissionError as e:
            flash(str(e), "error")
            return redirect(url_for("review_main", review_id=review_id))

        per_page, page, sort = parse_pagination_args()

        if request.method == "POST":
            study_id = int(request.form.get("study_id"))
            final = request.form.get("final_decision")
            notes = request.form.get("notes") or ""

            if final not in ("yes", "no"):
                flash("Invalid final decision.", "error")
                return redirect(url_for("first_screening_conflicts", review_id=review_id))

            db.execute(
                "UPDATE studies SET first_screening_included = %s WHERE id_review = %s AND id = %s;",
                (final, review_id, study_id),
            )

            row = db.execute(
                "SELECT first_screening_notes FROM studies WHERE id_review = %s AND id = %s;",
                (review_id, study_id),
            ).fetchone()
            new_notes = append_note(row["first_screening_notes"], reviewer_name, notes)
            db.execute(
                "UPDATE studies SET first_screening_notes = %s WHERE id_review = %s AND id = %s;",
                (new_notes, review_id, study_id),
            )
            db.commit()

            refresh_cached_metrics(review_id)
            return redirect(
                url_for(
                    "first_screening_conflicts",
                    review_id=review_id,
                    page=page,
                    per_page=per_page,
                    sort=sort,
                )
            )

        total = db.execute(
            "SELECT COUNT(*) AS c FROM studies WHERE id_review = %s AND first_screening_included = 'conflict';",
            (review_id,),
        ).fetchone()["c"]
        page, total_pages = clamp_page(page, total, per_page)
        offset = (page - 1) * per_page

        studies = db.execute(
            "SELECT * FROM studies WHERE id_review = %s AND first_screening_included = 'conflict' ORDER BY "
            + sort_clause(sort)
            + " LIMIT %s OFFSET %s;",
            (review_id, per_page, offset),
        ).fetchall()

        conflicts_map = {}
        for s in studies:
            rows = db.execute(
                """
                SELECT r.reviewer_name, fsc.decision
                FROM first_screening_conflicts fsc
                JOIN reviewers r ON r.id = fsc.id_reviewer
                WHERE fsc.id_review = %s AND fsc.id_study = %s
                ORDER BY lower(r.reviewer_name);
                """,
                (review_id, s["id"]),
            ).fetchall()
            conflicts_map[s["id"]] = rows

        return render_template(
            "first_screening_conflicts.html",
            review=review,
            studies=studies,
            conflicts_map=conflicts_map,
            reviewer_name=reviewer_name,
            page=page,
            per_page=per_page,
            sort=sort,
            total=total,
            total_pages=total_pages,
        )

    @app.route("/<int:review_id>_first_screening_contributions.html")
    def first_screening_contributions(review_id: int):
        db = get_db()
        review = db.execute("SELECT * FROM review WHERE id = %s;", (review_id,)).fetchone()
        if not review:
            abort(404)

        reviewers = db.execute(
            """
            SELECT reviewer_name, first_screening_contribution AS c
            FROM reviewers WHERE id_review = %s
            ORDER BY c DESC, lower(reviewer_name);
            """,
            (review_id,),
        ).fetchall()
        total = sum([r["c"] for r in reviewers]) or 1
        data = [{"name": r["reviewer_name"], "count": r["c"], "pct": int(r["c"] * 100 / total)} for r in reviewers]
        return render_template("first_screening_contributions.html", review=review, data=data)

    @app.route("/<int:review_id>_exclusion_reasons.html", methods=["GET", "POST"])
    def exclusion_reasons(review_id: int):
        db = get_db()
        review = db.execute("SELECT * FROM review WHERE id = %s;", (review_id,)).fetchone()
        if not review:
            abort(404)

        try:
            require_login(review_id)
        except PermissionError as e:
            flash(str(e), "error")
            return redirect(url_for("review_main", review_id=review_id))

        if request.method == "POST":
            action = request.form.get("action")
            if action == "add":
                hierarchy = request.form.get("hierarchy")
                reason = (request.form.get("reason") or "").strip()
                try:
                    hierarchy_i = int(hierarchy)
                except Exception:
                    hierarchy_i = None

                if hierarchy_i is None or not reason:
                    flash("Please provide hierarchy (integer) and reason.", "error")
                    return redirect(url_for("exclusion_reasons", review_id=review_id))

                db.execute(
                    "INSERT INTO exclusion_reasons (id_review, hierarchy, reason) VALUES (%s, %s, %s);",
                    (review_id, hierarchy_i, reason),
                )
                db.commit()
                flash("Exclusion reason added.", "success")
                return redirect(url_for("exclusion_reasons", review_id=review_id))

            if action == "delete":
                rid = int(request.form.get("reason_id"))
                db.execute(
                    "UPDATE exclusion_reasons SET is_active = 0 WHERE id_review = %s AND id = %s;",
                    (review_id, rid),
                )
                db.commit()
                flash("Exclusion reason deleted (deactivated).", "success")
                return redirect(url_for("exclusion_reasons", review_id=review_id))

        reasons = db.execute(
            """
            SELECT * FROM exclusion_reasons
            WHERE id_review = %s AND is_active = 1
            ORDER BY hierarchy ASC, id ASC;
            """,
            (review_id,),
        ).fetchall()

        return render_template("exclusion_reasons.html", review=review, reasons=reasons)

    @app.route("/review/<int:review_id>/studies/<int:study_id>/full_text", methods=["GET"])
    def read_full_text(review_id: int, study_id: int):
        db = get_db()
        review = db.execute("SELECT id FROM review WHERE id = %s;", (review_id,)).fetchone()
        if not review:
            abort(404)

        try:
            require_login(review_id)
        except PermissionError as e:
            flash(str(e), "error")
            return redirect(url_for("review_main", review_id=review_id))

        row = db.execute(
            "SELECT file_name, file_data FROM studies WHERE id_review = %s AND id = %s;",
            (review_id, study_id),
        ).fetchone()
        if not row or not row["file_name"]:
            abort(404)

        if row.get("file_data"):
            return send_file(
                BytesIO(row["file_data"]),
                mimetype="application/pdf",
                as_attachment=False,
                download_name=row["file_name"],
            )

        path = os.path.join(review_studies_dir(review_id), row["file_name"])
        if not os.path.exists(path):
            abort(404)

        return send_file(path, as_attachment=False, download_name=row["file_name"])

    @app.route("/review/<int:review_id>/studies/<int:study_id>/full_text/upload", methods=["POST"])
    def upload_full_text(review_id: int, study_id: int):
        db = get_db()
        review = db.execute("SELECT id FROM review WHERE id = %s;", (review_id,)).fetchone()
        if not review:
            abort(404)

        try:
            require_login(review_id)
        except PermissionError as e:
            flash(str(e), "error")
            return redirect(url_for("review_main", review_id=review_id))

        study = db.execute(
            "SELECT id FROM studies WHERE id_review = %s AND id = %s;",
            (review_id, study_id),
        ).fetchone()
        if not study:
            abort(404)

        per_page = parse_positive_int(request.form.get("per_page"), 25)
        if per_page not in {25, 50, 100}:
            per_page = 25
        page = parse_positive_int(request.form.get("page"), 1)
        sort = request.form.get("sort", "random")
        if sort not in {"random", "id", "authors", "title"}:
            sort = "random"

        upload = request.files.get("full_text")
        if not upload or not upload.filename:
            flash("Please select a PDF to upload.", "error")
            return redirect(url_for("second_screening", review_id=review_id, page=page, per_page=per_page, sort=sort))

        if not upload.filename.lower().endswith(".pdf"):
            flash("Only PDF files are allowed.", "error")
            return redirect(url_for("second_screening", review_id=review_id, page=page, per_page=per_page, sort=sort))

        file_name = safe_filename(upload.filename or f"{review_id}_{study_id}.pdf")
        upload_bytes = upload.read()

        db.execute(
            "UPDATE studies SET file_name = %s, file_data = %s WHERE id_review = %s AND id = %s;",
            (file_name, upload_bytes, review_id, study_id),
        )
        db.commit()

        redirect_url = url_for(
            "second_screening",
            review_id=review_id,
            page=page,
            per_page=per_page,
            sort=sort,
        )
        return redirect(f"{redirect_url}#study-{study_id}")

    @app.route("/review/<int:review_id>/studies/<int:study_id>/full_text/delete", methods=["POST"])
    def delete_full_text(review_id: int, study_id: int):
        db = get_db()
        review = db.execute("SELECT id FROM review WHERE id = %s;", (review_id,)).fetchone()
        if not review:
            abort(404)

        try:
            require_login(review_id)
        except PermissionError as e:
            flash(str(e), "error")
            return redirect(url_for("review_main", review_id=review_id))

        study = db.execute(
            "SELECT file_name, file_data FROM studies WHERE id_review = %s AND id = %s;",
            (review_id, study_id),
        ).fetchone()
        if not study:
            abort(404)

        per_page = parse_positive_int(request.form.get("per_page"), 25)
        if per_page not in {25, 50, 100}:
            per_page = 25
        page = parse_positive_int(request.form.get("page"), 1)
        sort = request.form.get("sort", "random")
        if sort not in {"random", "id", "authors", "title"}:
            sort = "random"

        if study.get("file_name") and not study.get("file_data"):
            path = os.path.join(review_studies_dir(review_id), study["file_name"])
            if os.path.exists(path):
                os.remove(path)

        db.execute(
            "UPDATE studies SET file_name = NULL, file_data = NULL WHERE id_review = %s AND id = %s;",
            (review_id, study_id),
        )
        db.commit()
        flash("Full-text PDF removed.", "success")

        redirect_url = url_for(
            "second_screening",
            review_id=review_id,
            page=page,
            per_page=per_page,
            sort=sort,
        )
        return redirect(f"{redirect_url}#study-{study_id}")

    @app.route("/<int:review_id>_second_screening.html", methods=["GET", "POST"])
    def second_screening(review_id: int):
        db = get_db()
        review = db.execute("SELECT * FROM review WHERE id = %s;", (review_id,)).fetchone()
        if not review:
            abort(404)

        try:
            reviewer_id, reviewer_name = require_login(review_id)
        except PermissionError as e:
            flash(str(e), "error")
            return redirect(url_for("review_main", review_id=review_id))

        per_page, page, sort = parse_pagination_args()

        reasons = db.execute(
            """
            SELECT id, hierarchy, reason FROM exclusion_reasons
            WHERE id_review = %s AND is_active = 1
            ORDER BY hierarchy ASC, id ASC;
            """,
            (review_id,),
        ).fetchall()

        if request.method == "POST":
            study_id = int(request.form.get("study_id"))
            action = request.form.get("action")
            notes = request.form.get("notes") or ""

            if action == "include":
                decision = "yes"
                reason_id = None
            elif action == "exclude":
                decision = "no"
                reason_id = request.form.get("reason_id")
                if not reason_id:
                    flash("Please select an exclusion reason.", "error")
                    return redirect(url_for("second_screening", review_id=review_id))
                reason_id = int(reason_id)
            else:
                flash("Invalid action.", "error")
                return redirect(url_for("second_screening", review_id=review_id))

            try:
                db.execute(
                    """
                    INSERT INTO second_screening (id_review, id_reviewer, id_study, decision, reason)
                    VALUES (%s, %s, %s, %s, %s);
                    """,
                    (review_id, reviewer_id, study_id, decision, reason_id),
                )
                db.commit()
            except Exception:
                db.rollback()
                flash("You already screened this study in second screening.", "error")
                return redirect(url_for("second_screening", review_id=review_id))

            row = db.execute(
                "SELECT second_screening_notes FROM studies WHERE id_review = %s AND id = %s;",
                (review_id, study_id),
            ).fetchone()
            new_notes = append_note(row["second_screening_notes"], reviewer_name, notes)
            db.execute(
                "UPDATE studies SET second_screening_notes = %s WHERE id_review = %s AND id = %s;",
                (new_notes, review_id, study_id),
            )
            db.commit()

            consolidate_second(review_id, study_id)
            refresh_cached_metrics(review_id)
            return redirect(url_for("second_screening", review_id=review_id, page=page, per_page=per_page, sort=sort))

        total = db.execute(
            """
            SELECT COUNT(*) AS c FROM studies
            WHERE id_review = %s
              AND first_screening_included = 'yes'
              AND second_screening_included IS NULL
              AND id NOT IN (
                SELECT id_study FROM second_screening
                WHERE id_review = %s AND id_reviewer = %s
              );
            """,
            (review_id, review_id, reviewer_id),
        ).fetchone()["c"]
        page, total_pages = clamp_page(page, total, per_page)
        offset = (page - 1) * per_page

        studies = db.execute(
            """
            SELECT * FROM studies
            WHERE id_review = %s
              AND first_screening_included = 'yes'
              AND second_screening_included IS NULL
              AND id NOT IN (
                SELECT id_study FROM second_screening
                WHERE id_review = %s AND id_reviewer = %s
              )
            ORDER BY """
            + sort_clause(sort)
            + """
            LIMIT %s OFFSET %s;
            """,
            (review_id, review_id, reviewer_id, per_page, offset),
        ).fetchall()

        return render_template(
            "second_screening.html",
            review=review,
            studies=studies,
            reviewer_name=reviewer_name,
            reasons=reasons,
            page=page,
            per_page=per_page,
            sort=sort,
            total=total,
            total_pages=total_pages,
        )

    @app.route("/<int:review_id>_second_screening_conflicts.html", methods=["GET", "POST"])
    def second_screening_conflicts(review_id: int):
        db = get_db()
        review = db.execute("SELECT * FROM review WHERE id = %s;", (review_id,)).fetchone()
        if not review:
            abort(404)

        try:
            _, reviewer_name = require_login(review_id)
        except PermissionError as e:
            flash(str(e), "error")
            return redirect(url_for("review_main", review_id=review_id))

        per_page, page, sort = parse_pagination_args()

        reasons = db.execute(
            """
            SELECT id, hierarchy, reason FROM exclusion_reasons
            WHERE id_review = %s AND is_active = 1
            ORDER BY hierarchy ASC, id ASC;
            """,
            (review_id,),
        ).fetchall()

        if request.method == "POST":
            study_id = int(request.form.get("study_id"))
            final = request.form.get("final")
            notes = request.form.get("notes") or ""

            if final == "include":
                db.execute(
                    "UPDATE studies SET second_screening_included = 'yes', exclusion_reason = NULL WHERE id_review = %s AND id = %s;",
                    (review_id, study_id),
                )
            elif final == "exclude":
                reason_id = request.form.get("reason_id")
                if not reason_id:
                    flash("Please select an exclusion reason for Exclude.", "error")
                    return redirect(url_for("second_screening_conflicts", review_id=review_id))
                reason_id = int(reason_id)
                db.execute(
                    "UPDATE studies SET second_screening_included = 'no', exclusion_reason = %s WHERE id_review = %s AND id = %s;",
                    (reason_id, review_id, study_id),
                )
            else:
                flash("Invalid final decision.", "error")
                return redirect(url_for("second_screening_conflicts", review_id=review_id))

            row = db.execute(
                "SELECT second_screening_notes FROM studies WHERE id_review = %s AND id = %s;",
                (review_id, study_id),
            ).fetchone()
            new_notes = append_note(row["second_screening_notes"], reviewer_name, notes)
            db.execute(
                "UPDATE studies SET second_screening_notes = %s WHERE id_review = %s AND id = %s;",
                (new_notes, review_id, study_id),
            )
            db.commit()

            refresh_cached_metrics(review_id)
            return redirect(
                url_for(
                    "second_screening_conflicts",
                    review_id=review_id,
                    page=page,
                    per_page=per_page,
                    sort=sort,
                )
            )

        total = db.execute(
            "SELECT COUNT(*) AS c FROM studies WHERE id_review = %s AND second_screening_included = 'conflict';",
            (review_id,),
        ).fetchone()["c"]
        page, total_pages = clamp_page(page, total, per_page)
        offset = (page - 1) * per_page

        studies = db.execute(
            "SELECT * FROM studies WHERE id_review = %s AND second_screening_included = 'conflict' ORDER BY "
            + sort_clause(sort)
            + " LIMIT %s OFFSET %s;",
            (review_id, per_page, offset),
        ).fetchall()

        conflicts_map = {}
        for s in studies:
            rows = db.execute(
                """
                SELECT r.reviewer_name, ssc.decision, ssc.reason, er.hierarchy, er.reason AS reason_text
                FROM second_screening_conflicts ssc
                JOIN reviewers r ON r.id = ssc.id_reviewer
                LEFT JOIN exclusion_reasons er ON er.id = ssc.reason
                WHERE ssc.id_review = %s AND ssc.id_study = %s
                ORDER BY lower(r.reviewer_name);
                """,
                (review_id, s["id"]),
            ).fetchall()
            conflicts_map[s["id"]] = rows

        return render_template(
            "second_screening_conflicts.html",
            review=review,
            studies=studies,
            conflicts_map=conflicts_map,
            reviewer_name=reviewer_name,
            reasons=reasons,
            page=page,
            per_page=per_page,
            sort=sort,
            total=total,
            total_pages=total_pages,
        )

    @app.route("/<int:review_id>_second_screening_contributions.html")
    def second_screening_contributions(review_id: int):
        db = get_db()
        review = db.execute("SELECT * FROM review WHERE id = %s;", (review_id,)).fetchone()
        if not review:
            abort(404)

        reviewers = db.execute(
            """
            SELECT reviewer_name, second_screening_contribution AS c
            FROM reviewers WHERE id_review = %s
            ORDER BY c DESC, lower(reviewer_name);
            """,
            (review_id,),
        ).fetchall()
        total = sum([r["c"] for r in reviewers]) or 1
        data = [{"name": r["reviewer_name"], "count": r["c"], "pct": int(r["c"] * 100 / total)} for r in reviewers]
        return render_template("second_screening_contributions.html", review=review, data=data)

    @app.route("/<int:review_id>_list_of_studies.html")
    def list_of_studies(review_id: int):
        db = get_db()
        review = db.execute("SELECT * FROM review WHERE id = %s;", (review_id,)).fetchone()
        if not review:
            abort(404)

        rows = db.execute(
            """
            SELECT s.*,
                   er.hierarchy AS exclusion_reason_hierarchy,
                   er.reason AS exclusion_reason_text
            FROM studies s
            LEFT JOIN exclusion_reasons er ON er.id = s.exclusion_reason
            WHERE s.id_review = %s
            ORDER BY s.id ASC;
            """,
            (review_id,),
        ).fetchall()

        return render_template("list_of_studies.html", review=review, rows=rows)

    @app.route("/review/<int:review_id>/export_studies.xlsx")
    def export_studies_xlsx(review_id: int):
        db = get_db()
        review = db.execute("SELECT * FROM review WHERE id = %s;", (review_id,)).fetchone()
        if not review:
            abort(404)

        rows = db.execute(
            """
            SELECT s.*,
                   er.hierarchy AS exclusion_reason_hierarchy,
                   er.reason AS exclusion_reason_text
            FROM studies s
            LEFT JOIN exclusion_reasons er ON er.id = s.exclusion_reason
            WHERE s.id_review = %s
            ORDER BY s.id ASC;
            """,
            (review_id,),
        ).fetchall()

        wb = Workbook()
        ws = wb.active
        ws.title = "Studies"

        headers = [
            "Study ID", "DOI", "Title", "Authors", "Year", "Abstract", "Source",
            "First screening decision", "First screening notes",
            "Second screening decision", "Second screening notes",
            "Exclusion reason",
        ]
        ws.append(headers)

        for r in rows:
            ws.append([
                r["id"],
                r["doi"] or "",
                r["title"] or "",
                r["authors"] or "",
                r["year"] or "",
                r["abstract"] or "",
                r["source_title"] or "",
                r["first_screening_included"] or "",
                r["first_screening_notes"] or "",
                r["second_screening_included"] or "",
                r["second_screening_notes"] or "",
                " ".join(
                    str(part)
                    for part in [r["exclusion_reason_hierarchy"], r["exclusion_reason_text"]]
                    if part
                ),
            ])

        out_path = os.path.join(app.instance_path, f"review_{review_id}_studies.xlsx")
        wb.save(out_path)
        return send_file(out_path, as_attachment=True, download_name=f"review_{review_id}_studies.xlsx")

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)

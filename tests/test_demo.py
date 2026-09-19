import os
import tempfile
import unittest


class DemoSmokeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        os.environ["DATABASE_URL"] = f"sqlite:///{cls.temp_dir.name}/test.db"
        os.environ["DEMO_MODE"] = "true"
        os.environ["SECRET_KEY"] = "test-only"
        from app import create_app

        cls.app = create_app()
        cls.app.config.update(TESTING=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def setUp(self):
        self.client = self.app.test_client()

    def test_seeded_demo_and_health(self):
        self.assertEqual(self.client.get("/healthz").status_code, 200)
        response = self.client.get("/0_home.html")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Example 1: Degrowth in agricultural systems", response.data)
        self.assertIn(b"6 participants", response.data)
        self.assertIn(b"Portfolio demo", response.data)

    def test_exported_metadata_and_exclusion_reasons(self):
        from db import get_db

        with self.app.app_context():
            db = get_db()
            study = db.execute(
                """
                SELECT doi, title, authors, year, abstract, source_title
                FROM studies
                WHERE id = %s
                """,
                (97,),
            ).fetchone()
            self.assertEqual(study["doi"], "10.1016/j.jclepro.2022.130632")
            self.assertEqual(
                study["title"],
                "Taking a whole-of-system approach to food packaging reduction",
            )
            self.assertIn("Chakori", study["authors"])
            self.assertEqual(study["year"], 2022)
            self.assertGreater(len(study["abstract"]), 500)
            self.assertEqual(study["source_title"], "JOURNAL OF CLEANER PRODUCTION")

            reasons = db.execute(
                "SELECT hierarchy, reason FROM exclusion_reasons ORDER BY hierarchy"
            ).fetchall()
            self.assertEqual([row["hierarchy"] for row in reasons], [1, 2, 3, 4])
            self.assertIn("Wrong Language", reasons[0]["reason"])
            self.assertIn("Wrong Conceptual focus", reasons[3]["reason"])

            excluded = db.execute(
                """
                SELECT s.second_screening_included, er.hierarchy
                FROM studies s
                JOIN exclusion_reasons er ON er.id = s.exclusion_reason
                WHERE s.id = %s
                """,
                (117,),
            ).fetchone()
            self.assertEqual(excluded["second_screening_included"], "no")
            self.assertEqual(excluded["hierarchy"], 3)

    def test_single_dropdown_login_and_seeded_conflicts(self):
        from db import get_db

        page = self.client.get("/1_main.html")
        self.assertEqual(page.status_code, 200)
        self.assertIn(b'name="login_name"', page.data)
        self.assertNotIn(b'login_name_2', page.data)

        login = self.client.post(
            "/1_main.html",
            data={"action": "login", "login_name": "Alex Morgan"},
            follow_redirects=True,
        )
        self.assertEqual(login.status_code, 200)
        self.assertIn(b"Logged in as", login.data)
        self.assertIn(b"Alex Morgan", login.data)

        with self.app.app_context():
            db = get_db()
            phase_counts = db.execute(
                """
                SELECT
                  SUM(CASE WHEN first_screening_included = 'conflict' THEN 1 ELSE 0 END)
                    AS first_conflicts,
                  SUM(CASE WHEN second_screening_included = 'conflict' THEN 1 ELSE 0 END)
                    AS second_conflicts
                FROM studies WHERE id_review = 1
                """
            ).fetchone()
            self.assertEqual(phase_counts["first_conflicts"], 2)
            self.assertEqual(phase_counts["second_conflicts"], 2)

            first_rows = db.execute(
                """
                SELECT s.id, s.first_screening_notes, COUNT(fsc.id_reviewer) AS decisions
                FROM studies s
                JOIN first_screening_conflicts fsc
                  ON fsc.id_review = s.id_review AND fsc.id_study = s.id
                WHERE s.id_review = 1 AND s.first_screening_included = 'conflict'
                GROUP BY s.id, s.first_screening_notes
                ORDER BY s.id
                """
            ).fetchall()
            self.assertEqual(len(first_rows), 2)
            self.assertTrue(all(row["decisions"] == 2 for row in first_rows))
            self.assertTrue(all(";$]" in row["first_screening_notes"] for row in first_rows))

            second_rows = db.execute(
                """
                SELECT s.id, s.second_screening_notes, er.hierarchy, er.reason
                FROM studies s
                JOIN second_screening_conflicts ssc
                  ON ssc.id_review = s.id_review AND ssc.id_study = s.id
                JOIN exclusion_reasons er ON er.id = ssc.reason
                WHERE s.id_review = 1
                  AND s.second_screening_included = 'conflict'
                  AND ssc.decision = 'no'
                ORDER BY s.id
                """
            ).fetchall()
            self.assertEqual(len(second_rows), 2)
            self.assertEqual(
                [row["hierarchy"] for row in second_rows],
                [3, 4],
            )
            self.assertTrue(all(row["reason"].startswith("Wrong ") for row in second_rows))
            self.assertTrue(all(";$]" in row["second_screening_notes"] for row in second_rows))

    def test_extraction_examples_have_complete_metadata(self):
        from db import get_db

        expected = {
            6: (
                "NATURE FOOD",
                2025,
                "10.1038/s43016-024-01108-5",
                "Matthew Gibson",
                "Degrowth as a plausible pathway",
            ),
            7: (
                "NATURE SUSTAINABILITY",
                2022,
                "10.1038/s41893-022-00933-5",
                "Steven R. McGreevy",
                "Sustainable agrifood systems",
            ),
            9: (
                "CERS",
                2014,
                None,
                "Judit Dombi",
                "Evaluation of Local Food Systems",
            ),
            10: (
                "NATURE FOOD",
                2022,
                "10.1038/s43016-022-00500-3",
                "Benjamin Leon Bodirsky",
                "Integrating degrowth and efficiency perspectives",
            ),
        }

        with self.app.app_context():
            db = get_db()
            rows = db.execute(
                """
                SELECT id, source_title, year, doi, authors, title, abstract,
                       file_name, length(file_data) AS file_size
                FROM studies
                WHERE id_review = 1 AND id IN (6,7,9,10)
                ORDER BY id
                """
            ).fetchall()
            self.assertEqual([row["id"] for row in rows], [6, 7, 9, 10])
            for row in rows:
                journal, year, doi, author, title = expected[row["id"]]
                self.assertEqual(row["source_title"], journal)
                self.assertEqual(row["year"], year)
                self.assertEqual(row["doi"], doi)
                self.assertIn(author, row["authors"])
                self.assertIn(title, row["title"])
                self.assertGreater(len(row["abstract"]), 250)
                self.assertTrue(row["file_name"].startswith(f"{row['id']}_"))
                self.assertGreater(row["file_size"], 0)

    def test_pdf_only_second_screening_and_phase_counts(self):
        from db import get_db

        with self.app.app_context():
            db = get_db()
            review = db.execute(
                "SELECT id, participants_number FROM review WHERE review_name = %s",
                ("Example 1: Degrowth in agricultural systems",),
            ).fetchone()
            self.assertEqual(review["participants_number"], 6)

            counts = db.execute(
                """
                SELECT
                  COUNT(*) AS total,
                  SUM(CASE WHEN file_data IS NOT NULL THEN 1 ELSE 0 END) AS with_pdf,
                  SUM(CASE WHEN first_screening_included IS NULL THEN 1 ELSE 0 END) AS first_pending,
                  SUM(CASE WHEN first_screening_included = 'conflict' THEN 1 ELSE 0 END) AS first_conflicts,
                  SUM(CASE WHEN first_screening_included = 'no' THEN 1 ELSE 0 END) AS first_rejected,
                  SUM(CASE WHEN first_screening_included = 'yes'
                            AND second_screening_included IS NULL THEN 1 ELSE 0 END) AS second_pending,
                  SUM(CASE WHEN second_screening_included = 'conflict' THEN 1 ELSE 0 END) AS second_conflicts,
                  SUM(CASE WHEN second_screening_included = 'yes' THEN 1 ELSE 0 END) AS to_extract,
                  SUM(CASE WHEN second_screening_included = 'no' THEN 1 ELSE 0 END) AS second_excluded,
                  SUM(CASE WHEN first_screening_included = 'yes'
                            AND second_screening_included IS NULL
                            AND file_data IS NULL THEN 1 ELSE 0 END) AS second_without_pdf
                FROM studies
                WHERE id_review = %s
                """,
                (review["id"],),
            ).fetchone()
            self.assertEqual(counts["total"], 258)
            self.assertEqual(counts["with_pdf"], 38)
            self.assertEqual(counts["first_pending"], 164)
            self.assertEqual(counts["first_conflicts"], 2)
            self.assertEqual(counts["first_rejected"], 54)
            self.assertEqual(counts["second_pending"], 12)
            self.assertEqual(counts["second_conflicts"], 2)
            self.assertEqual(counts["to_extract"], 6)
            self.assertEqual(counts["second_excluded"], 18)
            self.assertEqual(counts["second_without_pdf"], 0)

            second_studies = db.execute(
                """
                SELECT id, file_name, length(file_data) AS file_size
                FROM studies
                WHERE id_review = %s
                  AND first_screening_included = 'yes'
                  AND second_screening_included IS NULL
                """,
                (review["id"],),
            ).fetchall()
            self.assertTrue(second_studies)
            self.assertTrue(
                all(row["file_name"].startswith(f"{row['id']}_") for row in second_studies)
            )
            self.assertTrue(all(row["file_size"] > 0 for row in second_studies))

    def test_second_screening_pdf_can_be_opened(self):
        login = self.client.post(
            "/1_main.html",
            data={
                "action": "login",
                "login_name": "Alex Morgan",
            },
            follow_redirects=True,
        )
        self.assertEqual(login.status_code, 200)

        pdf = self.client.get("/review/1/studies/121/full_text")
        self.assertEqual(pdf.status_code, 200)
        self.assertEqual(pdf.mimetype, "application/pdf")
        self.assertTrue(pdf.data.startswith(b"%PDF"))

    def test_dashboard_and_export(self):
        self.assertEqual(self.client.get("/1_main.html").status_code, 200)
        export = self.client.get("/review/1/export_studies.xlsx")
        self.assertEqual(export.status_code, 200)
        self.assertEqual(
            export.mimetype,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    def test_create_review(self):
        response = self.client.post(
            "/0_home.html",
            data={
                "action": "create",
                "review_name": "Recruiter test",
                "participants": "Reviewer One",
                "two_reviewer_consensus": "no",
                "delete_password": "temporary",
                "delete_password_confirm": "temporary",
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Recruiter test", response.data)

        reset = self.client.post("/demo/reset", follow_redirects=True)
        self.assertEqual(reset.status_code, 200)
        self.assertNotIn(b"Recruiter test", reset.data)
        self.assertIn(b"Example 1: Degrowth in agricultural systems", reset.data)


    def test_z_local_sqlite_screening_workflow(self):
        from db import get_db

        self.client.post("/demo/reset")
        with self.app.app_context():
            db = get_db()
            first_study_id = db.execute(
                """
                SELECT id FROM studies
                WHERE id_review = 1 AND first_screening_included IS NULL
                ORDER BY id LIMIT 1
                """
            ).fetchone()["id"]
            second_study_id = db.execute(
                """
                SELECT id FROM studies
                WHERE id_review = 1
                  AND first_screening_included = 'yes'
                  AND second_screening_included IS NULL
                  AND file_data IS NOT NULL
                ORDER BY id LIMIT 1
                """
            ).fetchone()["id"]
            reason_id = db.execute(
                """
                SELECT id FROM exclusion_reasons
                WHERE id_review = 1 AND is_active = 1
                ORDER BY hierarchy LIMIT 1
                """
            ).fetchone()["id"]

        def logged_client(name):
            client = self.app.test_client()
            response = client.post(
                "/1_main.html",
                data={
                    "action": "login",
                    "login_name": name,
                },
                follow_redirects=True,
            )
            self.assertEqual(response.status_code, 200)
            return client

        alex = logged_client("Alex Morgan")
        sam = logged_client("Sam Rivera")
        priya = logged_client("Priya Shah")

        first_alex = alex.post(
            "/1_first_screening.html",
            data={
                "study_id": first_study_id,
                "decision": "yes",
                "notes": "Relevant population and intervention.",
            },
        )
        self.assertEqual(first_alex.status_code, 302)

        first_sam = sam.post(
            "/1_first_screening.html",
            data={
                "study_id": first_study_id,
                "decision": "no",
                "notes": "Outcome does not match the protocol.",
            },
        )
        self.assertEqual(first_sam.status_code, 302)

        with self.app.app_context():
            db = get_db()
            study = db.execute(
                """
                SELECT first_screening_included, first_screening_notes
                FROM studies WHERE id_review = 1 AND id = %s
                """,
                (first_study_id,),
            ).fetchone()
            self.assertEqual(study["first_screening_included"], "conflict")
            self.assertIn("Relevant population", study["first_screening_notes"])
            self.assertIn("Outcome does not match", study["first_screening_notes"])
            conflict_count = db.execute(
                """
                SELECT COUNT(*) AS c FROM first_screening_conflicts
                WHERE id_review = 1 AND id_study = %s
                """,
                (first_study_id,),
            ).fetchone()["c"]
            self.assertEqual(conflict_count, 2)

        first_resolution = priya.post(
            "/1_first_screening_conflicts.html",
            data={
                "study_id": first_study_id,
                "final_decision": "yes",
                "notes": "Resolved after discussion.",
            },
        )
        self.assertEqual(first_resolution.status_code, 302)

        second_alex = alex.post(
            "/1_second_screening.html",
            data={
                "study_id": second_study_id,
                "action": "include",
                "notes": "Full text meets the criteria.",
                "show": "with_pdf",
            },
        )
        self.assertEqual(second_alex.status_code, 302)

        second_sam = sam.post(
            "/1_second_screening.html",
            data={
                "study_id": second_study_id,
                "action": "exclude",
                "reason_id": reason_id,
                "notes": "Exclude using the protocol hierarchy.",
                "show": "with_pdf",
            },
        )
        self.assertEqual(second_sam.status_code, 302)

        with self.app.app_context():
            db = get_db()
            study = db.execute(
                """
                SELECT second_screening_included, second_screening_notes
                FROM studies WHERE id_review = 1 AND id = %s
                """,
                (second_study_id,),
            ).fetchone()
            self.assertEqual(study["second_screening_included"], "conflict")
            self.assertIn("Full text meets", study["second_screening_notes"])
            self.assertIn("protocol hierarchy", study["second_screening_notes"])
            conflict_count = db.execute(
                """
                SELECT COUNT(*) AS c FROM second_screening_conflicts
                WHERE id_review = 1 AND id_study = %s
                """,
                (second_study_id,),
            ).fetchone()["c"]
            self.assertEqual(conflict_count, 2)

        second_resolution = priya.post(
            "/1_second_screening_conflicts.html",
            data={
                "study_id": second_study_id,
                "final": "exclude",
                "reason_id": reason_id,
                "notes": "Final exclusion agreed by the team.",
            },
        )
        self.assertEqual(second_resolution.status_code, 302)

        with self.app.app_context():
            db = get_db()
            first_final = db.execute(
                """
                SELECT first_screening_included, first_screening_notes
                FROM studies WHERE id_review = 1 AND id = %s
                """,
                (first_study_id,),
            ).fetchone()
            self.assertEqual(first_final["first_screening_included"], "yes")
            self.assertIn("Resolved after discussion", first_final["first_screening_notes"])

            second_final = db.execute(
                """
                SELECT second_screening_included, exclusion_reason,
                       second_screening_notes
                FROM studies WHERE id_review = 1 AND id = %s
                """,
                (second_study_id,),
            ).fetchone()
            self.assertEqual(second_final["second_screening_included"], "no")
            self.assertEqual(second_final["exclusion_reason"], reason_id)
            self.assertIn("Final exclusion agreed", second_final["second_screening_notes"])

            remaining_conflicts = db.execute(
                """
                SELECT
                  (SELECT COUNT(*) FROM first_screening_conflicts
                   WHERE id_review = 1 AND id_study = %s)
                  +
                  (SELECT COUNT(*) FROM second_screening_conflicts
                   WHERE id_review = 1 AND id_study = %s) AS c
                """,
                (first_study_id, second_study_id),
            ).fetchone()["c"]
            self.assertEqual(remaining_conflicts, 0)

            events = db.execute(
                """
                SELECT phase, event_type, decision, note
                FROM screening_events
                WHERE id_review = 1
                  AND id_study IN (%s,%s)
                ORDER BY id
                """,
                (first_study_id, second_study_id),
            ).fetchall()
            self.assertEqual(len(events), 8)
            self.assertEqual(
                sum(row["event_type"] == "decision" for row in events), 4
            )
            self.assertEqual(
                sum(row["event_type"] == "conflict" for row in events), 2
            )
            self.assertEqual(
                sum(row["event_type"] == "resolution" for row in events), 2
            )

            duplicate_first = db.execute(
                """
                SELECT COUNT(*) AS c FROM first_screening
                WHERE id_review = 1 AND id_study = %s
                GROUP BY id_reviewer
                HAVING COUNT(*) > 1
                """,
                (first_study_id,),
            ).fetchall()
            duplicate_second = db.execute(
                """
                SELECT COUNT(*) AS c FROM second_screening
                WHERE id_review = 1 AND id_study = %s
                GROUP BY id_reviewer
                HAVING COUNT(*) > 1
                """,
                (second_study_id,),
            ).fetchall()
            self.assertEqual(duplicate_first, [])
            self.assertEqual(duplicate_second, [])

        self.client.post("/demo/reset")


if __name__ == "__main__":
    unittest.main()

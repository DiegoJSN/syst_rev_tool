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
                  SUM(CASE WHEN first_screening_included = 'no' THEN 1 ELSE 0 END) AS first_rejected,
                  SUM(CASE WHEN first_screening_included = 'yes'
                            AND second_screening_included IS NULL THEN 1 ELSE 0 END) AS second_pending,
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
            self.assertEqual(counts["first_pending"], 166)
            self.assertEqual(counts["first_rejected"], 54)
            self.assertEqual(counts["second_pending"], 14)
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
                "login_name_1": "Alex Morgan",
                "login_name_2": "Alex Morgan",
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


if __name__ == "__main__":
    unittest.main()

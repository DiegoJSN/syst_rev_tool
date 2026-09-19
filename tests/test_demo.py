import os
import tempfile
import unittest


class DemoSmokeTest(unittest.TestCase):
    EXPECTED_IDS = {
        6, 7, 9, 10, 97, 98, 99, 102, 104, 106, 112, 113,
        116, 117, 118, 119, 120, 121, 126, 128, 129, 130, 131, 134,
        143, 147, 151, 153, 154, 155, 161, 165, 166, 168, 169, 175, 177, 190,
    }

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
                """
                SELECT hierarchy, reason
                FROM exclusion_reasons
                ORDER BY hierarchy
                """
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

    def test_numbered_pdfs_and_phase_examples(self):
        from db import get_db

        with self.app.app_context():
            db = get_db()
            review = db.execute(
                "SELECT id, participants_number FROM review WHERE review_name = %s",
                ("Example 1: Degrowth in agricultural systems",),
            ).fetchone()
            self.assertIsNotNone(review)
            self.assertEqual(review["participants_number"], 6)

            reviewer_count = db.execute(
                "SELECT COUNT(*) AS c FROM reviewers WHERE id_review = %s",
                (review["id"],),
            ).fetchone()["c"]
            self.assertEqual(reviewer_count, 6)

            studies = db.execute(
                """
                SELECT id, file_name, length(file_data) AS file_size,
                       first_screening_included, second_screening_included
                FROM studies
                WHERE id_review = %s
                ORDER BY id
                """,
                (review["id"],),
            ).fetchall()
            self.assertEqual({row["id"] for row in studies}, self.EXPECTED_IDS)
            self.assertTrue(
                all(row["file_name"].startswith(f"{row['id']}_") for row in studies)
            )
            self.assertTrue(all(row["file_size"] > 0 for row in studies))

            first_pending = sum(
                row["first_screening_included"] is None for row in studies
            )
            second_pending = sum(
                row["first_screening_included"] == "yes"
                and row["second_screening_included"] is None
                for row in studies
            )
            to_extract = sum(
                row["first_screening_included"] == "yes"
                and row["second_screening_included"] == "yes"
                for row in studies
            )
            excluded = sum(
                row["first_screening_included"] == "yes"
                and row["second_screening_included"] == "no"
                for row in studies
            )
            self.assertEqual(
                (first_pending, second_pending, to_extract, excluded),
                (7, 7, 6, 18),
            )

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

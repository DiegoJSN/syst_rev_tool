import os
import tempfile
import unittest


class DemoSmokeTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        os.environ["DATABASE_URL"] = f"sqlite:///{self.temp_dir.name}/test.db"
        os.environ["DEMO_MODE"] = "true"
        os.environ["SECRET_KEY"] = "test-only"
        from app import create_app
        self.app = create_app()
        self.app.config.update(TESTING=True)
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_seeded_demo_and_health(self):
        self.assertEqual(self.client.get("/healthz").status_code, 200)
        response = self.client.get("/0_home.html")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Urban green spaces and wellbeing", response.data)
        self.assertIn(b"Portfolio demo", response.data)

    def test_dashboard_and_export(self):
        self.assertEqual(self.client.get("/1_main.html").status_code, 200)
        export = self.client.get("/review/1/export_studies.xlsx")
        self.assertEqual(export.status_code, 200)
        self.assertEqual(export.mimetype, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    def test_create_review(self):
        response = self.client.post("/0_home.html", data={
            "action": "create", "review_name": "Recruiter test",
            "participants": "Reviewer One", "two_reviewer_consensus": "no",
            "delete_password": "temporary", "delete_password_confirm": "temporary",
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Recruiter test", response.data)


if __name__ == "__main__":
    unittest.main()

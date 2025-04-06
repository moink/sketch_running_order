import unittest
from app import app


class TestFlaskAPI(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()  # Set up the Flask test client
        self.app.testing = True

    def test_optimize_success(self):
        request_data = {
            "sketches": [
                {"id": "sketch1", "title": "The Vikings", "cast": ["Erik", "Olaf"]},
                {"id": "sketch2", "title": "Just Erik", "cast": ["Erik"]},
                {"id": "sketch3", "title": "Girls", "cast": ["Caroline", "Michele"]},
                {"id": "sketch4", "title": "Boys", "cast": ["Caroline", "Olaf"]},
            ],
            "constraints": {"anchored": [{"sketch_id": "sketch1", "position": 0}]},
        }
        response = self.app.post("/optimize", json=request_data)
        result = response.get_json()
        self.assertTrue(result["success"])
        self.assertIn("order", result)

    def test_invalid_json(self):
        response = self.app.post("/optimize", data="invalid json")
        result = response.get_json()
        self.assertFalse(result["success"])
        self.assertIn("error", result)


if __name__ == "__main__":
    unittest.main()

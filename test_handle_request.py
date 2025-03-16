import unittest
from unittest.mock import Mock

import requests

from handle_request import convert_request_to_sketches, convert_result_to_json, \
    handle_running_order_request
from running_order import Sketch


class TestRunningOrderRequest(unittest.TestCase):
    """Tests for handling running order optimization requests."""

    def test_successful_request(self):
        """Test handling of valid request."""
        request_data = {
            "sketches": [
                {
                    "id": "sketch1",
                    "title": "The Vikings",
                    "cast": ["Erik", "Olaf"]
                },
                {
                    "id": "sketch2",
                    "title": "The Office",
                    "cast": ["Jim", "Pam"]
                }
            ],
            "constraints": {
                "anchored": [
                    {
                        "sketch_id": "sketch1",
                        "position": 0
                    }
                ]
            }
        }
        mock_request = unittest.mock.Mock()
        mock_request.json.return_value = request_data
        result = handle_running_order_request(mock_request)
        self.assertTrue(result["success"])
        self.assertEqual(len(result["order"]), 2)
        self.assertEqual(result["order"][0]["sketch_id"], "sketch1")  # anchored at 0

    def test_invalid_json(self):
        """Test handling of invalid JSON in request."""
        mock_request = Mock()
        mock_request.json.side_effect = requests.exceptions.JSONDecodeError(
            "Invalid JSON", "", 0
        )
        result = handle_running_order_request(mock_request)
        self.assertFalse(result["success"])
        self.assertIn("error", result)
        self.assertEqual(result["order"], [])

    def test_invalid_request_format(self):
        """Test handling of invalid request format."""
        # Missing required fields
        request_data = {
            "sketches": [
                {
                    "id": "sketch1",
                    # missing title and cast
                }
            ]
        }
        mock_request = unittest.mock.Mock()
        mock_request.json.return_value = request_data
        result = handle_running_order_request(mock_request)
        self.assertFalse(result["success"])
        self.assertIn("error", result)
        self.assertEqual(result["order"], [])

    def test_optimization_failure(self):
        """Test handling of optimization failure."""
        request_data = {
            "sketches": [
                {
                    "id": "sketch1",
                    "title": "The Vikings",
                    "cast": ["Erik", "Olaf"]
                },
                {
                    "id": "sketch2",
                    "title": "The Office",
                    "cast": ["Erik", "Jim"]
                }
            ],
            "constraints": {
                # Create unsolvable situation: sketches must be both before and after each other
                "precedence": [
                    {"before": "sketch1", "after": "sketch2"},
                    {"before": "sketch2", "after": "sketch1"}
                ]
            }
        }
        mock_request = unittest.mock.Mock()
        mock_request.json.return_value = request_data
        result = handle_running_order_request(mock_request)
        self.assertFalse(result["success"])
        self.assertEqual(len(result["order"]), 2)

class TestConvertRequestToSketches(unittest.TestCase):
    """Tests for converting JSON requests to Sketch objects."""

    def test_basic_request(self):
        """Test conversion of simple request with no constraints."""
        request = {
            "sketches": [
                {
                    "id": "sketch1",
                    "title": "The Vikings",
                    "cast": ["Erik", "Olaf"]
                },
                {
                    "id": "sketch2",
                    "title": "The Office",
                    "cast": ["Jim", "Pam"]
                }
            ]
        }
        result = convert_request_to_sketches(request)
        self.assertEqual(len(result.sketches), 2)
        self.assertEqual(result.sketches[0].title, "The Vikings")
        self.assertEqual(result.sketches[0].cast, frozenset(["Erik", "Olaf"]))
        self.assertEqual(result.sketches[1].title, "The Office")
        self.assertEqual(result.sketches[1].cast, frozenset(["Jim", "Pam"]))
        self.assertEqual(len(result.precedence), 0)

    def test_with_constraints(self):
        """Test conversion with both types of constraints."""
        request = {
            "sketches": [
                {
                    "id": "sketch1",
                    "title": "The Vikings",
                    "cast": ["Erik", "Olaf"]
                },
                {
                    "id": "sketch2",
                    "title": "The Office",
                    "cast": ["Jim", "Pam"]
                }
            ],
            "constraints": {
                "anchored": [
                    {
                        "sketch_id": "sketch1",
                        "position": 0
                    }
                ],
                "precedence": [
                    {
                        "before": "sketch1",
                        "after": "sketch2"
                    }
                ]
            }
        }
        result = convert_request_to_sketches(request)
        self.assertEqual(len(result.precedence), 1)
        self.assertEqual(result.precedence[0], (0, 1))  # sketch1 before sketch2

    def test_invalid_request_format(self):
        """Test handling of invalid request formats."""
        # Missing sketches field
        with self.assertRaises(KeyError):
            convert_request_to_sketches({})
        # Missing required sketch fields
        with self.assertRaises(ValueError):
            convert_request_to_sketches({
                "sketches": [
                    {
                        "id": "sketch1",
                        "title": "The Vikings"
                        # missing cast
                    }
                ]
            })
        # Duplicate sketch IDs
        with self.assertRaises(ValueError):
            convert_request_to_sketches({
                "sketches": [
                    {
                        "id": "sketch1",
                        "title": "The Vikings",
                        "cast": ["Erik"]
                    },
                    {
                        "id": "sketch1",  # duplicate ID
                        "title": "The Office",
                        "cast": ["Jim"]
                    }
                ]
            })

    def test_invalid_constraints(self):
        """Test handling of invalid constraints."""
        base_request = {
            "sketches": [
                {
                    "id": "sketch1",
                    "title": "The Vikings",
                    "cast": ["Erik"]
                },
                {
                    "id": "sketch2",
                    "title": "The Office",
                    "cast": ["Jim"]
                }
            ]
        }
        # Invalid anchor position
        with self.assertRaises(ValueError):
            bad_request = base_request.copy()
            bad_request["constraints"] = {
                "anchored": [
                    {
                        "sketch_id": "sketch1",
                        "position": 99  # position out of range
                    }
                ]
            }
            convert_request_to_sketches(bad_request)
        # Unknown sketch ID in anchor
        with self.assertRaises(ValueError):
            bad_request = base_request.copy()
            bad_request["constraints"] = {
                "anchored": [
                    {
                        "sketch_id": "unknown",  # nonexistent ID
                        "position": 0
                    }
                ]
            }
            convert_request_to_sketches(bad_request)
        # Unknown sketch ID in precedence
        with self.assertRaises(ValueError):
            bad_request = base_request.copy()
            bad_request["constraints"] = {
                "precedence": [
                    {
                        "before": "sketch1",
                        "after": "unknown"  # nonexistent ID
                    }
                ]
            }
            convert_request_to_sketches(bad_request)
        # Multiple sketches at same position
        with self.assertRaises(ValueError):
            bad_request = base_request.copy()
            bad_request["constraints"] = {
                "anchored": [
                    {
                        "sketch_id": "sketch1",
                        "position": 0
                    },
                    {
                        "sketch_id": "sketch2",
                        "position": 0  # duplicate position
                    }
                ]
            }
            convert_request_to_sketches(bad_request)


class TestConvertResultToJson(unittest.TestCase):
    """Tests for converting optimization results to JSON."""

    def setUp(self):
        """Create test sketches and ID mapping."""
        self.sketches = [
            Sketch("The Vikings", frozenset(["Erik", "Olaf"])),
            Sketch("The Office", frozenset(["Jim", "Pam"])),
            Sketch("The Band", frozenset(["Erik", "Paul"]))
        ]
        self.id_to_index = {
            "sketch1": 0,
            "sketch2": 1,
            "sketch3": 2
        }

    def test_basic_conversion(self):
        """Test basic conversion of optimization result."""
        order = [1, 2, 0]  # Office, Band, Vikings
        result = convert_result_to_json(
            self.sketches, order, self.id_to_index
        )
        self.assertTrue(result["success"])
        self.assertEqual(len(result["order"]), 3)
        # Check order
        self.assertEqual(result["order"][0]["sketch_id"], "sketch2")
        self.assertEqual(result["order"][0]["title"], "The Office")
        self.assertEqual(result["order"][0]["position"], 0)
        self.assertEqual(result["order"][1]["sketch_id"], "sketch3")
        self.assertEqual(result["order"][2]["sketch_id"], "sketch1")

    def test_cast_overlap_calculation(self):
        """Test that cast overlaps are correctly calculated."""
        # Put sketches with overlapping cast next to each other
        order = [0, 2, 1]  # Vikings(Erik,Olaf), Band(Erik,Paul), Office(Jim,Pam)
        result = convert_result_to_json(
            self.sketches, order, self.id_to_index
        )
        # Erik appears in both Vikings and Band
        self.assertEqual(result["metrics"]["cast_overlaps"], 1)
        # No overlaps in this order
        order = [0, 1, 2]  # Vikings, Office, Band
        result = convert_result_to_json(
            self.sketches, order, self.id_to_index
        )
        self.assertEqual(result["metrics"]["cast_overlaps"], 0)

    def test_failed_optimization(self):
        """Test conversion when optimization fails."""
        order = [0, 1, 2]
        result = convert_result_to_json(
            self.sketches, order, self.id_to_index, success=False
        )
        self.assertFalse(result["success"])
        # Should still include order and metrics
        self.assertIn("order", result)
        self.assertIn("metrics", result)

    def test_empty_result(self):
        """Test conversion with empty result."""
        result = convert_result_to_json([], [], {}, success=False)
        self.assertFalse(result["success"])
        self.assertEqual(len(result["order"]), 0)
        self.assertEqual(result["metrics"]["cast_overlaps"], 0)


if __name__ == '__main__':
    unittest.main()
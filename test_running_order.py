"""Tests for the py module."""

import os.path
import re
import unittest
from argparse import Namespace

from pdf2image import convert_from_path
from PIL import ImageChops

from running_order import (
    get_anchors,
    Sketch,
    SketchOrder,
    make_sketch_overlap_matrix,
)

TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), "test_data")



class TestGetAnchors(unittest.TestCase):
    """Tests for the get_anchors function."""

    def test_two_anchored_one_not(self):
        """Simple test with first and last sketch anchored."""
        sketch1 = Sketch("Jedi Warrior", anchored=True)
        sketch2 = Sketch("I am the boss", anchored=False)
        sketch3 = Sketch("It's just me", anchored=True)
        result = get_anchors([sketch1, sketch2, sketch3])
        expected_result = {0: 0, 2: 2}
        self.assertEqual(expected_result, result)

    def test_no_anchors(self):
        """Simple test with first and last sketch anchored."""
        sketch1 = Sketch("Jedi Warrior", anchored=False)
        sketch2 = Sketch("I am the boss", anchored=False)
        result = get_anchors([sketch1, sketch2])
        expected_result = {}
        self.assertEqual(expected_result, result)


class TestSketchOrder(unittest.TestCase):
    """Tests for the SketchOrder class."""

    def test_equals_true(self):
        """Test the = operator when it should return True."""
        order1 = SketchOrder([0, 1, 2])
        order2 = SketchOrder((0, 1, 2))
        self.assertEqual(order1, order2)

    def test_equals_false(self):
        """Test the = operator when it should return False."""
        order1 = SketchOrder([0, 1, 2])
        order2 = SketchOrder([0, 2, 1])
        self.assertNotEqual(order1, order2)

    def test_equals_different_lengths(self):
        """Test the = operator when the running orders are different lengths."""
        order1 = SketchOrder([0, 1])
        order2 = SketchOrder([0, 1, 2])
        self.assertNotEqual(order1, order2)

    def test_possible_next_states_allowed_nexts_only(self):
        """Test the possible_next_states method with only the allowed_nexts argument."""
        order = SketchOrder([1, 0])
        allowed_nexts = {
            0: {1, 2, 3},
            1: {0, 2},
            2: {1},
        }
        expected_result = {
            SketchOrder([1, 0, 2]),
            SketchOrder([1, 0, 3]),
        }
        result = order.possible_next_states(allowed_nexts, 3)
        self.assertEqual(expected_result, result)

    def test_possible_first_with_anchor(self):
        """Test passing an anchor restricting the first sketch."""
        order = SketchOrder([])
        anchors = {0: 1}
        allowed_nexts = {
            0: {1, 2, 3},
            1: {0, 2},
            2: {1},
        }
        expected_result = {SketchOrder([1])}
        result = order.possible_next_states(allowed_nexts, 3, anchors)
        self.assertEqual(expected_result, result)

    def test_possible_mid_with_anchor(self):
        """Test passing an anchor restricting a later sketch."""
        anchors = {2: 0}
        order = SketchOrder([1, 2])
        allowed_nexts = {2: {0, 3}}
        expected_result = {SketchOrder([1, 2, 0])}
        result = order.possible_next_states(allowed_nexts, 4, anchors)
        self.assertEqual(expected_result, result)

    def test_impossible_mid_with_anchor(self):
        """Test passing an anchor that is impossible to fulfill from this order."""
        anchors = {2: 0}
        order = SketchOrder([1, 2])
        allowed_nexts = {2: {1, 3}}
        expected_result = set()
        result = order.possible_next_states(allowed_nexts, 4, anchors)
        self.assertEqual(expected_result, result)


class TestOverlapMatrix(unittest.TestCase):
    """Tests for make_sketch_overlap_matrix"""

    def test_overlap_matrix_correctness(self):
        """Test that overlap matrix correctly represents cast overlaps."""
        self.sketches = [
            Sketch("Sketch 1", frozenset({"Actor1", "Actor2"})),
            Sketch("Sketch 2", frozenset({"Actor2", "Actor3"})),
            Sketch("Sketch 3", frozenset({"Actor3", "Actor4"})),
            Sketch("Sketch 4", frozenset({"Actor1", "Actor4"})),
        ]
        matrix = make_sketch_overlap_matrix(self.sketches)
        # Check specific overlaps we know should exist
        self.assertEqual(matrix[0, 1], 1)  # Sketches 1&2 share Actor2
        self.assertEqual(matrix[1, 2], 1)  # Sketches 2&3 share Actor3
        self.assertEqual(matrix[2, 3], 1)  # Sketches 3&4 share Actor4
        self.assertEqual(matrix[0, 3], 1)  # Sketches 1&4 share Actor1
        # Check non-overlaps
        self.assertEqual(matrix[0, 2], 0)  # Sketches 1&3 share no actors
        self.assertEqual(matrix[1, 3], 0)  # Sketches 2&4 share no actors



if __name__ == "__main__":
    unittest.main()

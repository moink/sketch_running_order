"""Test for lp_running_order."""

import unittest

import lp_running_order

from running_order import Sketch


class TestGetOverlapMatrix(unittest.TestCase):
    """Tests for the get_overlap_matrix function."""

    def test_get_overlap_matrix(self):
        """Test get_overlap_matrix in a simple case."""
        sketch1 = Sketch(
            "Jedi Warrior", frozenset({"Adrian", "Richie", "Michele"}), True
        )
        sketch2 = Sketch("I am the boss", frozenset({"Theresa", "Rocio"}), False)
        sketch3 = Sketch("It's just me", frozenset({"Adrian"}), False)
        sketches = [sketch1, sketch2, sketch3]
        overlap_matrix = lp_running_order.get_overlap_matrix(sketches)
        expected_result = [
            [3, 0, 1],
            [0, 2, 0],
            [1, 0, 1],
        ]
        self.assertEqual(expected_result, overlap_matrix)


class TestSolve(unittest.TestCase):
    """Tests for solve_sketch_order."""

    def test_solve(self):
        """Test the solve_sketch_order method."""
        overlap_matrix = [[0, 5, 3, 2], [5, 0, 4, 1], [3, 4, 0, 6], [2, 1, 6, 0]]
        fixed_positions = {0: 1, 2: 2}  # Example fixed positions
        # Sketch 1 must appear before sketch 3 in the running order
        precedence_constraints = [(1, 3)]
        result = lp_running_order.solve_sketch_order(
            overlap_matrix, fixed_positions, precedence_constraints
        )
        self.assertEqual([1, 0, 2, 3], result)

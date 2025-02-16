"""Tests for the running_order.py module."""

import unittest
from textwrap import dedent

from running_order import (get_anchors, find_best_order, get_allowable_next_sketches, \
    optimize_running_order, evaluate_cost, parse_csv, Sketch, SketchOrder, \
    find_all_orders, make_sketch_overlap_matrix, greedy_algo)


class TestParseCsv(unittest.TestCase):
    """Tests for the parse_csv function."""

    def test_parse_csv(self):
        """Test three sketches with casts and mix of anchored present and missing."""
        test_text = dedent(
            """\
        Title, Cast, Anchored
        Jedi Warrior, Adrian Richie Michele, True
        I am the boss, Theresa Rocio
        It's just me, Adrian, False
        """
        )  # deliberately left out the 3rd parameter in line 2, it's optional
        sketch1 = Sketch(
            "Jedi Warrior", frozenset({"Adrian", "Richie", "Michele"}), True
        )
        sketch2 = Sketch(
            "I am the boss", frozenset({"Theresa", "Rocio"}), False
        )
        sketch3 = Sketch("It's just me", frozenset({"Adrian"}), False)
        expected_result = [sketch1, sketch2, sketch3]
        result = parse_csv(test_text)
        self.assertEqual(expected_result, result)


class TestOptimizeRunningOrder(unittest.TestCase):
    """Tests for the optimize_running_order function."""

    def test_casting_constraints_only(self):
        """Test optimizing the running order with only casting constraints."""
        sketch1 = Sketch("Jedi Warrior", {"Adrian", "Richie", "Michele"})
        sketch2 = Sketch("I am the boss", {"Theresa", "Rocio"})
        sketch3 = Sketch("It's just me", {"Adrian"})
        result = optimize_running_order([sketch1, sketch2, sketch3])
        expected_result = [sketch3, sketch2, sketch1]
        self.assertEqual(expected_result, result)

    def test_with_anchor(self):
        """Use both casting constraints and an anchored sketch."""
        sketch1 = Sketch(
            "Jedi Warrior", {"Adrian", "Richie", "Michele"}, anchored=True
        )
        sketch2 = Sketch("I am the boss", {"Theresa", "Rocio"})
        sketch3 = Sketch("It's just me", {"Adrian"})
        result = optimize_running_order([sketch1, sketch2, sketch3])
        expected_result = [sketch1, sketch2, sketch3]
        self.assertEqual(expected_result, result)

    def test_with_try_to_keep_order(self):
        """Use casting constraints and an attempt to maintain the given order"""
        sketch1 = Sketch("Jedi Warrior", {"Adrian", "Richie", "Michele"})
        sketch2 = Sketch("I am the boss", {"Theresa", "Rocio"})
        sketch3 = Sketch("It's just me", {"Adrian"})
        result = optimize_running_order(
            [sketch1, sketch2, sketch3], try_to_keep_order=True
        )
        expected_result = [sketch1, sketch2, sketch3]
        self.assertEqual(expected_result, result)


class TestGetAllowableNextSketches(unittest.TestCase):
    """Tests for the get_allowable_next_sketches function."""

    def test_three_sketches(self):
        """Simple test of three sketches with casting."""
        sketch1 = Sketch("Jedi Warrior", {"Adrian", "Richie", "Michele"})
        sketch2 = Sketch("I am the boss", {"Theresa", "Rocio"})
        sketch3 = Sketch("It's just me", {"Adrian"})
        result = get_allowable_next_sketches([sketch1, sketch2, sketch3])
        expected_result = {0: {1}, 1: {0, 2}, 2: {1}}
        self.assertEqual(expected_result, result)


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


class TestFindAllOrders(unittest.TestCase):
    """Tests for the find_all_orders functions."""

    def test_find_all_orders_only_allowed_nexts(self):
        """Test passing only the allowed_nexts argument."""
        allowed_nexts = {
            0: {1},
            1: {0, 2},
            2: {1},
        }
        expected_result = {
            SketchOrder([0, 1, 2]),
            SketchOrder([2, 1, 0]),
        }
        result = find_all_orders(allowed_nexts)
        self.assertEqual(expected_result, result)

    def test_find_all_orders_with_start_anchor(self):
        """Test anchoring the first sketch."""
        allowed_nexts = {
            0: {1},
            1: {0, 2},
            2: {1},
        }
        anchors = {0: 0}
        expected_result = {
            SketchOrder([0, 1, 2]),
        }
        result = find_all_orders(allowed_nexts, anchors)
        self.assertEqual(expected_result, result)

    def test_find_all_orders_with_end_anchor(self):
        """Test anchoring the last sketch."""
        allowed_nexts = {
            0: {1},
            1: {0, 2},
            2: {1},
        }
        anchors = {2: 0}
        expected_result = {
            SketchOrder([2, 1, 0]),
        }
        result = find_all_orders(allowed_nexts, anchors)
        self.assertEqual(expected_result, result)


class TestEvaluateCost(unittest.TestCase):
    """Tests for the evaluate_cost function."""

    def test_perfect_match(self):
        """Test when the candidate is exactly equal to the desired order."""
        desired = [0, 1, 2]
        candidate = SketchOrder([0, 1, 2])
        result = evaluate_cost(candidate, desired)
        self.assertEqual(0, result)

    def test_reverse(self):
        """Test when the candidate is the reverse of the desired order."""
        desired = [2, 1, 0]
        candidate = SketchOrder([0, 1, 2])
        result = evaluate_cost(candidate, desired)
        self.assertEqual(4, result)

    def test_one_away(self):
        """Test when the candidate is one neighbour-swap away from the desired order."""
        desired = [0, 2, 1]
        candidate = SketchOrder([0, 1, 2])
        result = evaluate_cost(candidate, desired)
        self.assertEqual(2, result)


class TestFindBestOrder(unittest.TestCase):
    """Test the find_best_order function."""

    def test_find_best_order_allowed_nexts_only(self):
        """Test passing only the allowed_nexts constraints."""
        allowed_nexts = {
            0: {1},
            1: {0, 2},
            2: {1},
        }
        expected_result = SketchOrder([2, 1, 0])
        result = find_best_order(allowed_nexts)
        self.assertEqual(expected_result, result)

    def test_find_best_order_with_desired(self):
        """Test passing in a desired order."""
        allowed_nexts = {
            0: {1},
            1: {0, 2},
            2: {1},
        }
        desired = [0, 2, 1]
        expected_result = SketchOrder([0, 1, 2])
        result = find_best_order(allowed_nexts, desired=desired)
        self.assertEqual(expected_result, result)

    def test_find_best_order_with_anchors(self):
        """Test passing in an anchor."""
        allowed_nexts = {
            0: {1},
            1: {0, 2},
            2: {1},
        }
        anchors = {0: 0}
        expected_result = SketchOrder([0, 1, 2])
        result = find_best_order(allowed_nexts, anchors=anchors)
        self.assertEqual(expected_result, result)

    def test_find_best_order_with_anchors_and_desired(self):
        """Test passing in both anchors and a desired order."""
        allowed_nexts = {
            0: {1, 2},
            1: {0, 2},
            2: {1},
        }
        anchors = {0: 0}
        desired = [0, 2, 1]
        expected_result = SketchOrder([0, 2, 1])
        result = find_best_order(allowed_nexts, anchors, desired)
        self.assertEqual(expected_result, result)


class TestGreedyAlgorithm(unittest.TestCase):
    """Tests for the greedy algorithm and related functions."""

    def setUp(self):
        """Create test sketches with known overlaps."""
        self.sketches = [
            Sketch("Sketch 1", frozenset({"Actor1", "Actor2"})),
            Sketch("Sketch 2", frozenset({"Actor2", "Actor3"})),
            Sketch("Sketch 3", frozenset({"Actor3", "Actor4"})),
            Sketch("Sketch 4", frozenset({"Actor1", "Actor4"}))
        ]
        self.overlap_matrix = make_sketch_overlap_matrix(self.sketches)

    def test_greedy_algo_reduces_overlap(self):
        """Test that greedy algorithm reduces cast overlap."""
        # Start with worst possible order - maximum overlaps
        initial_order = SketchOrder([0, 1, 2, 3])
        initial_overlap = sum(
            self.overlap_matrix[i, j]
            for i, j in zip(initial_order.order, initial_order.order[1:])
        )

        optimized = greedy_algo(self.overlap_matrix, initial_order)
        final_overlap = sum(
            self.overlap_matrix[i, j]
            for i, j in zip(optimized.order, optimized.order[1:])
        )

        self.assertLess(
            final_overlap,
            initial_overlap,
            "Greedy algorithm should reduce cast overlap"
        )

    def test_greedy_algo_with_desired_order(self):
        """Test that desired order is used as tiebreaker."""
        initial_order = SketchOrder([0, 1, 2, 3])
        desired_order = [3, 2, 1, 0]

        # Run without desired order
        result1 = greedy_algo(self.overlap_matrix, initial_order)
        # Run with desired order
        result2 = greedy_algo(self.overlap_matrix, initial_order, desired_order)

        # Both should have same overlap
        overlap1 = sum(
            self.overlap_matrix[i, j]
            for i, j in zip(result1.order, result1.order[1:])
        )
        overlap2 = sum(
            self.overlap_matrix[i, j]
            for i, j in zip(result2.order, result2.order[1:])
        )
        self.assertEqual(overlap1, overlap2)

        # But result2 should be closer to desired order
        dist1 = evaluate_cost(result1, desired_order)
        dist2 = evaluate_cost(result2, desired_order)
        self.assertLessEqual(
            dist2,
            dist1,
            "Solution with desired order should be no further from desired order"
        )

    def test_overlap_matrix_correctness(self):
        """Test that overlap matrix correctly represents cast overlaps."""
        matrix = self.overlap_matrix

        # Check specific overlaps we know should exist
        self.assertEqual(matrix[0, 1], 1)  # Sketches 1&2 share Actor2
        self.assertEqual(matrix[1, 2], 1)  # Sketches 2&3 share Actor3
        self.assertEqual(matrix[2, 3], 1)  # Sketches 3&4 share Actor4
        self.assertEqual(matrix[0, 3], 1)  # Sketches 1&4 share Actor1

        # Check non-overlaps
        self.assertEqual(matrix[0, 2], 0)  # Sketches 1&3 share no actors
        self.assertEqual(matrix[1, 3], 0)  # Sketches 2&4 share no actors

    def test_greedy_algo_stability(self):
        """Test that greedy algorithm is stable with no better solution."""
        # Create an already-optimal order
        optimal_order = SketchOrder([0, 2, 1, 3])

        result = greedy_algo(self.overlap_matrix, optimal_order)

        # Should return same overlap as input
        initial_overlap = sum(
            self.overlap_matrix[i, j]
            for i, j in zip(optimal_order.order, optimal_order.order[1:])
        )
        final_overlap = sum(
            self.overlap_matrix[i, j]
            for i, j in zip(result.order, result.order[1:])
        )
        self.assertEqual(
            final_overlap,
            initial_overlap,
            "Greedy algorithm should not worsen an optimal solution"
        )


if __name__ == "__main__":
    unittest.main()

"""Tests for the running_order.py module."""

import unittest
from textwrap import dedent

import running_order


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
        sketch1 = running_order.Sketch(
            "Jedi Warrior", frozenset({"Adrian", "Richie", "Michele"}), True
        )
        sketch2 = running_order.Sketch(
            "I am the boss", frozenset({"Theresa", "Rocio"}), False
        )
        sketch3 = running_order.Sketch("It's just me", frozenset({"Adrian"}), False)
        expected_result = [sketch1, sketch2, sketch3]
        result = running_order.parse_csv(test_text)
        self.assertEqual(expected_result, result)


class TestOptimizeRunningOrder(unittest.TestCase):
    """Tests for the optimize_running_order function."""

    def test_casting_constraints_only(self):
        """Test optimizing the running order with only casting constraints."""
        sketch1 = running_order.Sketch("Jedi Warrior", {"Adrian", "Richie", "Michele"})
        sketch2 = running_order.Sketch("I am the boss", {"Theresa", "Rocio"})
        sketch3 = running_order.Sketch("It's just me", {"Adrian"})
        result = running_order.optimize_running_order([sketch1, sketch2, sketch3])
        expected_result = [sketch3, sketch2, sketch1]
        self.assertEqual(expected_result, result)

    def test_with_anchor(self):
        """Use both casting constraints and an anchored sketch."""
        sketch1 = running_order.Sketch(
            "Jedi Warrior", {"Adrian", "Richie", "Michele"}, anchored=True
        )
        sketch2 = running_order.Sketch("I am the boss", {"Theresa", "Rocio"})
        sketch3 = running_order.Sketch("It's just me", {"Adrian"})
        result = running_order.optimize_running_order([sketch1, sketch2, sketch3])
        expected_result = [sketch1, sketch2, sketch3]
        self.assertEqual(expected_result, result)

    def test_with_try_to_keep_order(self):
        """Use casting constraints and an attempt to maintain the given order"""
        sketch1 = running_order.Sketch("Jedi Warrior", {"Adrian", "Richie", "Michele"})
        sketch2 = running_order.Sketch("I am the boss", {"Theresa", "Rocio"})
        sketch3 = running_order.Sketch("It's just me", {"Adrian"})
        result = running_order.optimize_running_order(
            [sketch1, sketch2, sketch3], try_to_keep_order=True
        )
        expected_result = [sketch1, sketch2, sketch3]
        self.assertEqual(expected_result, result)


class TestGetAllowableNextSketches(unittest.TestCase):
    """Tests for the get_allowable_next_sketches function."""

    def test_three_sketches(self):
        """Simple test of three sketches with casting."""
        sketch1 = running_order.Sketch("Jedi Warrior", {"Adrian", "Richie", "Michele"})
        sketch2 = running_order.Sketch("I am the boss", {"Theresa", "Rocio"})
        sketch3 = running_order.Sketch("It's just me", {"Adrian"})
        result = running_order.get_allowable_next_sketches([sketch1, sketch2, sketch3])
        expected_result = {0: {1}, 1: {0, 2}, 2: {1}}
        self.assertEqual(expected_result, result)


class TestGetAnchors(unittest.TestCase):
    """Tests for the get_anchors function."""

    def test_two_anchored_one_not(self):
        """Simple test with first and last sketch anchored."""
        sketch1 = running_order.Sketch("Jedi Warrior", anchored=True)
        sketch2 = running_order.Sketch("I am the boss", anchored=False)
        sketch3 = running_order.Sketch("It's just me", anchored=True)
        result = running_order.get_anchors([sketch1, sketch2, sketch3])
        expected_result = {0: 0, 2: 2}
        self.assertEqual(expected_result, result)

    def test_no_anchors(self):
        """Simple test with first and last sketch anchored."""
        sketch1 = running_order.Sketch("Jedi Warrior", anchored=False)
        sketch2 = running_order.Sketch("I am the boss", anchored=False)
        result = running_order.get_anchors([sketch1, sketch2])
        expected_result = {}
        self.assertEqual(expected_result, result)


class TestSketchOrder(unittest.TestCase):
    """Tests for the SketchOrder class."""

    def test_equals_true(self):
        """Test the = operator when it should return True."""
        order1 = running_order.SketchOrder([0, 1, 2])
        order2 = running_order.SketchOrder((0, 1, 2))
        self.assertEqual(order1, order2)

    def test_equals_false(self):
        """Test the = operator when it should return False."""
        order1 = running_order.SketchOrder([0, 1, 2])
        order2 = running_order.SketchOrder([0, 2, 1])
        self.assertNotEqual(order1, order2)

    def test_equals_different_lengths(self):
        """Test the = operator when the running orders are different lengths."""
        order1 = running_order.SketchOrder([0, 1])
        order2 = running_order.SketchOrder([0, 1, 2])
        self.assertNotEqual(order1, order2)

    def test_possible_next_states_allowed_nexts_only(self):
        """Test the possible_next_states method with only the allowed_nexts argument."""
        order = running_order.SketchOrder([1, 0])
        allowed_nexts = {
            0: {1, 2, 3},
            1: {0, 2},
            2: {1},
        }
        expected_result = {
            running_order.SketchOrder([1, 0, 2]),
            running_order.SketchOrder([1, 0, 3]),
        }
        result = order.possible_next_states(allowed_nexts, 3)
        self.assertEqual(expected_result, result)

    def test_possible_first_with_anchor(self):
        """Test passing an anchor restricting the first sketch."""
        order = running_order.SketchOrder([])
        anchors = {0: 1}
        allowed_nexts = {
            0: {1, 2, 3},
            1: {0, 2},
            2: {1},
        }
        expected_result = {running_order.SketchOrder([1])}
        result = order.possible_next_states(allowed_nexts, 3, anchors)
        self.assertEqual(expected_result, result)

    def test_possible_mid_with_anchor(self):
        """Test passing an anchor restricting a later sketch."""
        anchors = {2: 0}
        order = running_order.SketchOrder([1, 2])
        allowed_nexts = {2: {0, 3}}
        expected_result = {running_order.SketchOrder([1, 2, 0])}
        result = order.possible_next_states(allowed_nexts, 4, anchors)
        self.assertEqual(expected_result, result)

    def test_impossible_mid_with_anchor(self):
        """Test passing an anchor that is impossible to fulfill from this order."""
        anchors = {2: 0}
        order = running_order.SketchOrder([1, 2])
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
            running_order.SketchOrder([0, 1, 2]),
            running_order.SketchOrder([2, 1, 0]),
        }
        result = running_order.find_all_orders(allowed_nexts)
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
            running_order.SketchOrder([0, 1, 2]),
        }
        result = running_order.find_all_orders(allowed_nexts, anchors)
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
            running_order.SketchOrder([2, 1, 0]),
        }
        result = running_order.find_all_orders(allowed_nexts, anchors)
        self.assertEqual(expected_result, result)


class TestEvaluateCost(unittest.TestCase):
    """Tests for the evaluate_cost function."""

    def test_perfect_match(self):
        """Test when the candidate is exactly equal to the desired order."""
        desired = [0, 1, 2]
        candidate = running_order.SketchOrder([0, 1, 2])
        result = running_order.evaluate_cost(candidate, desired)
        self.assertEqual(0, result)

    def test_reverse(self):
        """Test when the candidate is the reverse of the desired order."""
        desired = [2, 1, 0]
        candidate = running_order.SketchOrder([0, 1, 2])
        result = running_order.evaluate_cost(candidate, desired)
        self.assertEqual(4, result)

    def test_one_away(self):
        """Test when the candidate is one neighbour-swap away from the desired order."""
        desired = [0, 2, 1]
        candidate = running_order.SketchOrder([0, 1, 2])
        result = running_order.evaluate_cost(candidate, desired)
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
        expected_result = running_order.SketchOrder([2, 1, 0])
        result = running_order.find_best_order(allowed_nexts)
        self.assertEqual(expected_result, result)

    def test_find_best_order_with_desired(self):
        """Test passing in a desired order."""
        allowed_nexts = {
            0: {1},
            1: {0, 2},
            2: {1},
        }
        desired = [0, 2, 1]
        expected_result = running_order.SketchOrder([0, 1, 2])
        result = running_order.find_best_order(allowed_nexts, desired=desired)
        self.assertEqual(expected_result, result)

    def test_find_best_order_with_anchors(self):
        """Test passing in an anchor."""
        allowed_nexts = {
            0: {1},
            1: {0, 2},
            2: {1},
        }
        anchors = {0: 0}
        expected_result = running_order.SketchOrder([0, 1, 2])
        result = running_order.find_best_order(allowed_nexts, anchors=anchors)
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
        expected_result = running_order.SketchOrder([0, 2, 1])
        result = running_order.find_best_order(allowed_nexts, anchors, desired)
        self.assertEqual(expected_result, result)


if __name__ == "__main__":
    unittest.main()

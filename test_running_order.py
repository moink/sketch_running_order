import unittest

import running_order


class TestGetAllowableNextSketches(unittest.TestCase):
    def test_three_sketches(self):
        sketch1 = running_order.Sketch("Jedi Warrior", {"Adrian", "Richie", "Michele"})
        sketch2 = running_order.Sketch("I am the boss", {"Theresa", "Rocio"})
        sketch3 = running_order.Sketch("It's just me", {"Adrian"})
        result = running_order.get_allowable_next_sketches([sketch1, sketch2, sketch3])
        expected_result = {
            0: {1},
            1: {0, 2},
            2: {1},
        }
        self.assertEqual(expected_result, result)


class TestSketchOrder(unittest.TestCase):

    def test_equals_true(self):
        order1 = running_order.SketchOrder([0, 1, 2])
        order2 = running_order.SketchOrder((0, 1, 2))
        self.assertEqual(order1, order2)

    def test_equals_false(self):
        order1 = running_order.SketchOrder([0, 1, 2])
        order2 = running_order.SketchOrder([0, 2, 1])
        self.assertNotEqual(order1, order2)

    def test_equals_different_lengths(self):
        order1 = running_order.SketchOrder([0, 1])
        order2 = running_order.SketchOrder([0, 1, 2])
        self.assertNotEqual(order1, order2)

    def test_possible_next_states(self):
        order = running_order.SketchOrder([1, 0])
        allowed_nexts = {
            0: {1, 2, 3},
            1: {0, 2},
            2: {1},
        }
        expected_result = {
            running_order.SketchOrder([1, 0, 2]),
            running_order.SketchOrder([1, 0, 3])
        }
        result = order.possible_next_states(allowed_nexts, 3)
        self.assertEqual(expected_result, result)

    def test_possible_first_with_anchor(self):
        order = running_order.SketchOrder([])
        anchors = {0: 1}
        allowed_nexts = {
            0: {1, 2, 3},
            1: {0, 2},
            2: {1},
        }
        expected_result = {
            running_order.SketchOrder([1])
        }
        result = order.possible_next_states(allowed_nexts, 3, anchors)
        self.assertEqual(expected_result, result)

    def test_possible_mid_with_anchor(self):
        anchors = {2: 0}
        order = running_order.SketchOrder([1, 2])
        allowed_nexts = {2: {0, 3}}
        expected_result = {
            running_order.SketchOrder([1, 2, 0])
        }
        result = order.possible_next_states(allowed_nexts, 4, anchors)
        self.assertEqual(expected_result, result)

    def test_impossible_mid_with_anchor(self):
        anchors = {2: 0}
        order = running_order.SketchOrder([1, 2])
        allowed_nexts = {2: {1, 3}}
        expected_result = set()
        result = order.possible_next_states(allowed_nexts, 4, anchors)
        self.assertEqual(expected_result, result)


class TestFindAllOrders(unittest.TestCase):
    def test_find_all_orders(self):
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

    def test_perfect_match(self):
        desired = [0, 1, 2]
        candidate = running_order.SketchOrder([0, 1, 2])
        result = running_order.evaluate_cost(candidate, desired)
        self.assertEqual(0, result)

    def test_reverse(self):
        desired = [2, 1, 0]
        candidate = running_order.SketchOrder([0, 1, 2])
        result = running_order.evaluate_cost(candidate, desired)
        self.assertEqual(4, result)

    def test_one_away(self):
        desired = [0, 2, 1]
        candidate = running_order.SketchOrder([0, 1, 2])
        result = running_order.evaluate_cost(candidate, desired)
        self.assertEqual(2, result)


class TestFindBestOrder(unittest.TestCase):

    def test_find_best_order_constraints_only(self):
        allowed_nexts = {
            0: {1},
            1: {0, 2},
            2: {1},
        }
        expected_result = running_order.SketchOrder([2, 1, 0])
        result = running_order.find_best_order(allowed_nexts)
        self.assertEqual(expected_result, result)

    def test_find_best_order_with_desired(self):
        allowed_nexts = {
            0: {1},
            1: {0, 2},
            2: {1},
        }
        desired = [0, 2, 1]
        expected_result = running_order.SketchOrder([0, 1, 2])
        result = running_order.find_best_order(allowed_nexts, desired)
        self.assertEqual(expected_result, result)

    def test_find_best_order_with_anchors(self):
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
        allowed_nexts = {
            0: {1, 2},
            1: {0, 2},
            2: {1},
        }
        anchors = {0: 0}
        desired = [0, 2, 1]
        expected_result = running_order.SketchOrder([0, 2, 1])
        result = running_order.find_best_order(allowed_nexts, desired, anchors)
        self.assertEqual(expected_result, result)


if __name__ == '__main__':
    unittest.main()

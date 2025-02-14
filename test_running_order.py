import unittest

import running_order


class TestGetAllowableNextSketches(unittest.TestCase):
    def test_three_sketches(self):
        sketch1 = running_order.Sketch("Jedi Warrior", {"Adrian", "Richie", "Michelle"})
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


if __name__ == '__main__':
    unittest.main()

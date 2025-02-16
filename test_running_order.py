"""Tests for the running_order.py module."""

import os.path
import re
import unittest
from argparse import Namespace
from textwrap import dedent

from running_order import (get_anchors, find_best_order, get_allowable_next_sketches, \
    optimize_running_order, evaluate_cost, parse_csv, Sketch, SketchOrder, \
    find_all_orders, make_sketch_overlap_matrix, greedy_algo)
from pdf2image import convert_from_path
from PIL import ImageChops

import running_order

TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), "test_data")


class FileCleanupTestCase(unittest.TestCase):
    """Base class for tests that need to clean up output files."""

    output_filename = os.path.join(TEST_DATA_DIR, "test_output.pdf")

    def delete_written_file_if_exists(self):
        """Delete the test output file if it exists before running tests."""
        if os.path.exists(self.output_filename):
            os.remove(self.output_filename)

    def setUp(self):
        """Set up test by ensuring output file doesn't exist."""
        self.delete_written_file_if_exists()

    def tearDown(self):
        """Clean up by deleting output file."""
        self.delete_written_file_if_exists()


class TestMain(FileCleanupTestCase):
    """Tests for the main function."""

    def test_main(self):
        """Test the main function using test data from CSV file."""
        test_input = os.path.join(TEST_DATA_DIR, "main_test_input.csv")
        expected_output = os.path.join(TEST_DATA_DIR, "expected_main_output.pdf")
        running_order.main(["-f", test_input, "-o", self.output_filename])
        self.assertTrue(pdfs_look_same(expected_output, self.output_filename))


class TestReadAndValidateCSV(unittest.TestCase):
    """Tests for the read_and_validate_csv function."""

    @classmethod
    def tearDownClass(cls):
        """Clean up any test files we created."""
        for filename in ["empty.csv", "bad_header.csv", "inconsistent.csv"]:
            test_file = os.path.join(TEST_DATA_DIR, filename)
            if os.path.exists(test_file):
                os.remove(test_file)

    def test_valid_file(self):
        """Test reading a valid file with header and data."""
        test_file = os.path.join(TEST_DATA_DIR, "good_file.csv")
        result = running_order.read_and_validate_csv(test_file, ",")
        self.assertGreater(len(result), 0)

    def test_empty_file(self):
        """Test that an empty file raises an error."""
        test_file = os.path.join(TEST_DATA_DIR, "empty.csv")
        with open(test_file, "w", encoding="utf-8") as f:
            pass
        expected_msg = "Input file is empty"
        with self.assertRaisesRegex(ValueError, expected_msg):
            running_order.read_and_validate_csv(test_file, ",")

    def test_wrong_column_count_header(self):
        """Test that wrong number of columns in header raises error."""
        test_file = os.path.join(TEST_DATA_DIR, "bad_header.csv")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("Title Cast Anchored\n")
            f.write("Sketch 1, Cast 1, True\n")
        expected_msg = re.escape("Expected 2 or 3 columns at line 1, found 1.")
        with self.assertRaisesRegex(ValueError, expected_msg):
            running_order.read_and_validate_csv(test_file, ",")

    def test_inconsistent_columns(self):
        """Test that inconsistent column counts raise error."""
        test_file = os.path.join(TEST_DATA_DIR, "inconsistent.csv")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("Title, Cast, Anchored\n")
            f.write("Sketch 1, Cast 1\n")
            f.write("Sketch 2, Cast 2, True, Extra\n")
        expected_msg = re.escape("Expected 2 or 3 columns at line 3, found 4.")
        with self.assertRaisesRegex(ValueError, expected_msg):
            running_order.read_and_validate_csv(test_file, ",")

    def test_missing_file(self):
        """Test that a missing file raises FileNotFoundError."""
        test_file = os.path.join(TEST_DATA_DIR, "nonexistent.csv")
        with self.assertRaises(FileNotFoundError):
            running_order.read_and_validate_csv(test_file, ",")


class TestWriteRunningOrderToPDF(FileCleanupTestCase):
    """Tests for the generate_output function."""

    def test_write_running_order_to_pdf(self):
        """Test a simple version with three sketches."""
        sketch1 = running_order.Sketch(
            "Jedi Warrior", frozenset({"Adrian", "Richie", "Michele"}), True
        )
        sketch2 = running_order.Sketch(
            "I am the boss", frozenset({"Theresa", "Rocio"}), False
        )
        sketch3 = running_order.Sketch("It's just me", frozenset({"Adrian"}), False)
        order = [sketch1, sketch2, sketch3]
        expected_filename = os.path.join(
            TEST_DATA_DIR, "expected_output_test_output.pdf"
        )
        running_order.write_running_order_to_pdf(order, self.output_filename)
        self.assertTrue(pdfs_look_same(expected_filename, self.output_filename))


def pdfs_look_same(pdf1, pdf2, dpi=150):
    """Return True if the PDFs have the same appearance."""
    images1 = convert_from_path(pdf1, dpi=dpi)
    images2 = convert_from_path(pdf2, dpi=dpi)
    if len(images1) != len(images2):
        return False
    for img1, img2 in zip(images1, images2):
        diff = ImageChops.difference(img1, img2)
        bbox = diff.getbbox()
        if bbox is not None:
            return False
    return True


class TestParseCommandLineArgs(unittest.TestCase):
    """Tests for the parse_command_line_args function."""

    def test_parse_no_args(self):
        """Test when no arguments are passed."""
        expected_result = Namespace(
            filename="casting.csv",
            output_filename="running_order.pdf",
            dont_try_to_keep_order=False,
            column_sep=",",
            cast_sep=" ",
        )
        result = running_order.parse_args([])
        self.assertEqual(expected_result, result)

    def test_parse_filename(self):
        """Test when only passing the filename."""
        expected_result = Namespace(
            filename="poop.csv",
            output_filename="running_order.pdf",
            dont_try_to_keep_order=False,
            column_sep=",",
            cast_sep=" ",
        )
        result = running_order.parse_args(["-f", "poop.csv"])
        self.assertEqual(expected_result, result)

    def test_parse_dont_try_to_keep_order(self):
        """Test when passing the -d flag."""
        expected_result = Namespace(
            filename="casting.csv",
            output_filename="running_order.pdf",
            dont_try_to_keep_order=True,
            column_sep=",",
            cast_sep=" ",
        )
        result = running_order.parse_args(["-d"])
        self.assertEqual(expected_result, result)

    def test_parse_column_sep(self):
        """Test changing the column separator."""
        expected_result = Namespace(
            filename="casting.csv",
            output_filename="running_order.pdf",
            dont_try_to_keep_order=False,
            column_sep=";",
            cast_sep=" ",
        )
        result = running_order.parse_args(["--column_sep", ";"])
        self.assertEqual(expected_result, result)

    def test_parse_cast_sep(self):
        """Test changing the cast separator."""
        expected_result = Namespace(
            filename="casting.csv",
            output_filename="running_order.pdf",
            dont_try_to_keep_order=False,
            column_sep=",",
            cast_sep=";",
        )
        result = running_order.parse_args(["-c", ";"])
        self.assertEqual(expected_result, result)

    def test_parse_all(self):
        """Test when all CLI arguments are passed."""
        expected_result = Namespace(
            filename="poop.csv",
            output_filename="you're an eight.pdf",
            dont_try_to_keep_order=True,
            column_sep=";",
            cast_sep=",",
        )
        result = running_order.parse_args(
            ["-f", "poop.csv", "-o", "you're an eight.pdf", "-d", "-s", ";", "-c", ","]
        )
        self.assertEqual(expected_result, result)

    def test_raise_if_column_and_cast_sep_the_same(self):
        """Test that an error is raised when column and cast separators are the same."""
        expected_msg = re.escape(
            "Column separator and cast separator cannot be the same character."
        )
        with self.assertRaisesRegex(ValueError, expected_msg):
            running_order.parse_args(["-c", ","])


class TestParseCsv(unittest.TestCase):
    """Tests for the parse_csv function."""

    def test_parse_csv(self):
        """Test three sketches with casts and mix of anchored present and missing."""
        test_lines = [
            "Jedi Warrior, Adrian Richie Michele, True",
            "I am the boss, Theresa Rocio",
            "It's just me, Adrian, False",
        ]
        sketch1 = Sketch(
            "Jedi Warrior", frozenset({"Adrian", "Richie", "Michele"}), True
        )
        sketch2 = Sketch(
            "I am the boss", frozenset({"Theresa", "Rocio"}), False
        )
        sketch3 = Sketch("It's just me", frozenset({"Adrian"}), False)
        expected_result = [sketch1, sketch2, sketch3]
        result = parse_csv(test_lines)
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

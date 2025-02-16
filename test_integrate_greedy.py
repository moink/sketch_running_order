"""Test the greedy algorithm with real show data."""

import unittest
import os
import time
import pandas as pd
import numpy as np
from running_order import (
    Sketch,
    SketchOrder,
    make_sketch_overlap_matrix,
    greedy_algo,
    evaluate_cost
)


class TestGreedyWithShowData(unittest.TestCase):
    """Test greedy algorithm using actual show running order."""

    @classmethod
    def setUpClass(cls):
        """Load the show data from spreadsheet."""
        sketch_casting = pd.read_csv(
            os.path.join(os.path.dirname(__file__),
                "test_data",
                "casting.csv"
            )
        )
        sketch_casting.set_index("title", inplace=True)
        cls.sketches = []
        for row in sketch_casting.iterrows():
            cls.sketches.append(
                Sketch(row[1].name, frozenset(row[1][~row[1].isna()].index))
            )
        cls.original_sketches = cls.sketches.copy()
        cls.sketches = list(np.random.permutation(cls.sketches))
        cls.overlap_matrix = make_sketch_overlap_matrix(cls.sketches)

    def test_greedy_without_original_order(self):
        """Test greedy algorithm without using original order."""
        start_time = time.time()
        candidate = greedy_algo(
            self.overlap_matrix,
            SketchOrder(range(len(self.sketches)))
        )
        initial_overlap = sum(
            self.overlap_matrix[i, j]
            for i, j in zip(range(len(self.sketches)), range(1, len(self.sketches)))
        )
        final_overlap = sum(
            self.overlap_matrix[i, j]
            for i, j in zip(candidate.order, candidate.order[1:])
        )
        distance = evaluate_cost(candidate, range(len(self.sketches)))
        execution_time = time.time() - start_time
        print("Greedy without original order:")
        print(f"Initial overlap: {initial_overlap}")
        print(f"Final overlap: {final_overlap}")
        print(f"Distance from original order: {distance}")
        print(f"Execution time: {execution_time:.2f}s")
        self.assertLess(
            final_overlap,
            initial_overlap,
            "Greedy algorithm should reduce cast overlap"
        )

    def test_greedy_with_original_order(self):
        """Test greedy algorithm using original order as tiebreaker."""
        start_time = time.time()
        candidate = greedy_algo(
            self.overlap_matrix,
            SketchOrder(range(len(self.sketches))),
            range(len(self.sketches))
        )
        initial_overlap = sum(
            self.overlap_matrix[i, j]
            for i, j in zip(range(len(self.sketches)), range(1, len(self.sketches)))
        )
        final_overlap = sum(
            self.overlap_matrix[i, j]
            for i, j in zip(candidate.order, candidate.order[1:])
        )
        distance = evaluate_cost(candidate, range(len(self.sketches)))
        execution_time = time.time() - start_time
        print("Greedy with original order:")
        print(f"Initial overlap: {initial_overlap}")
        print(f"Final overlap: {final_overlap}")
        print(f"Distance from original order: {distance}")
        print(f"Execution time: {execution_time:.2f}s")
        self.assertLess(
            final_overlap,
            initial_overlap,
            "Greedy algorithm should reduce cast overlap"
        )

    def test_multiple_random_starts(self):
        """Test greedy algorithm with multiple random starting points."""
        start_time = time.time()
        best_distance = float('inf')
        best_overlap = float('inf')
        print("Multiple random starts:")
        for i in range(20):
            iter_start = time.time()
            random_start = list(np.random.permutation(len(self.sketches)))
            candidate = greedy_algo(
                self.overlap_matrix,
                SketchOrder(random_start),
                range(len(self.sketches))
            )
            current_overlap = sum(
                self.overlap_matrix[i, j]
                for i, j in zip(candidate.order, candidate.order[1:])
            )
            current_distance = evaluate_cost(candidate, range(len(self.sketches)))
            iter_time = time.time() - iter_start
            best_distance = min(best_distance, current_distance)
            best_overlap = min(best_overlap, current_overlap)

            print(f'Run {i + 1:2d} - Overlap: {current_overlap:2d}, '
                  f'Distance: {current_distance:2d}, '
                  f'Time: {iter_time:.2f}s')
            self.assertGreaterEqual(
                current_overlap,
                0,
                "Cast overlap cannot be negative"
            )
            self.assertGreaterEqual(
                current_distance,
                0,
                "Distance from original order cannot be negative"
            )
        total_time = time.time() - start_time
        print(f'Best overlap achieved: {best_overlap}')
        print(f'Best distance achieved: {best_distance}')
        print(f'Total time: {total_time:.2f}s')
        print(f'Average time per run: {total_time / 20:.2f}s')


if __name__ == "__main__":
    unittest.main()
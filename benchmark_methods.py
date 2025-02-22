"""Benchmark the 3 methods against each other."""
import os
from time import perf_counter

import numpy as np
import pandas as pd

from running_order import (
    Sketch,
    optimize_running_order as dp_method,
    make_sketch_overlap_matrix,
    calc_order_overlap,
    SketchOrder,
    optimize_running_order_greedy,
)
from lp_running_order import optimize_running_order as lp_method

NUM_RUNS = 10


def main() -> None:
    """Benchmark the 3 methods against each other."""
    sketch_casting = pd.read_csv(
        os.path.join(os.path.dirname(__file__), "test_data", "casting.csv")
    ).iloc[:, :18]
    sketch_casting.drop(columns=["Time", "chars", "casted"], inplace=True)
    sketches = []
    for _, row in sketch_casting.iterrows():
        cast = row[1:]
        sketches.append(Sketch(row["title"], frozenset(cast[~cast.isna()].index)))
    algorithms = [
        ("Dynamic Programming", dp_method),
        ("Linear Programming", lp_method),
        ("Greedy Algorithm", optimize_running_order_greedy),
    ]
    cols = [alg[0] for alg in algorithms]
    scores = pd.DataFrame(index=range(NUM_RUNS), columns=cols)
    times = scores.copy()
    for i in range(NUM_RUNS):
        sketches = list(np.random.permutation(sketches))
        overlap_matrix = np.array(make_sketch_overlap_matrix(sketches))
        s = SketchOrder(range(len(sketches)))
        for name, algorithm in algorithms:
            start_time = perf_counter()
            try:
                result = algorithm(sketches)
            except ValueError:
                pass
            else:
                s = SketchOrder(result)
                overlap = calc_order_overlap(overlap_matrix, s)
                scores.loc[i, name] = overlap
            times.loc[i, name] = perf_counter() - start_time
    print("Times")
    print(times)
    print("Overlap Scores")
    print(scores)


if __name__ == "__main__":
    main()

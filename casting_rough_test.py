#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Feb 15 11:01:37 2025

@author: richie
"""

import pandas as pd
from running_order import *
import numpy as np


# %% Test saved sketches
df = pd.read_excel(
    "/Users/richie/Documents/Admin/Improv/202501 Sketch Bomb/Casting.ods",
    engine="odf",
    sheet_name="RUNNING ORDER",
)

df = df.iloc[:23, 1:]
df.set_index("title", inplace=True)


sketches = []
for row in df.iterrows():
    sketches.append(Sketch(row[1].name, frozenset(row[1][~row[1].isna()].index)))

# Jumble
sketches_original = sketches
sketches = list(np.random.permutation(sketches))

# Get viable candidate
candidate = greedy_algo(
    make_sketch_overlap_matrix(sketches), SketchOrder(range(len(sketches)))
)
print("Distance from original order", evaluate_cost(candidate, range(len(sketches))))


# Get viable candidate using closeness to original order as tie-breaker
# Doesn't always result in a closer candidate despite chasing it stepwise,
# so greedy algorithm appears to be not very well-behaved
# Could just run both versions and pick one of the two
candidate = greedy_algo(
    make_sketch_overlap_matrix(sketches),
    SketchOrder(range(len(sketches))),
    SketchOrder(range(len(sketches))),
)
print("Distance from original order", evaluate_cost(candidate, range(len(sketches))))


# Do a few random permutations but use original final order as tie-breaker
# (cheating a bit but at least simulates how good tie-breaker + random would)
# be at getting back to a target
for i in range(20):
    sketches = sketches_original
    candidate = greedy_algo(make_sketch_overlap_matrix(sketches),
                            SketchOrder(list(np.random.permutation(len(sketches)))),
                            SketchOrder(range(len(sketches))))
    print('Distance from original order', evaluate_cost(candidate, range(len(sketches))))

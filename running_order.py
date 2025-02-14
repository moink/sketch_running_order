import collections
import itertools
from collections import defaultdict
from dataclasses import dataclass


@dataclass
class Sketch:
    title: str
    cast: frozenset[str] = frozenset()
    lateness_weight: float = 0.0


def get_allowable_next_sketches(sketches):
    result = defaultdict(set)
    for ((ind1, sketch1), (ind2, sketch2)) in itertools.product(enumerate(sketches), repeat=2):
        if not sketch1.cast.intersection(sketch2.cast):
            result[ind1].add(ind2)
    return result


class SketchOrder:

    order: list[int]

    def __init__(self, sketches):
        self.order = list(sketches)

    def __hash__(self):
        return hash(tuple(self.order))

    def __repr__(self):
        return f"Sketch Order: {','.join(str(sketch) for sketch in self.order)}"

    def __eq__(self, other):
        if len(self.order) != len(other.order):
            return False
        return all(val1 == val2 for val1, val2 in zip(self.order, other.order))

    def possible_next_states(self, allowed_nexts, num_sketches, anchors=None):
        if anchors is None:
            anchors = {}
        if not self.order:
            try:
                return {SketchOrder([anchors[0]])}
            except KeyError:
                return set(SketchOrder([first_sketch]) for first_sketch in range(num_sketches))
        last_sketch = self.order[-1]
        try:
            next_sketch = anchors[len(self.order)]
        except KeyError:
            allowed_next = allowed_nexts[last_sketch].difference(self.order)
            return {SketchOrder(self.order + [next_sketch]) for next_sketch in allowed_next}
        else:
            if next_sketch in allowed_nexts[last_sketch] and next_sketch not in self.order:
                return {SketchOrder(self.order + [next_sketch])}
            else:
                return set()


def find_all_orders(allowed_nexts, anchors=None):
    num_sketches = len(allowed_nexts)
    allowed_full_orders = set()
    empty_order = SketchOrder([])
    stack = [empty_order]
    discovered = {empty_order}
    while stack:
        partial_order = stack.pop()
        candidates = partial_order.possible_next_states(allowed_nexts, num_sketches, anchors)
        for candidate_one_longer in candidates:
            if len(candidate_one_longer.order) == num_sketches:
                allowed_full_orders.add(candidate_one_longer)
            elif candidate_one_longer not in discovered:
                discovered.add(candidate_one_longer)
                stack.append(candidate_one_longer)
    return allowed_full_orders


def evaluate_cost(candidate, desired):
    desired_spot = {val: ind for ind, val in enumerate(desired)}
    actual_spot = {val: ind for ind, val in enumerate(candidate.order)}
    return sum(abs(actual - desired) for actual, desired in zip(actual_spot.keys(), desired_spot.keys()))


def find_best_order(allowed_nexts, desired=None, anchors=None):
    all_orders = find_all_orders(allowed_nexts, anchors)
    if desired is None:
        best_orders = all_orders
    else:
        costs = {candidate: evaluate_cost(candidate, desired) for candidate in all_orders}
        min_cost = min(costs.values())
        best_orders = {candidate for candidate, cost in costs.items() if cost == min_cost}
    return list(best_orders)[0]

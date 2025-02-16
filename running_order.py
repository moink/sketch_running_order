"""Choose the optimum running order for a sketch show."""

import itertools
from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable, Self
import numpy as np


@dataclass
class Sketch:
    """A sketch close to how it could be imported from a file or a UI.

    Attributes:
        title:
            The title of the sketch for use in printing the running order etc.
        cast:
            The actors who will act in the sketch.
        anchored:
            Whether the sketch is required to stay in its currently assigned position.
    """

    title: str
    cast: frozenset[str] = frozenset()
    anchored: bool = False


def parse_csv(
    text: str, sep: str = ",", cast_sep: str = " ", header: bool = True
) -> list[Sketch]:
    """Parse the text of a csv file to generate a list of sketches.

    Args:
        text:
            Text about sketches. Expected to have three columns: title, cast,
            and anchored.
        sep:
            Separator between the columns
        cast_sep:
            Separator between the cast members in the cast column

    Returns:
        The sketches as a list of populated Sketch entries.
    """
    result = []
    if header:
        first_line = 1
    else:
        first_line = 0
    for line in text.splitlines()[first_line:]:
        if not line.strip():
            continue
        try:
            title, cast, anchored = line.split(sep)
        except ValueError:
            title, cast = line.split(sep)
            anchored = ""
        result.append(
            Sketch(
                title=title,
                cast=frozenset(cast.strip().split(cast_sep)),
                anchored=anchored.lower().strip() == "true",
            )
        )
    return result


def optimize_running_order(
    sketches: list[Sketch], try_to_keep_order=False
) -> list[Sketch]:
    """Optimize the running order of the sketches

    Args:
        sketches:
            Populated sketches
        try_to_keep_order:
            Whether it's desirable to keep the sketches in the given order.

    Returns:
        The sketches in an optimized order.
    """
    allowed_next = get_allowable_next_sketches(sketches)
    anchors = get_anchors(sketches)
    if try_to_keep_order:
        desired = list(range(len(sketches)))
    else:
        desired = None
    solution = find_best_order(allowed_next, anchors, desired)
    return [sketches[place] for place in solution.order]


def get_allowable_next_sketches(sketches: Iterable[Sketch]) -> dict[int, set[int]]:
    """Get all sketches that can follow each sketch in form needed for solving.

    Args:
        sketches:
            The sketches with their casts populated.

    Returns:
        allowed_nexts:
            The key is a sketch number and the value is the set of all sketch numbers
            that are permitted to be immediately after that sketch according the casting
            constraints.
    """
    result = defaultdict(set)
    for (ind1, sketch1), (ind2, sketch2) in itertools.product(
        enumerate(sketches), repeat=2
    ):
        if not sketch1.cast.intersection(sketch2.cast):
            result[ind1].add(ind2)
    return dict(result)


def get_anchors(sketches: Iterable[Sketch]) -> dict[int, int]:
    """Get the anchors in the form needed for solving from the list of sketches.

    Args:
        sketches:
            The sketches with their anchored properties populated.

    Returns:

    """
    return {ind: ind for ind, sketch in enumerate(sketches) if sketch.anchored}


class SketchOrder:
    """Possible partial or full running order of sketches.

    Contains tools for generating longer viable orders starting with this partial
    order.
    """

    order: list[int]

    def __init__(self, sketches: Iterable[int]):
        """Create a sketch order.

        Args:
            sketches: Order (partial or full) of sketches, indexed by integer. For
            example, the empty list [] indicates no sketches in the order as of yet.
            [3] is a partial order with sketch 3 as the only sketch. [4, 2, 15] is a
            partial order with sketch 4 first, 2 second, and 15 third.
        """
        self.order = list(sketches)

    def __hash__(self) -> int:
        """Create a hash of this sketch order."""
        return hash(tuple(self.order))

    def __repr__(self) -> str:
        """Pretty print this sketch order for debugging."""
        return f"Sketch Order: {','.join(str(sketch) for sketch in self.order)}"

    def __eq__(self, other: Self) -> bool:
        """Evaluate equality with another sketch order."""
        if len(self.order) != len(other.order):
            return False
        return all(val1 == val2 for val1, val2 in zip(self.order, other.order))

    def possible_next_states(
        self,
        allowed_nexts: dict[int, set[int]],
        num_sketches: int,
        anchors: dict[int, int] | None = None,
    ) -> set[Self]:
        """Return all viable sketch orders that begin with this sketch order.

        Args:
            allowed_nexts:
                The key is a sketch number and the value is the set of all sketch
                numbers that are permitted to be immediately after that sketch
                according the casting or other constraints.
            num_sketches:
                Total number of sketches in the show
            anchors:
                Sketches that are required to be in a set position in the sequence.
                The key is the position the sketch is required to be in, and the
                value is the sketch number of the sketch required to be there.

        Returns:
            All partial sketch orders one longer than this sketch order that comply
            with the allowed_nexts and anchors constraints.
        """
        if anchors is None:
            anchors = {}
        if not self.order:
            try:
                return {SketchOrder([anchors[0]])}
            except KeyError:
                return set(
                    SketchOrder([first_sketch]) for first_sketch in range(num_sketches)
                )
        last_sketch = self.order[-1]
        try:
            next_sketch = anchors[len(self.order)]
        except KeyError:
            allowed_next = allowed_nexts[last_sketch].difference(self.order)
            return {
                SketchOrder(self.order + [next_sketch]) for next_sketch in allowed_next
            }
        else:
            if (
                next_sketch in allowed_nexts[last_sketch]
                and next_sketch not in self.order
            ):
                return {SketchOrder(self.order + [next_sketch])}
            else:
                return set()


def find_best_order(
    allowed_nexts: dict[int, set[int]],
    anchors: dict[int, int] | None = None,
    desired: list[int] | None = None,
) -> SketchOrder:
    """Find one best order giving constraints and possibly a desired order.

    Args:
        allowed_nexts:
            The key is a sketch number and the value is the set of all sketch
            numbers that are permitted to be immediately after that sketch
            according the casting or other constraints.
        anchors:
            Sketches that are required to be in a set position in the sequence.
            The key is the position the sketch is required to be in, and the
            value is the sketch number of the sketch required to be there.
        desired:
            Preferences for order of sketches if constraints were not active.
            Closeness to this order is considered preferable (returns low costs).
            Example [2, 1, 0] if, ignoring constraints, the user would prefer sketch
            number 2 to be the first sketch, 1 to be the second, and 0 to be the third.

    Returns:
        The running order that follows the constraints that is closest to the desired
        order. If there is more than one such sketch order it will choose one at random.

    Raises:
        IndexError
            If there is no running order that fits the constraints.
    """
    all_orders = find_all_orders(allowed_nexts, anchors)
    if desired is None:
        best_orders = all_orders
    else:
        costs = {
            candidate: evaluate_cost(candidate, desired) for candidate in all_orders
        }
        min_cost = min(costs.values())
        best_orders = {
            candidate for candidate, cost in costs.items() if cost == min_cost
        }
    return list(best_orders)[0]


def find_all_orders(
    allowed_nexts: dict[int, set[int]], anchors: dict[int, int] | None = None
) -> set[SketchOrder]:
    """Find all viable sketch run orders considering the casting constraints and anchors.

    Args:
        allowed_nexts:
            The key is a sketch number and the value is the set of all sketch
            numbers that are permitted to be immediately after that sketch
            according the casting or other constraints.
        anchors:
            Sketches that are required to be in a set position in the sequence.
            The key is the position the sketch is required to be in, and the
            value is the sketch number of the sketch required to be there.

    Returns:
        All full-length (includes all sketches) running orders that follow both sets
        of constraints passed as arguments.
    """
    num_sketches = len(allowed_nexts)
    allowed_full_orders = set()
    empty_order = SketchOrder([])
    stack = [empty_order]
    discovered = {empty_order}
    while stack:
        partial_order = stack.pop()
        candidates = partial_order.possible_next_states(
            allowed_nexts, num_sketches, anchors
        )
        for candidate_one_longer in candidates:
            if len(candidate_one_longer.order) == num_sketches:
                allowed_full_orders.add(candidate_one_longer)
            elif candidate_one_longer not in discovered:
                discovered.add(candidate_one_longer)
                stack.append(candidate_one_longer)
    return allowed_full_orders


def evaluate_cost(candidate: SketchOrder, desired: list[int]) -> int:
    """Get the distance between a sketch order and a desired sketch order.

    Args:
        candidate:
            Candidate full sketch order to be evaluated.
        desired:
            Preferences for order of sketches if constraints were not active.
            Closeness to this order is considered preferable (returns low costs).
            Example [2, 1, 0] if, ignoring constraints, the user would prefer sketch
            number 2 to be the first sketch, 1 to be the second, and 0 to be the third.

    Returns:
        cost:
            Sum of the absolute distances between a sketches position and it's
            desired position.
    """
    desired_spot = {val: ind for ind, val in enumerate(desired)}
    actual_spot = {val: ind for ind, val in enumerate(candidate.order)}
    return sum(
        abs(actual - desired)
        for actual, desired in zip(actual_spot.keys(), desired_spot.keys())
    )


# %% Greedy algorithm
def make_player_incidence_matrix(sketches: Iterable[Sketch]) -> list[list[int]]:
    """Create a matrix showing which players are in which sketches.

    Args:
        sketches: List of sketches with cast information

    Returns:
        A matrix where:
        - Each row represents a player
        - Each column represents a sketch
        - Matrix[i][j] is 1 if player i is in sketch j, 0 otherwise
    """
    all_players = list(set(itertools.chain.from_iterable(x.cast for x in sketches)))
    return [[int(x in y.cast) for y in sketches] for x in all_players]


def make_sketch_overlap_matrix(sketches: Iterable[Sketch]) -> np.ndarray:
    """Create a matrix showing cast overlap between sketches.

    Args:
        sketches: List of sketches with cast information

    Returns:
        A square matrix where entry [i,j] represents the number of
        cast members that sketches i and j have in common
    """
    mat = np.array(make_player_incidence_matrix(sketches))
    return mat.T @ mat


def calc_order_overlap(overlap_mat: np.ndarray, candidate: SketchOrder) -> int:
    """Calculate total cast overlap between adjacent sketches in an order.

    Args:
        overlap_mat: Matrix of cast overlaps between sketches
        candidate: A potential running order to evaluate

    Returns:
        Sum of cast overlaps between consecutive sketches in the order
    """
    return sum(overlap_mat[i, j] for i, j in itertools.pairwise(candidate.order))


def find_best_swap(
    overlap_mat: np.ndarray,
    sketch_order: SketchOrder,
    desired: list[int]
) -> tuple[SketchOrder, int, int]:
    """Find the best swap of two sketches that minimizes cast overlap.

    Args:
        overlap_mat: Matrix of cast overlaps between sketches
        sketch_order: Current running order
        desired: Optional target order to try to maintain

    Returns:
        Tuple of:
        - Best order found after swapping
        - Total cast overlap in that order
        - Cost (distance from desired order, if provided)
    """
    best_overlap = calc_order_overlap(overlap_mat, sketch_order)
    best_order = sketch_order
    best_cost = float("inf")
    if desired is SketchOrder:
        desired = desired.order
    for i in range(len(sketch_order.order) - 1):
        for j in range(i + 1, len(sketch_order.order)):
            new_order = SketchOrder(sketch_order.order.copy())  # Added .copy()
            new_order.order[i], new_order.order[j] = (
                new_order.order[j],
                new_order.order[i],
            )
            new_overlap = calc_order_overlap(overlap_mat, new_order)
            new_cost = (
                best_cost if desired is None else evaluate_cost(new_order, desired)
            )
            if (new_overlap < best_overlap) or (
                (new_overlap == best_overlap) and (new_cost < best_cost)
            ):
                best_overlap = new_overlap
                best_order = new_order
                best_cost = new_cost
    return best_order, best_overlap, best_cost


def greedy_algo(
    overlap_mat: np.ndarray, candidate: SketchOrder, desired: SketchOrder | None = None
) -> SketchOrder:
    """Find a locally optimal running order using a greedy algorithm.

    Repeatedly swaps pairs of sketches to reduce cast overlap between
    adjacent sketches. If a desired order is provided, uses it as a
    tiebreaker when multiple swaps give the same overlap reduction.

    Args:
        overlap_mat: Matrix of cast overlaps between sketches
        candidate: Initial running order
        desired: Optional target order to try to maintain

    Returns:
        A locally optimal running order
    """
    best_overlap = calc_order_overlap(overlap_mat, candidate)
    best_order = candidate
    best_cost = float("inf")  # Changed from 10000000
    while True:
        print(f"Current best overlap: {best_overlap}")
        new_order, new_overlap, new_cost = find_best_swap(
            overlap_mat, best_order, desired
        )
        if (new_overlap < best_overlap) or (
            (new_overlap == best_overlap) and (new_cost < best_cost)
        ):
            best_overlap = new_overlap
            best_order = new_order
            best_cost = new_cost
        else:
            return best_order

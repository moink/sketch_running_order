"""Choose the optimum running order for a sketch show."""

import itertools
import sys
from argparse import ArgumentParser, Namespace, ArgumentDefaultsHelpFormatter
from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable, Self
import numpy as np

from fpdf import FPDF

PROGRESS_UPDATE_FREQUENCY = 10


@dataclass
class PdfConfig:
    """Configuration settings for PDF output formatting.

    Attributes:
        font: Font family to use in the PDF
        title_font_size: Font size for sketch titles
        cast_font_size: Font size for cast lists
        title_cell_height: Height of cells containing titles
        cast_cell_height: Height of cells containing cast lists
        space_between_sketches: Vertical space between sketch entries
    """

    font: str = "Helvetica"
    title_font_size: int = 18
    cast_font_size: int = 12
    title_cell_height: int = 10
    cast_cell_height: int = 8
    space_between_sketches: int = 10


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

    def __post_init__(self):
        """Validate sketch data after initialization."""
        self.cast = frozenset(self.cast)
        if not self.title.strip():
            raise ValueError("Sketch title cannot be empty")


def main(cli_args):
    """Read input file, optimize running order, and write result to pdf."""
    args = parse_args(cli_args)
    lines = read_and_validate_csv(args.filename, args.column_sep)
    sketches = parse_csv(lines, args.column_sep, args.cast_sep)
    order = optimize_running_order(sketches)
    write_running_order_to_pdf(order, args.output_filename)


def parse_args(cli_args: list[str]) -> Namespace:
    """Parse the command-line arguments.

    Args:
        cli_args: List of command-line arguments

    Returns:
        Parsed argument namespace

    Example:
        $ python running_order.py -f input.csv -o output.pdf
        $ python running_order.py --dont_try_to_keep_order -f input.csv
    """
    parser = ArgumentParser(
        description="Find optimal running order for sketch shows.",
        epilog="""
        Example usage:
          %(prog)s -f input.csv -o output.pdf
          %(prog)s --dont_try_to_keep_order -f input.csv
        """,
        formatter_class=ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-f",
        "--filename",
        help="Input CSV file containing sketch data",
        default="casting.csv",
    )
    parser.add_argument(
        "-o",
        "--output_filename",
        help="Output PDF file for the running order",
        default="running_order.pdf",
    )
    parser.add_argument(
        "-d",
        "--dont_try_to_keep_order",
        action="store_true",
        help="Ignore original order when optimizing",
        default=False,
    )
    parser.add_argument(
        "-s", "--column_sep", help="Separator character for CSV columns", default=","
    )
    parser.add_argument(
        "-c", "--cast_sep", help="Separator character for cast lists", default=" "
    )
    args = parser.parse_args(cli_args)
    if args.column_sep == args.cast_sep:
        raise ValueError(
            "Column separator and cast separator cannot be the same character."
        )
    return args


def read_and_validate_csv(filename: str, sep: str) -> list[str]:
    """Read and validate the CSV file format.

    Args:
        filename: Path to the input file
        sep: Separator between the columns

    Returns:
        The lines of the validated file

    Raises:
        ValueError: If file format is invalid
        FileNotFoundError: If file doesn't exist
    """
    with open(filename, encoding="utf-8") as f:
        lines = f.readlines()
    if not lines:
        raise ValueError("Input file is empty")
    for line_num, line in enumerate(lines, 1):
        stripped = line.strip()
        col_count = stripped.count(sep) + 1
        if col_count not in (2, 3):
            raise ValueError(
                f"Expected 2 or 3 columns at line {line_num}, found {col_count}."
            )
    return lines[1:]


def parse_csv(
    lines: list[str], sep: str = ",", cast_sep: str = " ", header: bool = True
) -> list[Sketch]:
    """Parse the lines of a csv file to generate a list of sketches.

    Args:
        lines: Lines from the CSV file, excluding the header
        sep: Separator between the columns
        cast_sep: Separator between the cast members
        header: Whether the text contains a header line

    Returns:
        The sketches as a list of populated Sketch entries.
    """
    result = []
    for line in lines:
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
            example, the empty list [] indicates no sketches in the order as yet.
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
        if next_sketch in allowed_nexts[last_sketch] and next_sketch not in self.order:
            return {SketchOrder(self.order + [next_sketch])}
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
    if not all_orders:
        raise ValueError("No valid running order found that satisfies all constraints")

    if desired is None:
        return next(iter(all_orders))

    return find_closest_to_desired(all_orders, desired)


def find_closest_to_desired(
    orders: set[SketchOrder], desired: list[int]
) -> SketchOrder:
    """Find the order closest to the desired order."""
    costs = {candidate: evaluate_cost(candidate, desired) for candidate in orders}
    min_cost = min(costs.values())
    best_orders = {candidate for candidate, cost in costs.items() if cost == min_cost}
    return next(iter(best_orders))


def find_all_orders(
    allowed_nexts: dict[int, set[int]], anchors: dict[int, int] | None = None
) -> set[SketchOrder]:
    """Find all viable run orders considering the casting constraints and anchors.

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
    progress_interval = max(1, num_sketches // PROGRESS_UPDATE_FREQUENCY)
    last_progress = len(discovered)
    while stack:
        partial_order = stack.pop()
        candidates = partial_order.possible_next_states(
            allowed_nexts, num_sketches, anchors
        )
        if len(discovered) - last_progress >= progress_interval:
            print(f"Processed {len(discovered)} partial orders...")
            last_progress = len(discovered)
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
            Sum of the absolute distances between a sketch's position and its
            desired position.
    """
    desired_spot = {val: ind for ind, val in enumerate(desired)}
    actual_spot = {val: ind for ind, val in enumerate(candidate.order)}
    return sum(
        abs(actual - desired)
        for actual, desired in zip(actual_spot.keys(), desired_spot.keys())
    )


def write_running_order_to_pdf(sketches, filename, config: PdfConfig = PdfConfig()):
    """Write the running order to a formatted PDF file.

    Args:
        sketches: List of sketches to include in the running order
        filename: Name of the output PDF file
        config: PDF formatting configuration settings
    """
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    for i, sketch in enumerate(sketches, start=1):
        pdf.set_font(config.font, style="B", size=config.title_font_size)
        pdf.cell(
            0, config.title_cell_height, f"{i}. {sketch.title}", ln=True, align="C"
        )
        pdf.set_font(config.font, size=config.cast_font_size)
        cast_text = ", ".join(sorted(sketch.cast))
        pdf.cell(0, config.cast_cell_height, cast_text, ln=True, align="C")
        pdf.ln(config.space_between_sketches)
    pdf.output(filename)


if __name__ == "__main__":
    main(sys.argv[1:])


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

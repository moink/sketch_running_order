"""Choose the optimum running order for a sketch show."""

import itertools
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

    def __post_init__(self):
        """Validate sketch data after initialization."""
        self.cast = frozenset(self.cast)
        if not self.title.strip():
            raise ValueError("Sketch title cannot be empty")



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


def get_anchors(sketches: Iterable[Sketch]) -> dict[int, int]:
    """Get sketches that must remain in their current positions.

    Args:
        sketches: The sketches with their anchored properties populated

    Returns:
        A dictionary mapping position indices to sketch indices for all
        sketches that must remain in their current positions

    Example:
        >>> sketch1 = Sketch("Opening", anchored=True)
        >>> sketch2 = Sketch("Middle", anchored=False)
        >>> sketch3 = Sketch("Closing", anchored=True)
        >>> get_anchors([sketch1, sketch2, sketch3])
        {0: 0, 2: 2}  # First and last sketches are anchored to their positions
    """
    anchored = {}
    for i, sketch in enumerate(sketches):
        if sketch.anchored:
            anchored[i] = i
    return anchored
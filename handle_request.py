import dataclasses
from typing import Any

from pydantic.config import JsonDict

from running_order import Sketch, make_sketch_overlap_matrix


@dataclasses.dataclass
class RunningOrderRequest:
    """Container for sketches and constraints from JSON request.

    Attributes:
        sketches
            List of Sketch objects to optimize
        anchored
            Dictionary mapping sketch indices to required positions
        precedence
            List of tuples (before_index, after_index) for ordering constraints
        id_to_index
            Mapping from sketch IDs to indices for JSON conversion
    """
    sketches: list[Sketch]
    precedence: list[tuple[int, int]]  # list of (before_index, after_index)
    id_to_index: dict[str, int]  # for converting back to JSON response


def create_error_response(error_message: str) -> JsonDict:
    """Create JSON error response with consistent structure.

    Args:
        error_message: Description of what went wrong

    Returns:
        Error response in standard JSON format with:
        - success
            False
        - error
            The provided error message
        - order
            Empty list
        - metrics
            Zero cast overlaps
    """
    return {
        "success": False,
        "error": error_message,
        "order": [],
        "metrics": {"cast_overlaps": 0},
    }


def convert_request_to_sketches(request_data: JsonDict) -> RunningOrderRequest:
    """Convert optimization result to JSON response format.

    Args:
        sketches
            Original list of Sketch objects
        order
            List of indices representing optimal order
        id_to_index
            Mapping of sketch IDs to indices from request
        success
            Whether optimization succeeded (False for invalid constraints)

    Returns:
       A RunningOrderRequest that can be passed to optimize_running_order
    """
    id_to_index, sketches = get_sketch_list(request_data)
    anchored = {}
    precedence = []
    if "constraints" in request_data:
        constraints = request_data["constraints"]
        if "anchored" in constraints:
            add_anchors_to_sketches(
                anchored, constraints["anchored"], id_to_index, sketches
            )
        if "precedence" in constraints:
            precedence_constraints = constraints["precedence"]
            get_precedence_constraints(id_to_index, precedence, precedence_constraints)
    return RunningOrderRequest(
        sketches=sketches, precedence=precedence, id_to_index=id_to_index
    )


def get_precedence_constraints(id_to_index, precedence, precedence_constraints):
    """Process precedence constraints from JSON request format.

    Takes sketch ordering constraints from the request and converts them
    to index-based constraints used by the optimizer. Updates the precedence
    list in place.

    Args:
        id_to_index
            Mapping from sketch IDs to indices
        precedence
            List to be populated with (before_index, after_index) pairs
        precedence_constraints
            List of dicts, each with 'before' and 'after' sketch IDs

    Raises:
        ValueError: If constraint format is invalid or references unknown sketch IDs

    Example:
        >>> id_to_index = {"sketch1": 0, "sketch2": 1}
        >>> precedence = []
        >>> constraints = [{"before": "sketch1", "after": "sketch2"}]
        >>> get_precedence_constraints(id_to_index, precedence, constraints)
        >>> precedence
        [(0, 1)]  # sketch1 (index 0) must come before sketch2 (index 1)
    """
    for pred in precedence_constraints:
        if not all(key in pred for key in ["before", "after"]):
            raise ValueError("Precedence constraint missing required fields")
        before_id = pred["before"]
        after_id = pred["after"]
        if before_id not in id_to_index:
            raise ValueError(f"Unknown sketch ID in precedence: {before_id}")
        if after_id not in id_to_index:
            raise ValueError(f"Unknown sketch ID in precedence: {after_id}")
        before_index = id_to_index[before_id]
        after_index = id_to_index[after_id]
        precedence.append((before_index, after_index))


def add_anchors_to_sketches(
    anchored: dict[int, int],
    anchored_constraints: list[dict[str, Any]],
    id_to_index: dict[str, int],
    sketches: list[Sketch],
) -> None:
    """Process anchored constraints from JSON request format.

    Takes position constraints from the request and:
    1. Updates the sketches' anchored property
    2. Adds position mappings to the anchored dictionary

    Args:
        anchored
            Dictionary to be populated with sketch_index -> position mappings
        anchored_constraints
            List of dicts, each with 'sketch_id' and 'position'
        id_to_index
            Mapping from sketch IDs to indices
        sketches
            List of Sketch objects to be updated

    Raises:
        ValueError: If:
            - Constraint format is invalid
            - Sketch ID doesn't exist
            - Position is out of range
            - Multiple sketches assigned to same position

    Example:
        >>> anchored = {}
        >>> constraints = [{"sketch_id": "sketch1", "position": 0}]
        >>> id_to_index = {"sketch1": 0}
        >>> sketches = [Sketch("Title", set(), anchored=False)]
        >>> add_anchors_to_sketches(anchored, constraints, id_to_index, sketches)
        >>> anchored
        {0: 0}  # sketch index 0 is anchored to position 0
        >>> sketches[0].anchored
        True
    """
    for anchor in anchored_constraints:
        if not all(key in anchor for key in ["sketch_id", "position"]):
            raise ValueError("Anchored constraint missing required fields")
        sketch_id = anchor["sketch_id"]
        if sketch_id not in id_to_index:
            raise ValueError(f"Unknown sketch ID in anchor: {sketch_id}")
        sketch_index = id_to_index[sketch_id]
        position = anchor["position"]
        if position < 0 or position >= len(sketches):
            raise ValueError(f"Invalid position in anchor: {position}")
        if position in anchored.values():
            raise ValueError(f"Multiple sketches anchored to position {position}")
        sketches[sketch_index].anchored = True
        anchored[sketch_index] = position


def get_sketch_list(request_data: JsonDict) -> tuple[dict[str, int], list[Sketch]]:
    """Extract and validate sketches from JSON request data.

    Creates Sketch objects from JSON data and builds an ID mapping.
    Each sketch must have a unique ID and contain title and cast information.

    Args:
        request_data: Dictionary containing a 'sketches' list where each sketch
            has 'id', 'title', and 'cast' fields

    Returns:
        A tuple containing:
        - id_to_index: Dictionary mapping sketch IDs to their indices
        - sketches: List of validated Sketch objects

    Raises:
        ValueError: If:
            - Required fields are missing from any sketch
            - Duplicate sketch IDs are found

    Example:
        >>> data = {
        ...     "sketches": [{
        ...         "id": "sketch1",
        ...         "title": "The Office",
        ...         "cast": ["Jim", "Pam"]
        ...     }]
        ... }
        >>> id_map, sketches = get_sketch_list(data)
        >>> id_map
        {'sketch1': 0}
        >>> sketches[0].title
        'The Office'
    """
    sketches = []
    id_to_index = {}
    for i, sketch_data in enumerate(request_data["sketches"]):
        if not all(key in sketch_data for key in ["id", "title", "cast"]):
            raise ValueError(f"Sketch {i} missing required fields")
        sketch_id = sketch_data["id"]
        if sketch_id in id_to_index:
            raise ValueError(f"Duplicate sketch ID: {sketch_id}")
        id_to_index[sketch_id] = i
        sketches.append(
            Sketch(
                title=sketch_data["title"],
                cast=frozenset(sketch_data["cast"]),
                anchored=False,
            )
        )
    return id_to_index, sketches


def convert_result_to_json(
    sketches: list[Sketch],
    order: list[int],
    id_to_index: dict[str, int],
    success: bool = True,
) -> JsonDict:
    """Convert optimization result to JSON response format.

    Args:
        sketches: Original list of Sketch objects
        order: List of indices representing optimal order
        id_to_index: Mapping of sketch IDs to indices from request
        success: Whether optimization succeeded

    Returns:
        Dictionary matching the JSON response format
    """
    index_to_id = {v: k for k, v in id_to_index.items()}
    overlap_matrix = make_sketch_overlap_matrix(sketches)
    overlaps = 0
    if order and len(order) > 1:
        print(f"Order type: {type(order)}, contents: {order}")  # Debug
        print(
            f"Matrix type: {type(overlap_matrix)}, shape: {overlap_matrix.shape}"
        )  # Debug
        for i, j in zip(order[:-1], order[1:]):
            print(f"Index types: {type(i)}, {type(j)}")  # Debug
            i_int = int(i)
            j_int = int(j)
            overlaps += overlap_matrix[i_int, j_int]
    ordered_sketches = []
    for position, sketch_index in enumerate(order):
        ordered_sketches.append(
            {
                "position": position,
                "sketch_id": index_to_id[int(sketch_index)],
                "title": sketches[int(sketch_index)].title,
            }
        )
    return {
        "success": success,
        "order": ordered_sketches,
        "metrics": {"cast_overlaps": int(overlaps)},
    }

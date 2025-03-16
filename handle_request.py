import requests

from dataclasses import dataclass
from typing import Any, TypeAlias

import lp_running_order
from running_order import Sketch, make_sketch_overlap_matrix, calc_order_overlap, \
    SketchOrder

JsonDict: TypeAlias = dict[str, Any]

@dataclass
class RunningOrderRequest:
    """Container for sketches and constraints from JSON request."""
    sketches: list[Sketch]
    precedence: list[tuple[int, int]]  # list of (before_index, after_index)
    id_to_index: dict[str, int]  # for converting back to JSON response


def handle_running_order_request(request: requests.Request) -> JsonDict:
    """Handle running order optimization request.

    Args:
        request: HTTP request containing JSON data

    Returns:
        JSON response with optimization result
    """
    try:
        request_data = request.json()
    except requests.exceptions.JSONDecodeError as e:
        return create_error_response(f"Invalid JSON in request: {str(e)}")
    try:
        converted = convert_request_to_sketches(request_data)
    except (KeyError, ValueError) as e:
        return create_error_response(f"Invalid request format: {str(e)}")
    try:
        optimal_order = lp_running_order.optimize_running_order(
            converted.sketches,
            converted.precedence
        )
    except ValueError as e:
        # Optimization failed but request was valid
        optimal_order = list(range(len(converted.sketches)))
        return convert_result_to_json(
            converted.sketches,
            optimal_order,
            converted.id_to_index,
            success=False
        )
    return convert_result_to_json(
        converted.sketches,
        optimal_order,
        converted.id_to_index,
        success=True
    )


def create_error_response(error_message: str) -> JsonDict:
    """Create JSON error response with consistent structure.

    Args:
        error_message: Description of what went wrong

    Returns:
        Error response in standard JSON format
    """
    return {
        "success": False,
        "error": error_message,
        "order": [],
        "metrics": {"cast_overlaps": 0}
    }


def convert_request_to_sketches(request_data: JsonDict) -> RunningOrderRequest:
    """Convert JSON request format to Sketch objects and constraints.

    Args:
        request_data: Dictionary matching the JSON request format

    Returns:
        RunningOrderRequest containing converted data structures

    Raises:
        ValueError: If request format is invalid
    """
    # Convert sketches and build ID mapping
    id_to_index, sketches = get_sketch_list(request_data)
    # Process constraints
    anchored = {}
    precedence = []
    if "constraints" in request_data:
        constraints = request_data["constraints"]
        if "anchored" in constraints:
            add_anchors_to_sketches(anchored, constraints["anchored"], id_to_index,
                                    sketches)
        # Process precedence constraints
        if "precedence" in constraints:
            precedence_constraints = constraints["precedence"]
            get_precedence_constraints(id_to_index, precedence, precedence_constraints)
    return RunningOrderRequest(
        sketches=sketches,
        precedence=precedence,
        id_to_index=id_to_index
    )


def get_precedence_constraints(id_to_index, precedence, precedence_constraints):
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


def add_anchors_to_sketches(anchored, anchored_constraints, id_to_index, sketches):
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
            raise ValueError(
                f"Multiple sketches anchored to position {position}")
        sketches[sketch_index].anchored = True
        anchored[sketch_index] = position


def get_sketch_list(request_data):
    sketches = []
    id_to_index = {}
    for i, sketch_data in enumerate(request_data["sketches"]):
        if not all(key in sketch_data for key in ["id", "title", "cast"]):
            raise ValueError(f"Sketch {i} missing required fields")
        sketch_id = sketch_data["id"]
        if sketch_id in id_to_index:
            raise ValueError(f"Duplicate sketch ID: {sketch_id}")
        id_to_index[sketch_id] = i
        sketches.append(Sketch(
            title=sketch_data["title"],
            cast=frozenset(sketch_data["cast"]),
            anchored=False
        ))
    return id_to_index, sketches


def convert_result_to_json(
        sketches: list[Sketch],
        order: list[int],
        id_to_index: dict[str, int],
        success: bool = True
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
    # Create reverse mapping from index to ID
    index_to_id = {v: k for k, v in id_to_index.items()}

    # Calculate cast overlaps using existing function
    overlap_matrix = make_sketch_overlap_matrix(sketches)
    overlaps = 0
    # Only calculate overlaps if we have a valid order
    if order and len(order) > 1:
        print(f"Order type: {type(order)}, contents: {order}")  # Debug
        print(
            f"Matrix type: {type(overlap_matrix)}, shape: {overlap_matrix.shape}")  # Debug
        for i, j in zip(order[:-1], order[1:]):
            print(f"Index types: {type(i)}, {type(j)}")  # Debug
            i_int = int(i)
            j_int = int(j)
            overlaps += overlap_matrix[i_int, j_int]

    # Build ordered list of sketches
    ordered_sketches = []
    for position, sketch_index in enumerate(order):
        ordered_sketches.append({
            "position": position,
            "sketch_id": index_to_id[int(sketch_index)],
            "title": sketches[int(sketch_index)].title
        })

    return {
        "success": success,
        "order": ordered_sketches,
        "metrics": {
            "cast_overlaps": int(overlaps)
        }
    }
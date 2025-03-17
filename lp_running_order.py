"""Find sketch running order using linear programming."""
from ortools.sat.python import cp_model

from running_order import Sketch

MAX_SOLVER_TIME_SECONDS = 60


def optimize_running_order(sketches: list[Sketch], precedence_constraints):
    """Optimize the running order using linear programming."""
    overlap_matrix = get_overlap_matrix(sketches)
    anchors = get_anchors(sketches)
    solution = solve_sketch_order(overlap_matrix, anchors, precedence_constraints)
    return solution


def get_overlap_matrix(sketches: list[Sketch]):
    """Get the overlap matrix, the cost of having sketch i and sketch j sequentially."""
    result = []
    for sketch1 in sketches:
        result.append([])
        for sketch2 in sketches:
            result[-1].append(len(sketch1.cast.intersection(sketch2.cast)))
    return result


def solve_sketch_order(
    overlap_matrix, fixed_positions=None, precedence_constraints=None
):
    """Find the optimal order of sketches using linear programing."""
    n = len(overlap_matrix)
    model = cp_model.CpModel()
    # Variables: order[i] represents the position of sketch i in the running order
    order = [model.NewIntVar(0, n - 1, f"order_{i}") for i in range(n)]
    model.AddAllDifferent(order)
    add_fixed_positions(fixed_positions, model, order)
    add_precedence_constraints(model, order, precedence_constraints)
    add_cost_function(model, n, order, overlap_matrix)
    return solve_model(model, order, n)


def add_precedence_constraints(model, order, precedence_constraints):
    """Add the constraints that some sketches have to be before others."""
    if precedence_constraints:
        for before, after in precedence_constraints:
            model.Add(order[before] < order[after])


def add_fixed_positions(fixed_positions, model, order):
    """Add the constraints that anchor or fix sketches in certain positions."""
    if fixed_positions:
        for sketch, pos in fixed_positions.items():
            model.Add(order[sketch] == pos)


def add_cost_function(model, n, order, overlap_matrix):
    """Add the overlap cost function to the linear programming problem."""
    total_overlap = model.NewIntVar(0, sum(map(sum, overlap_matrix)), "total_overlap")
    pairwise_overlap = []
    for i in range(n):
        for j in range(n):
            if i != j:
                is_immediate = model.NewBoolVar(f"is_immediate_{i}_{j}")
                model.Add(order[j] == order[i] + 1).OnlyEnforceIf(is_immediate)
                model.Add(order[j] != order[i] + 1).OnlyEnforceIf(is_immediate.Not())
                overlap_var = model.NewIntVar(
                    0, max(map(max, overlap_matrix)), f"overlap_{i}_{j}"
                )
                model.Add(overlap_var == overlap_matrix[i][j]).OnlyEnforceIf(
                    is_immediate
                )
                model.Add(overlap_var == 0).OnlyEnforceIf(is_immediate.Not())
                pairwise_overlap.append(overlap_var)
    model.Add(total_overlap == sum(pairwise_overlap))
    model.Minimize(total_overlap)


def solve_model(model, order, n):
    """Find a solution to the linear programming problem."""
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = MAX_SOLVER_TIME_SECONDS
    status = solver.Solve(model)
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        final_order = sorted(range(n), key=lambda i: solver.Value(order[i]))
        return final_order
    raise ValueError("No feasible solution found within time limit.")

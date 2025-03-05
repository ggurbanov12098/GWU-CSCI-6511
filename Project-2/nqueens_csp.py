"""
nqueens_csp.py

Top-level "solve_nqueens_csp" function that sets up:
- domains, neighbors
- runs AC3 to prune
- calls backtracking to find solution
"""
from ac3 import AC3
from backtracking import backtracking_search

def solve_nqueens_csp(n):
    """
    Sets up domains and neighbors for an N-Queens CSP,
    enforces AC3, and uses backtracking to find a solution.

    Returns:
        assignment dict {row -> col} if found, else None
    """
    # 1) Prepare domains (each row can be any col from 0..n-1)
    domains = {r: set(range(n)) for r in range(n)}

    # 2) Prepare neighbors (all rows conflict with all others)
    neighbors = {r: [x for x in range(n) if x != r] for r in range(n)}

    # 3) Prepare an assignment
    assignment = {r: None for r in range(n)}

    # 4) AC3 to prune initial domain
    if not AC3(domains, neighbors, n):
        return None  # No solution possible

    # 5) Backtracking
    success = backtracking_search(domains, neighbors, assignment, n)
    return assignment if success else None


def print_solution(assignment, n):
    """
    Prints assignment in a 1-based indexing style
    """
    if assignment is None:
        print("No solution found.")
        return
    print("Solution found!")
    for r in range(n):
        print(f"Row {r+1} -> Column {assignment[r] + 1}")

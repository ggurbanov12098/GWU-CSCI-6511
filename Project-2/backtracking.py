"""
backtracking.py

Implements the backtracking search for N-Queens using MRV, LCV, and AC3 after each assignment.
"""
from ac3 import AC3, conflict
from heuristics import select_unassigned_row, order_domain_values

def backtracking_search(domains, neighbors, assignment, n):
    """
    Backtracking with:
      1) MRV row selection
      2) LCV column ordering
      3) AC3 after each assignment

    Returns True if a full assignment is found, else False
    """
    # Check if complete
    unassigned_rows = [r for r in range(n) if assignment[r] is None]
    if not unassigned_rows:
        return True  # done

    # 1) MRV + tie-break
    row = select_unassigned_row(domains, unassigned_rows, neighbors)

    # 2) LCV
    candidate_cols = order_domain_values(row, domains, neighbors)

    for col in candidate_cols:
        # Quick check of conflict with existing assignments
        if not any(conflict(row, col, r2, assignment[r2])
                   for r2 in range(n) if assignment[r2] is not None):
            # Tentatively assign
            assignment[row] = col

            # Save domain state for backtrack
            saved_domains = {r: set(domains[r]) for r in range(n)}

            # Restrict row's domain to {col}
            domains[row] = {col}

            # AC3 to prune
            if AC3(domains, neighbors, n):
                if backtracking_search(domains, neighbors, assignment, n):
                    return True

            # Backtrack
            assignment[row] = None
            for r in range(n):
                domains[r] = saved_domains[r]

    return False

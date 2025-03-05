"""
ac3.py

Implements the AC3 algorithm for arc consistency, plus any helper it needs.
"""
from collections import deque

def AC3(domains, neighbors, n):
    """
    Enforces arc consistency over all pairs of rows (variables).
    Returns True if successful (no domain is emptied), False otherwise.
    """
    queue = deque()
    # Initialize queue with all arcs
    for r in range(n):
        for nb in neighbors[r]:
            queue.append((r, nb))

    while queue:
        Xi, Xj = queue.popleft()
        if revise(domains, Xi, Xj):
            if len(domains[Xi]) == 0:
                return False
            # If we removed a value from Xi, re-check arcs Xk->Xi
            for Xk in neighbors[Xi]:
                if Xk != Xj:
                    queue.append((Xk, Xi))
    return True

def revise(domains, Xi, Xj):
    """
    Removes values in domains[Xi] that conflict with all values in domains[Xj].
    Returns True if at least one value was removed, otherwise False.
    """
    removed = False
    to_remove = []
    for vi in domains[Xi]:
        # If for every vj in Xj's domain, (vi,vj) is conflict => remove vi
        conflict_with_all = True
        for vj in domains[Xj]:
            if not conflict(Xi, vi, Xj, vj):
                conflict_with_all = False
                break
        if conflict_with_all:
            to_remove.append(vi)

    for val in to_remove:
        domains[Xi].remove(val)
        removed = True

    return removed

def conflict(r1, c1, r2, c2):
    """
    True if queens at (r1, c1) and (r2, c2) conflict (same column or diagonal)
    """
    if c1 == c2:
        return True
    return abs(r1 - r2) == abs(c1 - c2)

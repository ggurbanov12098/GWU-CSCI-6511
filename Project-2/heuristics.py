"""
heuristics.py

Implements CSP heuristics for N-Queens:
- select_unassigned_row (MRV + tie-break)
- order_domain_values (LCV)
"""
from ac3 import conflict

def select_unassigned_row(domains, unassigned_rows, neighbors):
    """
    MRV + tie-break:
      1) Sort by domain size ascending...
      2) If tie, row with more neighbors first
    """
    unassigned_rows.sort(key=lambda r: (len(domains[r]), -len(neighbors[r])))
    return unassigned_rows[0]

def order_domain_values(row, domains, neighbors):
    """
    LCV: sort columns by how many neighbor-domain-values they'd rule out
    """
    values = list(domains[row])

    def constraining_cost(col):
        cost = 0
        for nb in neighbors[row]:
            for val in domains[nb]:
                if conflict(row, col, nb, val):
                    cost += 1
        return cost

    values.sort(key=constraining_cost)
    return values

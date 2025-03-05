import unittest

# Adjust imports to match your actual file/module names.
# For instance, if your main solver is in nqueens_csp.py and you have:
#   def solve_nqueens_csp(n): -> returns assignment or None
#   def conflict(r1, c1, r2, c2): -> returns True/False
from nqueens_csp import solve_nqueens_csp, print_solution
from ac3 import conflict

class TestNQueensCSP(unittest.TestCase):
    def test_conflict(self):
        """
        Simple checks for the conflict(r1, c1, r2, c2) function
        """
        # Same column
        self.assertTrue(conflict(0, 2, 2, 2), "Same column should conflict")
        self.assertTrue(conflict(0, 2, 1, 3), "Same diagonal should conflict")

        # Same diagonal
        self.assertTrue(conflict(0, 0, 1, 1), "Main diagonal conflict")
        self.assertTrue(conflict(2, 3, 4, 1), "Minor diagonal conflict")
        self.assertFalse(conflict(0, 0, 2, 1), "Positions (0,0) and (2,1) do not conflict")

    def test_nqueens_small_valid(self):
        """
        Test a small board known to have solutions, example n=4
        """
        n = 4
        assignment = solve_nqueens_csp(n)
        self.assertIsNotNone(assignment, "4-Queens should have a valid solution")

        # Check for actual conflicts in the returned assignment
        for r1 in range(n):
            c1 = assignment[r1]
            for r2 in range(r1+1, n):
                c2 = assignment[r2]
                self.assertFalse(conflict(r1, c1, r2, c2), 
                                 f"Conflict found between rows {r1} and {r2} in 4-Queens solution")

    def test_nqueens_small_invalid(self):
        """
        n=3 has no solutions. Ensure solver returns None for n < 4
        """
        n = 3
        assignment = solve_nqueens_csp(n)
        self.assertIsNone(assignment, "3-Queens is unsolvable, expected None")

    def test_nqueens_medium(self):
        """
        Should find a solution for test n=8 or n=10 as a standard puzzle.
        This doesn't verify which solution, just that one exists and is conflict-free.
        """
        n = 8
        assignment = solve_nqueens_csp(n)
        self.assertIsNotNone(assignment, "8-Queens should have a valid solution")
        # Optional quick conflict check
        for r1 in range(n):
            c1 = assignment[r1]
            for r2 in range(r1+1, n):
                c2 = assignment[r2]
                self.assertFalse(conflict(r1, c1, r2, c2),
                                 f"Conflict found between rows {r1} and {r2} in 8-Queens solution")

if __name__ == "__main__":
    unittest.main()

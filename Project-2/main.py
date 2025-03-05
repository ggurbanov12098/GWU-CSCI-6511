"""
main.py

Example entry point that uses solve_nqueens_csp from nqueens_csp.py
"""
import sys
from nqueens_csp import solve_nqueens_csp, print_solution

def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <n>")
        sys.exit(1)

    n = int(sys.argv[1])
    if n < 10:
        print("The value must be between 10<=n<=1000")
        sys.exit(0)

    assignment = solve_nqueens_csp(n)
    if assignment:
        print_solution(assignment, n)
    else:
        print("No solution found")

if __name__ == "__main__":
    main()

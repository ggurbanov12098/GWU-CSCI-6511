import sys, math, queue
from math import gcd, ceil

def parse_file(file_path):
    """
    Parses the input file to extract pitcher capacities and the target quantity.  
    
    Args:
        file_path (str): Path to the input file. 
    Returns:
        tuple: A tuple containing a list of capacities (with an extra 'infinite' container added) and the target integer.
    """
    with open(file_path) as file:
        # Read the first line (container sizes)
        line = file.readline().strip()
        sizes = [int(x) for x in line.split(',')] if line else []
        sizes.append(float('inf'))  # add the infinite container
        # Read the second line (target)
        target_line = file.readline().strip()
        target = int(target_line) if target_line else 0
    return sizes, target


def can_measure(sizes, goal):
    """
    Determines if the target quantity can be measured using finite pitchers, based on the GCD of their capacities.
    
    Args:
        sizes (list): List of capacities (last element is infinite).
        goal (int): Target quantity.
    Returns:
        bool: True if the target is measurable, False otherwise.
    """
    finite = sizes[:-1]  # exclude infinite container
    if not finite: 
        return goal == 0
    div = finite[0]
    for x in finite[1:]:
        div = gcd(div, x)
    return (goal % div == 0)

def heuristic(state, goal, sizes):
    """
    Heuristic function for the A* search.      
    Estimates the minimum moves needed in A* search by dividing the remaining water by the smallest finite pitcher capacity.

    Args:
        state (tuple): The current state (water amounts in each pitcher).
        goal (int): The target quantity.
        sizes (list): List of capacities (last element is infinite).
        
    Returns:
        int: The heuristic value (lower bound on steps needed).
    """
    # Simple estimate: distance based on smallest finite container
    needed = goal - state[-1]
    if not needed: 
        return 0
    finite = sizes[:-1]  # exclude infinite container
    return math.inf if not finite else ceil(abs(needed) / min(finite))


def fill(current_state, sizes):
    """
    Generates new states by filling each finite pitcher to its maximum capacity.
    
    Args:
        current_state (tuple): The current state.
        sizes (list): List of capacities (last element is infinite).
    Returns:
        list: A list of new states resulting from fill operations.
    """
    moves = []
    for i in range(len(sizes) - 1):  # skip infinite container
        if current_state[i] < sizes[i]:
            new_state = list(current_state)
            new_state[i] = sizes[i] # Fill pitcher i
            moves.append(tuple(new_state))
    return moves

def pour(current_state, sizes):
    """
    Generates new states by transferring water between pitchers until the source is empty or the destination is full.

    Args:
        state (tuple): The current state.
        sizes (list): List of capacities (last element is infinite).
    Returns:
        list: A list of new states resulting from pour operations.
    """
    moves = []
    for i in range(len(sizes)):
        if current_state[i] == 0: # Nothing to pour from pitcher i
            continue
        for j in range(len(sizes)):
            if i == j or current_state[j] == sizes[j]: # Skip same pitcher or if destination is full
                continue
            amount = min(current_state[i], sizes[j] - current_state[j]) # Maximum water to pour
            if amount > 0:
                new_state = list(current_state)
                new_state[i] -= amount
                new_state[j] += amount
                moves.append(tuple(new_state))
    return moves


def a_star(file_path="input.txt"):
    """
    Implements the A* search algorithm to solve the Water Pitcher problem.
    
    Args:
        file_path (str): Path to the input file.
    Returns:
        int: The minimum number of steps required to reach the target quantity in the infinite pitcher, or -1 if no solution exists.
    """
    sizes, goal = parse_file(file_path)
    if not can_measure(sizes, goal):
        return -1 # No solution possible
    
    start = tuple([0] * len(sizes)) # Initial state: all pitchers are empty
    visited = set([start])      ## Visited = {(0,0,0,0,0)}
    pq = queue.PriorityQueue()  # (priority, steps, state)
    pq.put((heuristic(start, goal, sizes), 0, start)) 
    ## start, heuristic((0,0,0,0,0), 143, [2,5,6,72,inf])
    
    while not pq.empty():
        _, steps, state = pq.get()
        # Check if target reached in infinite pitcher
        if state[-1] == goal:
            return steps
        # Generate new states from fill and pour operations
        for next in fill(state, sizes) + pour(state, sizes):
            if next not in visited:
                visited.add(next)
                cost = steps + 1
                pq.put((cost + heuristic(next, goal, sizes), cost, next))
                # print(f"State: {next}, Steps: {cost}, Heuristic: {heuristic(next, goal, sizes)}")
    return -1 # No solution found

if __name__ == "__main__":
    file_path = sys.argv[1] if len(sys.argv) > 1 else "input.txt"
    res = a_star(file_path)
    print(res if res >= 0 else -1)

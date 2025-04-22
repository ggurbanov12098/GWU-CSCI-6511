# Local GridWorld Q-Learning Agent

This project implements a local GridWorld simulator and a Q-Learning agent to solve multiple grid-based environments. The agent learns to navigate the grid, avoid traps, and reach goal cells using a reinforcement learning approach.

## Overview

- **GridWorld Environment:** Simulates a 40×40 grid with stochastic movements. Each grid contains:
  - Regular cells with a default reward of -0.04.
  - Randomly chosen goal cells (reward +1).
  - Randomly chosen traps (reward -1).
  - Randomly placed walls, which block movement.
- **Q-Learning Agent:** Utilizes an ε-greedy, decaying strategy to update the Q-table over multiple episodes.

## Files

- **[p4_local.py](/Project-4/p4_local.py)**  
  Contains the implementation for:
  - `GridWorldEnv`: The environment simulator.
  - `QLearn`: The Q-Learning algorithm.
  - `train_all_worlds()`: The training loop that runs the agent in 10 different grid worlds.

- **q_tables/**  
  A folder where each world's Q-table is persisted between runs as `Q_world_{w}.pkl`.

- **[README.md](/Project-4/README.md)**  
  This documentation file.

## How It Works

1. **GridWorldEnv Class**  
   - Simulates a grid world where:
     - 3 random goal cells give a reward of +1.
     - 5 random trap cells give a reward of -1.
     - Default reward for all other cells is -0.04.
     - Approximately 10% of the grid is randomly assigned as walls.
   - Supports stochastic movement:
     - 80% probability of moving in the intended direction.
     - 10% probability of turning left.
     - 10% probability of turning right.
   - The `reset()` method initializes the agent at a random non-terminal, non-wall state.
   - The `step()` method simulates action execution in the grid.

2. **QLearn Class**  
   - Implements a standard Q-Learning algorithm:
     - Uses a Q-table to store state-action values.
     - Implements ε-greedy action selection.
     - Updates the Q-table based on the learning rate (`alpha`), discount factor (`gamma`), and decaying exploration rate (`epsilon`).
   - Persists training progress by saving and loading the Q-table from pickle files.

3. **Training Process (`train_all_worlds` Function)**  
   - Runs training in 10 distinct grid worlds.
   - Executes 5 episodes per world.
   - Resets the environment at the start of each episode.
   - Saves the Q-table for each world after every episode, allowing training to persist across runs.

## How to Run

Ensure you have Python and the required dependencies installed. Then, run the script from your terminal:

```shell
python p4_local.py
```

The training progress, including episode start states and completion messages, will be printed to the console.

## Project Structure

```plaintext
Project-4/
 ├── README.md
 ├── p4_local.py
 └── q_tables/
     ├── Q_world_0.pkl
     ├── Q_world_1.pkl
     ├── Q_world_2.pkl
     ├── Q_world_3.pkl
     ├── Q_world_4.pkl
     ├── Q_world_5.pkl
     ├── Q_world_6.pkl
     ├── Q_world_7.pkl
     ├── Q_world_8.pkl
     └── Q_world_9.pkl
## Additional Information
```

For further details on individual classes and functions, please refer to the comments in the [p4_local.py](/Project-4/p4_local.py) source code.

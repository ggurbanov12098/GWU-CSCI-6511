#!/usr/bin/env python3
"""
Local GridWorld Q-Learning Agent for Project 4

- Simulates 10 distinct 40*40 grid worlds
- Runs Q-Learning (1600 states * 4 actions) in each world
- Meets “quorum” of ≥5 full traversals per world
- Persists each world's Q-table between runs
"""

import os
import pickle
import random
import numpy as np


class GridWorldEnv:
    """A local 40×40 gridworld simulator with stochastic moves."""

    # action → (dr, dc)
    ACTIONS = [(-1, 0), (0, 1), (1, 0), (0, -1)]
    N_ACTIONS = len(ACTIONS)

    def __init__(self, shape=(40, 40), seed=None):
        self.rows, self.cols = shape
        self.n_states = self.rows * self.cols

        if seed is not None:
            np.random.seed(seed)
            random.seed(seed)

        # build prize grid: default reward -0.04
        self.prize = np.full(shape, -0.04, dtype=float)

        # randomly pick 3 goal cells, reward +1
        goals = np.random.choice(self.n_states, size=3, replace=False)
        for idx in goals:
            r, c = divmod(idx, self.cols)
            self.prize[r, c] = +1.0

        # randomly pick 5 traps, reward -1
        traps = np.random.choice([i for i in range(self.n_states) if i not in goals],
                                 size=5, replace=False)
        for idx in traps:
            r, c = divmod(idx, self.cols)
            self.prize[r, c] = -1.0

        # terminal mask: goals ∪ traps
        self.terminal = np.zeros(shape, dtype=bool)
        for idx in np.concatenate([goals, traps]):
            r, c = divmod(idx, self.cols)
            self.terminal[r, c] = True

        # randomly place 10% walls (non-traversable)
        self.wall = np.random.rand(*shape) < 0.10
        # ensure terminal cells are not walls
        self.wall[self.terminal] = False

    def reset(self):
        """Pick a random non-terminal, non-wall start state."""
        valid = np.where(~self.terminal & ~self.wall)
        choice = np.random.randint(len(valid[0]))
        r, c = valid[0][choice], valid[1][choice]
        return r * self.cols + c

    def step(self, state_idx, action_idx):
        """
        Take action in {0,1,2,3}. Stochastic:
          80% intended, 10% turn left, 10% turn right.
        Returns: next_state_idx, reward, done
        """
        r, c = divmod(state_idx, self.cols)
        # choose actual direction
        rand_val = random.random()
        if rand_val < 0.80:
            move = action_idx
        elif rand_val < 0.90:
            move = (action_idx - 1) % self.N_ACTIONS
        else:
            move = (action_idx + 1) % self.N_ACTIONS

        dr, dc = self.ACTIONS[move]
        r2 = min(max(r + dr, 0), self.rows - 1)
        c2 = min(max(c + dc, 0), self.cols - 1)
        # bounce back if wall
        if self.wall[r2, c2]:
            r2, c2 = r, c

        reward = float(self.prize[r2, c2])
        done = bool(self.terminal[r2, c2])
        next_idx = r2 * self.cols + c2
        return next_idx, reward, done


class QLearn:
    """Tabular Q-Learning (ε-greedy, decaying ε)."""

    def __init__(self, n_states, n_actions,
                 alpha=0.5, gamma=0.9,
                 epsilon=0.5, epsilon_decay=0.995):
        self.n_states = n_states
        self.n_actions = n_actions
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon = epsilon
        self.epsilon_decay = epsilon_decay
        self.Q = np.zeros((n_states, n_actions), dtype=float)
        self._last_state = None
        self._last_action = None

    def load(self, filename):
        if os.path.exists(filename):
            self.Q = pickle.load(open(filename, "rb"))

    def save(self, filename):
        pickle.dump(self.Q, open(filename, "wb"))

    def choose(self, state):
        """ε-greedy action selection."""
        if random.random() < self.epsilon:
            a = random.randrange(self.n_actions)
        else:
            a = int(np.argmax(self.Q[state]))
        self._last_state = state
        self._last_action = a
        return a

    def update(self, next_state, reward, done):
        s, a = self._last_state, self._last_action
        future = 0.0 if done else np.max(self.Q[next_state])
        # Q ← (1−α)Q + α[r + γ max Q']
        self.Q[s, a] = (1 - self.alpha) * self.Q[s, a] + \
                       self.alpha * (reward + self.gamma * future)
        # decay exploration
        self.epsilon *= self.epsilon_decay


def train_all_worlds():
    worlds = 10
    shape = (40, 40)
    episodes = 5
    qdir = "q_tables"
    os.makedirs(qdir, exist_ok=True)

    for w in range(worlds):
        print(f"\n=== World {w} ===")
        env = GridWorldEnv(shape=shape, seed=1000 + w)
        qfile = os.path.join(qdir, f"Q_world_{w}.pkl")
        ql = QLearn(n_states=env.n_states, n_actions=env.N_ACTIONS)
        ql.load(qfile)

        for ep in range(episodes):
            s = env.reset()
            done = False
            print(f" Episode {ep+1} start at state {s}")
            while not done:
                a = ql.choose(s)
                ns, r, done = env.step(s, a)
                ql.update(ns, r, done)
                s = ns
            print(f"  ↳ Episode {ep+1} done.")
            ql.save(qfile)

    print("\nTraining complete for all worlds.")


if __name__ == "__main__":
    train_all_worlds()

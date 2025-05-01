# dyna_q_agent.py

import time
import random
import numpy as np
import os
import json
import pickle
from api import GridWorldAPI
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from datetime import datetime
import glob

class DynaQAgent:
    def __init__(
        self,
        world_size=(40, 40),
        num_actions=4,
        alpha=0.1,
        gamma=0.99,
        epsilon_start=1.0,
        epsilon_min=0.05,
        epsilon_decay=0.9,
        planning_steps=20,
        max_steps_per_episode=1000,
        save_dir="saved_models",
        plots_dir="plots",
        manual_goals=None  # New parameter for manually specified goals
    ):
        """
        Dyna-Q agent for GridWorldAPI.

        Args:
            world_size: tuple (width, height) of the grid
            num_actions: number of discrete actions (N, E, S, W)
            alpha: learning rate
            gamma: discount factor
            epsilon_start: initial exploration rate
            epsilon_min: minimal exploration rate after decay
            epsilon_decay: multiplicative decay per episode
            planning_steps: number of planning (simulated) updates per real step
            max_steps_per_episode: safety cap on steps per episode
            save_dir: directory to save/load models and world knowledge
            plots_dir: directory to save visualization plots
            manual_goals: dict of world_id -> list of goal positions to insert manually
        """
        self.width, self.height = world_size
        self.num_actions = num_actions
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon = epsilon_start
        self.epsilon_min = epsilon_min
        self.epsilon_decay = epsilon_decay
        self.planning_steps = planning_steps
        self.max_steps = max_steps_per_episode
        self.save_dir = save_dir
        self.plots_dir = plots_dir

        # Create directories if they don't exist
        for directory in [self.save_dir, self.plots_dir]:
            if not os.path.exists(directory):
                os.makedirs(directory)

        # Q-table: shape [x, y, action]
        self.Q = np.zeros((self.width, self.height, self.num_actions), dtype=np.float32)
        # Model memory: maps (x,y,action) -> (x2,y2,reward)
        self.model = {}

        # For "no-immediate-backtracking" heuristic
        # action idx: 0=N,1=E,2=S,3=W
        self.opposite = {0:2, 1:3, 2:0, 3:1}

        # World knowledge base
        self.world_knowledge = {}  # Map of world_id -> {goals, traps, visited, episode_count}
        
        # Visits tracker for heatmap
        self.visits_grid = np.zeros((self.width, self.height), dtype=np.int32)

        # API wrapper
        self.api = GridWorldAPI()
        
        # Dictionary to store manually added goals
        self.manual_goals = manual_goals or {}
        
        # Load saved state if available
        self.load_state()
        
        # Add any manual goals to world knowledge
        self.add_manual_goals()

    def choose_action(self, x, y, last_action, world_id, prev_reward=None, recent_rewards=None):
        """Epsilon-greedy, with trap avoidance, goal-seeking, and reward-based path stickiness."""
        # Track recent rewards to detect if we're on a promising path
        if recent_rewards is None:
            recent_rewards = []
        
        # If we have reward history, determine if we're on a promising path
        on_promising_path = False
        if prev_reward is not None and len(recent_rewards) > 0:
            # Check if the trend is positive (rewards increasing)
            avg_recent = sum(recent_rewards[-3:]) / min(3, len(recent_rewards)) if recent_rewards else -1
            if prev_reward > avg_recent:
                on_promising_path = True
        
        # Modify exploration rate based on whether we're on a promising path
        effective_epsilon = self.epsilon
        if on_promising_path:
            # On promising path, reduce exploration dramatically
            effective_epsilon = self.epsilon * 0.3  # Much less exploration
        elif prev_reward is not None and prev_reward < -0.5:
            # If getting negative rewards, slightly increase exploration
            effective_epsilon = min(0.8, self.epsilon * 1.2)
        
        # Check if we're near a known goal
        if world_id in self.world_knowledge and 'goals' in self.world_knowledge[world_id]:
            # Check if we're close to a goal (within 3 steps)
            for goal_str in self.world_knowledge[world_id]['goals']:
                try:
                    goal_x, goal_y = eval(goal_str)
                    # Manhattan distance to goal
                    distance = abs(x - goal_x) + abs(y - goal_y)
                    
                    # If we're close to a goal, try to head toward it
                    if distance <= 3:
                        # Determine action that moves toward goal
                        if x < goal_x:  # Goal is East
                            goal_action = 1  # East
                        elif x > goal_x:  # Goal is West
                            goal_action = 3  # West
                        elif y < goal_y:  # Goal is North
                            goal_action = 0  # North
                        elif y > goal_y:  # Goal is South
                            goal_action = 2  # South
                        
                        # If we're already very close to the goal, higher chance to move toward it
                        if distance <= 1 and random.random() < 0.9:
                            return goal_action
                        # Otherwise, increased but not guaranteed chance to move toward goal
                        elif random.random() < 0.7:
                            return goal_action
                except:
                    pass
        
        # If we're on a promising path and last action exists, higher chance to repeat it
        if on_promising_path and last_action is not None and random.random() < 0.4:
            return last_action
        
        # Check if this position might lead to a trap
        if world_id in self.world_knowledge and 'traps' in self.world_knowledge[world_id]:
            # Convert position to string for dict lookup
            pos_str = str((x, y))
            if pos_str in self.world_knowledge[world_id]['traps']:
                # We're at a known position that has led to traps before
                unsafe_actions = self.world_knowledge[world_id]['traps'][pos_str]
                
                # Avoid actions that led to traps (100% avoidance)
                candidates = [a for a in range(self.num_actions) if a not in unsafe_actions]
                
                # If we have safe actions and the last action's opposite is in candidates, 
                # we prefer not to backtrack but will if necessary
                if candidates and last_action is not None:
                    back = self.opposite[last_action]
                    if back in candidates and len(candidates) > 1:
                        candidates.remove(back)
                        
                if candidates:  # If we have safe actions, choose from them
                    if random.random() < effective_epsilon:
                        if on_promising_path and last_action is not None and last_action in candidates:
                            # If on promising path, higher chance to keep going the same direction
                            if random.random() < 0.6:
                                return last_action
                        return random.choice(candidates)
                    else:
                        # Find best Q value among safe actions
                        safe_q_values = [self.Q[x, y, a] for a in candidates]
                        return candidates[np.argmax(safe_q_values)]
            
            # Also check neighboring positions for traps and avoid moving toward them
            neighbor_positions = [
                ((x, y+1), 0),  # North
                ((x+1, y), 1),  # East
                ((x, y-1), 2),  # South
                ((x-1, y), 3)   # West
            ]
            
            dangerous_actions = []
            for (nx, ny), action in neighbor_positions:
                # Skip if out of bounds
                if nx < 0 or nx >= self.width or ny < 0 or ny >= self.height:
                    continue
                    
                neighbor_str = str((nx, ny))
                if neighbor_str in self.world_knowledge[world_id]['traps']:
                    # This neighbor is a trap position, avoid moving there
                    dangerous_actions.append(action)
            
            # If we have actions to avoid but some safe options remain
            if dangerous_actions and len(dangerous_actions) < self.num_actions:
                safe_actions = [a for a in range(self.num_actions) if a not in dangerous_actions]
                # Avoid backtracking if possible, unless on a promising path
                if last_action is not None:
                    back = self.opposite[last_action]
                    if back in safe_actions and len(safe_actions) > 1 and not on_promising_path:
                        safe_actions.remove(back)
                
                # Use safe actions with high probability
                if random.random() < 0.8:
                    if random.random() < effective_epsilon:
                        if on_promising_path and last_action is not None and last_action in safe_actions:
                            # If on promising path, higher chance to keep going the same direction
                            if random.random() < 0.6:
                                return last_action
                        return random.choice(safe_actions)
                    else:
                        # Find best Q value among safe actions
                        safe_q_values = [self.Q[x, y, a] for a in safe_actions]
                        return safe_actions[np.argmax(safe_q_values)]
        
        # Normal epsilon-greedy with no-backtracking, modified by promising path
        if random.random() < effective_epsilon:
            # explore: pick any action except immediate backtrack (unless on promising path)
            candidates = list(range(self.num_actions))
            if last_action is not None:
                back = self.opposite[last_action]
                # Only remove backtracking if not on a promising path
                if not on_promising_path:
                    candidates.remove(back)
                # If on promising path, favor continuing in same direction
                elif random.random() < 0.6:
                    return last_action
            return random.choice(candidates)
        else:
            # exploit: pick best Q
            return int(np.argmax(self.Q[x, y, :]))

    def update_q(self, x, y, a, r, x2, y2):
        """One-step Q-learning update with boundary penalty."""
        # Add boundary penalty to discourage edges and corners
        boundary_penalty = self.get_boundary_penalty(x2, y2)
        
        # Apply the boundary penalty to the reward
        adjusted_reward = r + boundary_penalty
        
        # Standard Q-learning update with adjusted reward
        target = adjusted_reward + self.gamma * np.max(self.Q[x2, y2, :])
        self.Q[x, y, a] += self.alpha * (target - self.Q[x, y, a])

    def planning(self):
        """Perform Dyna planning steps from stored model."""
        if not self.model:
            return
        for _ in range(self.planning_steps):
            # sample a previously observed (s,a) at random
            (xs, ys, asamp), (xsp, ysp, rp) = random.choice(list(self.model.items()))
            target = rp + self.gamma * np.max(self.Q[xsp, ysp, :])
            self.Q[xs, ys, asamp] += self.alpha * (target - self.Q[xs, ys, asamp])

    def save_knowledge_backup(self):
        """Create a timestamped backup of world knowledge."""
        if not self.world_knowledge:
            return  # Nothing to backup
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = os.path.join(self.save_dir, "backups")
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
            
        backup_file = os.path.join(backup_dir, f"world_knowledge_backup_{timestamp}.json")
        with open(backup_file, 'w') as f:
            json.dump(self.world_knowledge, f)
        
        print(f"Created knowledge backup: {backup_file}")

    def save_state(self):
        """Save Q-values, model and world knowledge."""
        # Create a backup of world knowledge first
        self.save_knowledge_backup()
        
        # Save Q-values
        q_file = os.path.join(self.save_dir, "q_values.npy")
        np.save(q_file, self.Q)
        
        # Save model for planning
        model_file = os.path.join(self.save_dir, "model.pkl")
        with open(model_file, 'wb') as f:
            pickle.dump(self.model, f)
        
        # Save world knowledge
        knowledge_file = os.path.join(self.save_dir, "world_knowledge.json")
        with open(knowledge_file, 'w') as f:
            json.dump(self.world_knowledge, f)
        
        print(f"Saved agent state to {self.save_dir}")

    def load_state(self):
        """Load Q-values, model and world knowledge if they exist."""
        loaded_something = False
        
        # Load Q-values
        q_file = os.path.join(self.save_dir, "q_values.npy")
        if (os.path.exists(q_file)):
            self.Q = np.load(q_file)
            print(f"Loaded Q-values from {q_file}")
            loaded_something = True
        
        # Load model
        model_file = os.path.join(self.save_dir, "model.pkl")
        if os.path.exists(model_file):
            with open(model_file, 'rb') as f:
                self.model = pickle.load(f)
            print(f"Loaded model from {model_file}")
            loaded_something = True
        
        # Load world knowledge
        knowledge_file = os.path.join(self.save_dir, "world_knowledge.json")
        if os.path.exists(knowledge_file):
            with open(knowledge_file, 'r') as f:
                self.world_knowledge = json.load(f)
            print(f"Loaded world knowledge from {knowledge_file}")
            
            # Print summary of loaded knowledge
            if self.world_knowledge:
                print("\nLoaded knowledge summary:")
                for world_id, data in self.world_knowledge.items():
                    print(f"  World {world_id}:")
                    print(f"    Goals known: {len(data.get('goals', []))}")
                    print(f"    Trap positions known: {len(data.get('traps', {}))}")
                    print(f"    Positions visited: {len(data.get('visited', []))}")
            
            loaded_something = True
        
        if not loaded_something:
            print("No previous knowledge found. Starting fresh.")
        
        return loaded_something

    def merge_world_knowledge(self, new_knowledge):
        """Merge new knowledge into existing world knowledge."""
        if not new_knowledge:
            return
            
        for world_id, world_data in new_knowledge.items():
            # Initialize this world if it doesn't exist
            if world_id not in self.world_knowledge:
                self.world_knowledge[world_id] = {
                    'goals': [],
                    'traps': {},
                    'visited': [],
                    'episode_count': 0
                }
            
            # Merge goals
            if 'goals' in world_data:
                for goal in world_data['goals']:
                    if goal not in self.world_knowledge[world_id]['goals']:
                        self.world_knowledge[world_id]['goals'].append(goal)
            
            # Merge traps
            if 'traps' in world_data:
                for pos, actions in world_data['traps'].items():
                    if pos not in self.world_knowledge[world_id]['traps']:
                        self.world_knowledge[world_id]['traps'][pos] = []
                    
                    # Add new unsafe actions
                    for action in actions:
                        if action not in self.world_knowledge[world_id]['traps'][pos]:
                            self.world_knowledge[world_id]['traps'][pos].append(action)
            
            # Merge visited positions
            if 'visited' in world_data:
                for pos in world_data['visited']:
                    if pos not in self.world_knowledge[world_id]['visited']:
                        self.world_knowledge[world_id]['visited'].append(pos)
            
            # Take max of episode counts
            if 'episode_count' in world_data:
                self.world_knowledge[world_id]['episode_count'] = max(
                    self.world_knowledge[world_id].get('episode_count', 0),
                    world_data['episode_count']
                )
        
        print("Merged new knowledge into existing world knowledge")
    
    def restore_knowledge_from_backup(self, backup_file=None):
        """Restore world knowledge from a backup file."""
        backup_dir = os.path.join(self.save_dir, "backups")
        
        if not os.path.exists(backup_dir):
            print("No backup directory found")
            return False
        
        if backup_file is None:
            # Find the most recent backup
            backup_files = glob.glob(os.path.join(backup_dir, "world_knowledge_backup_*.json"))
            
            if not backup_files:
                print("No backup files found")
                return False
                
            # Sort by timestamp (newest first)
            backup_files.sort(reverse=True)
            backup_file = backup_files[0]
        
        try:
            with open(backup_file, 'r') as f:
                backup_knowledge = json.load(f)
            
            # Merge with current knowledge
            self.merge_world_knowledge(backup_knowledge)
            
            print(f"Restored knowledge from backup: {backup_file}")
            return True
        except Exception as e:
            print(f"Error restoring from backup: {e}")
            return False

    def train_world(self, world_id, num_episodes=5, use_manual_goals=True):
        """Train on a single world for a given number of episodes."""
        world_id_str = str(world_id)
        print(f"\n=== Training on world {world_id} for {num_episodes} episodes ===")
        
        # Initialize world knowledge for this world if not exists
        if world_id_str not in self.world_knowledge:
            self.world_knowledge[world_id_str] = {
                'goals': [],
                'traps': {},
                'visited': [],
                'episode_count': 0
            }
        else:
            # Print summary of prior knowledge for this world
            print(f"Using existing knowledge for world {world_id}:")
            print(f"  Known goals: {len(self.world_knowledge[world_id_str].get('goals', []))}")
            print(f"  Known trap positions: {len(self.world_knowledge[world_id_str].get('traps', {}))}")
            print(f"  Visited positions: {len(self.world_knowledge[world_id_str].get('visited', []))}")
            print(f"  Previous episodes: {self.world_knowledge[world_id_str].get('episode_count', 0)}")
        
        # Determine starting episode number
        start_episode = self.get_next_episode_number(world_id)
        print(f"Starting from episode {start_episode}")
        
        for episode in range(start_episode, start_episode + num_episodes):
            print(f"\n--- Episode {episode} ---")
            
            # Enter the world
            print(f"Entering world {world_id}...")
            in_world = False
            max_attempts = 3
            attempts = 0
            
            while not in_world and attempts < max_attempts:
                attempts += 1
                try:
                    init = self.api.enter_world(world_id)
                    if init is None:
                        print(f"Failed to enter world {world_id}, attempt {attempts}/{max_attempts}...")
                        time.sleep(1)  # Respect rate limits
                        continue
                    in_world = True
                    print(f"Successfully entered world {world_id}")
                except Exception as e:
                    print(f"Error entering world: {str(e)}, attempt {attempts}/{max_attempts}")
                    time.sleep(1)
            
            if not in_world:
                print(f"Failed to enter world {world_id} after {max_attempts} attempts. Skipping episode.")
                continue
            
            # Reset environment
            reset_successful = False
            reset_attempts = 0
            max_reset_attempts = 3
            
            while not reset_successful and reset_attempts < max_reset_attempts:
                reset_attempts += 1
                try:
                    state = self.api.reset(world=world_id)
                    if state is None:
                        print(f"Failed to reset world {world_id}, attempt {reset_attempts}/{max_reset_attempts}...")
                        time.sleep(1)
                        # We might need to re-enter the world if reset fails
                        try:
                            self.api.enter_world(world_id)
                        except:
                            pass
                        continue
                    reset_successful = True
                except Exception as e:
                    print(f"Error resetting world: {str(e)}, attempt {reset_attempts}/{max_reset_attempts}")
                    time.sleep(1)
                    # Re-enter the world if there was an exception
                    try:
                        self.api.enter_world(world_id)
                    except:
                        pass
            
            if not reset_successful:
                print(f"Failed to reset world {world_id}. Skipping episode.")
                continue
                
            (x, y) = state['agent_position']
            print(f"Starting at position ({x}, {y})")
            
            # Reset visit grid for this episode
            self.visits_grid = np.zeros((self.width, self.height), dtype=np.int32)
            
            done = False
            step = 0
            last_action = None
            prev_reward = None
            recent_rewards = []  # Keep track of recent rewards to detect trends
            encountered_trap = False
            found_goal = False
            
            # Record starting position as visited
            if str((x, y)) not in self.world_knowledge[world_id_str]['visited']:
                self.world_knowledge[world_id_str]['visited'].append(str((x, y)))
            
            # Update visits grid for visualization
            self.visits_grid[x, y] += 1

            while not done and step < self.max_steps:
                # First, try to use manual goal knowledge if available and enabled
                manual_action = None
                if use_manual_goals and len(self.world_knowledge[world_id_str].get('goals', [])) > 0:
                    manual_action = self.choose_action_with_manual_goals(x, y, world_id_str)
                    
                    # If we have a suggested action from manual goals, use it with high probability
                    if manual_action is not None and random.random() < 0.8:
                        a = manual_action
                        print(f"Using manual goal knowledge to choose action {a}")
                    else:
                        # Fall back to regular action selection
                        a = self.choose_action(x, y, last_action, world_id_str, prev_reward, recent_rewards)
                else:
                    # Use regular action selection
                    a = self.choose_action(x, y, last_action, world_id_str, prev_reward, recent_rewards)
                
                try:
                    # Take a step
                    next_state, reward, done = self.api.step(a)
                    
                    # Update reward history
                    if prev_reward is not None:
                        recent_rewards.append(prev_reward)
                        # Keep only the most recent rewards (last 10)
                        if len(recent_rewards) > 10:
                            recent_rewards.pop(0)
                    prev_reward = reward
                    
                    # Check if hit a terminal state (API returns None for next_state)
                    if next_state is None:
                        is_goal = False
                        is_trap = False
                        
                        # Check for Goal State based on reward spike
                        # Adjusted conditions:
                        # 1. For large positive reward (absolute value), always consider as goal
                        # 2. For positive rewards that are significantly bigger than previous reward
                        if (reward > 100) or (prev_reward is not None and reward > 0 and 
                                            prev_reward != 0 and (reward / abs(max(0.001, prev_reward))) >= 50):
                            print(f"Probable Goal State detected at ({x}, {y}) based on large reward: {reward}")
                            # Record the current position as a goal state
                            goal_pos_str = str((x, y))
                            if goal_pos_str not in self.world_knowledge[world_id_str]['goals']:
                                self.world_knowledge[world_id_str]['goals'].append(goal_pos_str)
                                print(f"Added goal position {goal_pos_str} to world knowledge")
                            found_goal = True
                            is_goal = True
                            done = True # Treat this as episode end
                            
                        # Check for Trap State based on reward drop
                        # Adjusted conditions:
                        # 1. For large negative reward (absolute value), always consider as trap
                        # 2. For negative rewards that are significantly lower than previous reward
                        elif (reward < -100) or (prev_reward is not None and reward < 0 and 
                                            (reward - prev_reward) <= -50):
                            print(f"Probable Trap State detected at ({x}, {y}) with action {a} based on large negative reward: {reward}")
                            pos_str = str((x, y))
                            if pos_str not in self.world_knowledge[world_id_str]['traps']:
                                self.world_knowledge[world_id_str]['traps'][pos_str] = []
                            if a not in self.world_knowledge[world_id_str]['traps'][pos_str]:
                                self.world_knowledge[world_id_str]['traps'][pos_str].append(a)
                            encountered_trap = True
                            is_trap = True
                            done = True # Treat this as episode end
                        
                        # Default case if next_state is None but reward doesn't match criteria
                        else:
                            print(f"Hit a terminal state at ({x}, {y}) with action {a}, reward: {reward}")
                            # Use reward sign to determine if this might be a goal or trap
                            if reward > 0:
                                print(f"Positive reward suggests this might be a goal state, but not enough evidence. Treating as neutral.")
                                # We could potentially mark as a potential goal for future investigation
                            else:
                                print(f"Non-positive reward suggests this is likely a trap. Adding to trap knowledge.")
                                pos_str = str((x, y))
                                if pos_str not in self.world_knowledge[world_id_str]['traps']:
                                    self.world_knowledge[world_id_str]['traps'][pos_str] = []
                                if a not in self.world_knowledge[world_id_str]['traps'][pos_str]:
                                    self.world_knowledge[world_id_str]['traps'][pos_str].append(a)
                                encountered_trap = True
                                is_trap = True
                            done = True # Treat this as episode end

                        # Save state and handle re-entry if needed (common for traps/errors)
                        self.save_state()
                        
                        # Need to re-enter the world after hitting a terminal state that required re-entry
                        # (Assuming the API requires re-entry after None state, similar to traps/errors)
                        print("Re-entering world after terminal state...")
                        rejoined = False
                        rejoin_attempts = 0
                        max_rejoin_attempts = 3
                        
                        while not rejoined and rejoin_attempts < max_rejoin_attempts:
                            rejoin_attempts += 1
                            try:
                                self.api.enter_world(world_id)
                                rejoined = True
                                print("Successfully re-entered world after terminal state")
                            except Exception as e:
                                print(f"Failed to re-enter world: {str(e)}, attempt {rejoin_attempts}/{max_rejoin_attempts}")
                                time.sleep(1)
                        
                        if not rejoined:
                            print("Could not re-enter world after terminal state. Ending episode.")
                        
                        break # End the episode loop
                    
                    # --- Normal Step Processing (next_state is not None) ---
                    # Get new position
                    (x2, y2) = next_state['agent_position']
                    
                    # Update Q-values
                    self.update_q(x, y, a, reward, x2, y2)
                    
                    # Store in model for planning
                    self.model[(x, y, a)] = (x2, y2, reward)
                    
                    # Perform planning steps
                    self.planning()
                    
                    # Record position as visited
                    if str((x2, y2)) not in self.world_knowledge[world_id_str]['visited']:
                        self.world_knowledge[world_id_str]['visited'].append(str((x2, y2)))
                    
                    # Update visits grid for visualization
                    self.visits_grid[x2, y2] += 1
                    
                    # If completed with positive reward (standard goal detection)
                    if done and reward > 0:
                        print(f"Found goal at position ({x2, y2}) with reward {reward}")
                        goal_pos_str = str((x2, y2))
                        if goal_pos_str not in self.world_knowledge[world_id_str]['goals']:
                            self.world_knowledge[world_id_str]['goals'].append(goal_pos_str)
                            print(f"Added new goal position {goal_pos_str} to world knowledge")
                        found_goal = True
                    
                    # Move to next state
                    last_action = a
                    x, y = x2, y2
                    step += 1
                    
                    # Progress report
                    if step % 100 == 0:
                        print(f"Step {step}/{self.max_steps}, position ({x}, {y})")
                    
                    if done:
                        print(f"Episode {episode} finished in {step} steps with reward {reward}")
                        break
                        
                except Exception as e:
                    print(f"Error during step: {str(e)}")
                    
                    # When we get an error, assume it's a trap state
                    goal_detected = False
                    error_msg = str(e).lower()
                    
                    # Treat the error as hitting a trap state
                    pos_str = str((x, y))
                    if pos_str not in self.world_knowledge[world_id_str]['traps']:
                        self.world_knowledge[world_id_str]['traps'][pos_str] = []
                    
                    # Make sure we have a valid action before adding it to traps
                    if 'a' in locals() and a is not None:
                        if a not in self.world_knowledge[world_id_str]['traps'][pos_str]:
                            self.world_knowledge[world_id_str]['traps'][pos_str].append(a)
                            print(f"Added action {a} to trap list for position {pos_str}")
                    
                    encountered_trap = True
                    
                    # Re-enter the world after the error
                    print("Re-entering world after error...")
                    try:
                        self.api.enter_world(world_id)
                        print("Successfully re-entered world after error")
                    except Exception as re_e:
                        print(f"Failed to re-enter world: {str(re_e)}")
                    
                    break # End the episode after an error
            
            # Create visualization for this episode
            self.visualize_episode(world_id, episode, found_goal, encountered_trap)
            
            # Visualize the current policy and save to file (overwrites previous)
            self.visualize_policy(world_id, episode)
            
            # Update episode count
            self.world_knowledge[world_id_str]['episode_count'] = episode
            
            # Decay exploration rate
            if self.epsilon > self.epsilon_min:
                self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)
                print(f"Decayed epsilon to {self.epsilon:.3f}")
            
            # Save state after each episode
            self.save_state()
            
            if encountered_trap:
                print(f"Episode {episode} encountered a trap after {step} steps")
            elif found_goal:
                print(f"Episode {episode} found a goal after {step} steps")
            
            # Sleep briefly to ensure API rate limits
            time.sleep(0.5)

        print(f"\nTraining complete for world {world_id}.\n")
    
    def add_manual_goals(self):
        """Add manually specified goals to the agent's world knowledge."""
        if not self.manual_goals:
            return
            
        goals_added = 0
        for world_id, goals in self.manual_goals.items():
            world_id_str = str(world_id)
            
            # Initialize world knowledge for this world if it doesn't exist
            if world_id_str not in self.world_knowledge:
                self.world_knowledge[world_id_str] = {
                    'goals': [],
                    'traps': {},
                    'visited': [],
                    'episode_count': 0
                }
            
            # Add each manual goal position to the world knowledge
            for goal_pos in goals:
                goal_str = str(goal_pos)  # Convert to string format for storage
                if goal_str not in self.world_knowledge[world_id_str]['goals']:
                    self.world_knowledge[world_id_str]['goals'].append(goal_str)
                    goals_added += 1
                    
                    # Update Q-values to make this goal location highly attractive
                    x, y = goal_pos
                    if 0 <= x < self.width and 0 <= y < self.height:
                        # Set high Q-values for all actions leading to the goal state
                        for action in range(self.num_actions):
                            self.Q[x, y, action] = 10.0  # High value to attract the agent
        
        if goals_added > 0:
            print(f"Added {goals_added} manual goal positions to world knowledge")
            self.save_state()  # Save the updated world knowledge

    def add_goal(self, world_id, goal_position):
        """
        Add a single goal position to a specific world.
        
        Args:
            world_id: ID of the world to add the goal to
            goal_position: Tuple of (x, y) coordinates for the goal
        """
        world_id_str = str(world_id)
        goal_str = str(goal_position)
        
        # Initialize world knowledge for this world if it doesn't exist
        if world_id_str not in self.world_knowledge:
            self.world_knowledge[world_id_str] = {
                'goals': [],
                'traps': {},
                'visited': [],
                'episode_count': 0
            }
        
        # Add the goal position if it's not already known
        if goal_str not in self.world_knowledge[world_id_str]['goals']:
            self.world_knowledge[world_id_str]['goals'].append(goal_str)
            
            # Update Q-values to make this goal location highly attractive
            x, y = goal_position
            if 0 <= x < self.width and 0 <= y < self.height:
                # Set high Q-values for all actions leading to the goal state
                for action in range(self.num_actions):
                    self.Q[x, y, action] = 10.0  # High value to attract the agent
            
            print(f"Added manual goal at position {goal_position} to world {world_id}")
            
            # Also store it in manual_goals for future reference
            if world_id_str not in self.manual_goals:
                self.manual_goals[world_id_str] = []
            if goal_position not in self.manual_goals[world_id_str]:
                self.manual_goals[world_id_str].append(goal_position)
            
            # Save the updated world knowledge
            self.save_state()
            return True
        else:
            print(f"Goal position {goal_position} already known for world {world_id}")
            return False

    def choose_action_with_manual_goals(self, x, y, world_id):
        """
        Choose an action that will move the agent toward the nearest known goal
        while avoiding known traps.
        
        Args:
            x, y: Current position
            world_id: ID of the current world
            
        Returns:
            Action index to move toward nearest goal, or None if no goals known
        """
        world_id_str = str(world_id)
        
        # Check if we have any known goals for this world
        if world_id_str not in self.world_knowledge or not self.world_knowledge[world_id_str]['goals']:
            return None
        
        # Find the nearest goal
        nearest_goal = None
        min_distance = float('inf')
        
        for goal_str in self.world_knowledge[world_id_str]['goals']:
            try:
                goal_x, goal_y = eval(goal_str)
                distance = abs(x - goal_x) + abs(y - goal_y)  # Manhattan distance
                
                if distance < min_distance:
                    min_distance = distance
                    nearest_goal = (goal_x, goal_y)
            except:
                continue
        
        if nearest_goal is None:
            return None
        
        # If we're close to the goal (within 3 steps), move directly toward it
        # unless we know there's a trap in that direction
        goal_x, goal_y = nearest_goal
        
        # Get list of possible directions to consider
        possible_actions = list(range(self.num_actions))
        
        # First, check if the current position has any known unsafe actions
        # and remove them from consideration
        pos_str = str((x, y))
        if world_id_str in self.world_knowledge and 'traps' in self.world_knowledge[world_id_str] and pos_str in self.world_knowledge[world_id_str]['traps']:
            unsafe_actions = self.world_knowledge[world_id_str]['traps'][pos_str]
            possible_actions = [a for a in possible_actions if a not in unsafe_actions]
            
            # If all actions from this position are unsafe, return None to fall back to normal action selection
            if not possible_actions:
                return None
        
        # Check neighboring cells for traps and avoid moving toward them
        dangerous_neighbors = []
        
        # Map of possible neighbor positions
        neighbor_positions = [
            ((x, y+1), 0),  # North
            ((x+1, y), 1),  # East
            ((x, y-1), 2),  # South
            ((x-1, y), 3)   # West
        ]
        
        # Identify dangerous neighbors
        for (nx, ny), action in neighbor_positions:
            # Skip if out of bounds
            if nx < 0 or nx >= self.width or ny < 0 or ny >= self.height:
                # Mark out of bounds actions as dangerous
                dangerous_neighbors.append(action)
                continue
                
            # Check if this neighbor position is a known trap
            neighbor_str = str((nx, ny))
            if world_id_str in self.world_knowledge and 'traps' in self.world_knowledge[world_id_str] and neighbor_str in self.world_knowledge[world_id_str]['traps']:
                dangerous_neighbors.append(action)
        
        # Remove dangerous actions from consideration
        safe_actions = [a for a in possible_actions if a not in dangerous_neighbors]
        
        # If no safe actions remain, fall back to the full list of possible actions
        # This might happen when we're completely surrounded by traps or boundaries
        if not safe_actions:
            safe_actions = possible_actions
        
        # Calculate distances to the goal for each potential next position
        action_distances = []
        
        for action in safe_actions:
            # Calculate the next position if we take this action
            if action == 0:  # North
                next_x, next_y = x, y+1
            elif action == 1:  # East
                next_x, next_y = x+1, y
            elif action == 2:  # South
                next_x, next_y = x, y-1
            elif action == 3:  # West
                next_x, next_y = x-1, y
            
            # Skip if out of bounds
            if next_x < 0 or next_x >= self.width or next_y < 0 or next_y >= self.height:
                continue
                
            # Calculate Manhattan distance from next position to goal
            distance = abs(next_x - goal_x) + abs(next_y - goal_y)
            
            # Store action and resulting distance
            action_distances.append((action, distance))
        
        # If no valid actions found, fall back to basic goal direction
        if not action_distances:
            # Basic directional logic as fallback
            horizontal_diff = goal_x - x
            vertical_diff = goal_y - y
            
            if abs(horizontal_diff) > abs(vertical_diff):
                if horizontal_diff > 0:
                    return 1  # East
                else:
                    return 3  # West
            else:
                if vertical_diff > 0:
                    return 0  # North
                else:
                    return 2  # South
        
        # Sort actions by distance (ascending)
        action_distances.sort(key=lambda x: x[1])
        
        # Check if there's a tie for best action (multiple actions with same shortest distance)
        best_distance = action_distances[0][1]
        best_actions = [a for a, d in action_distances if d == best_distance]
        
        # If multiple actions are equally good, use Q-values to break the tie
        if len(best_actions) > 1:
            # Find the action with highest Q-value
            best_q_value = float('-inf')
            best_action = best_actions[0]  # Default to first action
            
            for action in best_actions:
                q_value = self.Q[x, y, action]
                if q_value > best_q_value:
                    best_q_value = q_value
                    best_action = action
            
            return best_action
        else:
            # Return the action that minimizes distance to goal
            return action_distances[0][0]

    def get_next_episode_number(self, world_id):
        """Determine the next episode number for a world based on existing plots."""
        world_id_str = str(world_id)
        # Check world knowledge for episode count
        if world_id_str in self.world_knowledge and 'episode_count' in self.world_knowledge[world_id_str]:
            return self.world_knowledge[world_id_str]['episode_count'] + 1
        
        # Check existing plots to determine episode number
        pattern = os.path.join(self.plots_dir, f"world_{world_id}_episode_*.png")
        existing_plots = glob.glob(pattern)
        
        if not existing_plots:
            return 1
            
        # Extract episode numbers from filenames
        episode_numbers = []
        for plot_path in existing_plots:
            try:
                # Extract the episode number from the filename
                filename = os.path.basename(plot_path)
                episode_str = filename.split("episode_")[1].split("_")[0]
                episode_numbers.append(int(episode_str))
            except (IndexError, ValueError):
                continue
                
        return max(episode_numbers) + 1 if episode_numbers else 1

    def visualize_episode(self, world_id, episode_num, found_goal=False, hit_trap=False):
        """Create and save visualization of the current episode."""
        world_id_str = str(world_id)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create figure with 2 subplots
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 10))
        
        # 1. Heatmap of visits with black/orange theme
        # Create a custom black-to-orange colormap with more gradient steps
        colors = [
            (0, 0, 0),           # Black (no visits)
            (0.2, 0.1, 0),       # Very dark orange (few visits)
            (0.4, 0.2, 0),       # Dark orange
            (0.6, 0.3, 0),       # Medium orange
            (0.8, 0.4, 0),       # Bright orange
            (1.0, 0.6, 0.2),     # Light orange
            (1.0, 0.8, 0.4)      # Very light orange (many visits)
        ]
        cmap_name = 'visit_intensity'
        cmap = mcolors.LinearSegmentedColormap.from_list(cmap_name, colors, N=256)
        
        # Find the maximum visit count for proper normalization
        max_visits = max(1, np.max(self.visits_grid))
        
        # Use a power-law normalization for better visualization of visit intensity differences
        # This will make the color intensity increase more clearly with visit frequency
        power = 0.5  # Square root transformation gives good balance
        norm = mcolors.PowerNorm(gamma=power, vmin=0, vmax=max_visits)
        
        visits_heatmap = ax1.imshow(
            self.visits_grid.T,  # Transpose for correct orientation
            cmap=cmap,
            norm=norm,
            interpolation='nearest',
            origin='lower'
        )
        
        # Add a colorbar with clear tick marks showing actual visit counts
        cbar = fig.colorbar(visits_heatmap, ax=ax1)
        tick_positions = np.linspace(0, max_visits, min(10, max_visits+1))
        tick_positions = np.unique(np.floor(tick_positions).astype(int))  # Get unique integer ticks
        cbar.set_ticks(tick_positions)
        cbar.set_label('Number of visits', color='white')
        cbar.ax.tick_params(colors='white')
        
        ax1.set_title(f'Visit Heatmap for World {world_id}, Episode {episode_num}', 
                     color='white', fontsize=14)
        ax1.set_xlabel('X coordinate', color='white')
        ax1.set_ylabel('Y coordinate', color='white')
        ax1.tick_params(colors='white')  # Make tick labels white
        
        # Add grid lines for better coordinate reference
        ax1.grid(color='gray', linestyle='--', linewidth=0.5, alpha=0.3)
        
        # Set black background
        ax1.set_facecolor('black')
        
        # 2. Goals and Traps visualization
        # Create a blank grid for goals and traps
        gt_grid = np.zeros((self.width, self.height))
        
        # Mark goals as 1
        if world_id_str in self.world_knowledge and 'goals' in self.world_knowledge[world_id_str]:
            for goal_str in self.world_knowledge[world_id_str]['goals']:
                try:
                    x, y = eval(goal_str)  # Convert string repr of tuple back to tuple
                    gt_grid[x, y] = 1  # Mark goal
                except:
                    pass
        
        # Mark trap positions as -1
        if world_id_str in self.world_knowledge and 'traps' in self.world_knowledge[world_id_str]:
            for trap_pos_str in self.world_knowledge[world_id_str]['traps']:
                try:
                    x, y = eval(trap_pos_str)  # Convert string repr of tuple back to tuple
                    gt_grid[x, y] = -1  # Mark trap
                except:
                    pass
        
        # Create custom colormap: red for traps, green for goals, transparent for empty
        cmap = mcolors.ListedColormap(['red', 'black', 'green'])
        bounds = [-1.5, -0.5, 0.5, 1.5]
        norm = mcolors.BoundaryNorm(bounds, cmap.N)
        
        # Plot goals and traps
        gt_map = ax2.imshow(
            gt_grid.T,  # Transpose for correct orientation
            cmap=cmap,
            norm=norm,
            interpolation='nearest',
            origin='lower',
            alpha=0.7  # Semi-transparent
        )
        
        # Add colorbar with custom labels
        cbar = fig.colorbar(gt_map, ax=ax2, ticks=[-1, 0, 1])
        cbar.ax.set_yticklabels(['Trap', 'Empty', 'Goal'])
        cbar.ax.tick_params(colors='white')  # Make colorbar labels white
        
        ax2.set_title(f'Goals and Traps for World {world_id}, Episode {episode_num}',
                     color='white', fontsize=14)
        ax2.set_xlabel('X coordinate', color='white')
        ax2.set_ylabel('Y coordinate', color='white')
        ax2.tick_params(colors='white')  # Make tick labels white
        
        # Add grid lines for better coordinate reference
        ax2.grid(color='gray', linestyle='--', linewidth=0.5, alpha=0.3)
        
        # Set black background
        ax2.set_facecolor('black')
        
        # Add event information to title
        title_parts = [f"World {world_id}, Episode {episode_num}"]
        if found_goal:
            title_parts.append("- GOAL FOUND!")
        if hit_trap:
            title_parts.append("- TRAP HIT!")
        
        # Set global title with white text
        fig.suptitle(" ".join(title_parts), fontsize=16, color='white')
        
        # Set figure background to black
        fig.set_facecolor('black')
        
        # Save the episode-specific plot with timestamp
        episode_plot_path = os.path.join(self.plots_dir, f"world_{world_id}_episode_{episode_num}_{timestamp}.png")
        plt.tight_layout()
        plt.savefig(episode_plot_path, facecolor='black')
        
        plt.close(fig)
        print(f"Saved visualization to {episode_plot_path}")

    def visualize_policy(self, world_id, episode_num):
        """Create and save visualization of the current policy."""
        world_id_str = str(world_id)
        policy = self.get_policy()  # Get current policy (action indices)
        
        # Create a figure
        plt.figure(figsize=(15, 15))
        
        # Create a policy grid for visualization
        policy_grid = np.zeros((self.width, self.height, 3))  # RGB color coding
        
        # Map actions to colors: 
        # North (0) = Blue, East (1) = Red, South (2) = Green, West (3) = Yellow
        action_colors = {
            0: [0, 0, 1],      # North: Blue
            1: [1, 0, 0],      # East: Red
            2: [0, 0.8, 0],    # South: Green
            3: [1, 0.8, 0]     # West: Yellow
        }
        
        # Fill the policy grid with colors based on action
        for x in range(self.width):
            for y in range(self.height):
                policy_grid[x, y] = action_colors[policy[x, y]]
        
        # Plot the policy grid
        plt.imshow(policy_grid.transpose(1, 0, 2), origin='lower')
        
        # Add colorbar legend
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor=action_colors[0], label='North (0)'),
            Patch(facecolor=action_colors[1], label='East (1)'),
            Patch(facecolor=action_colors[2], label='South (2)'),
            Patch(facecolor=action_colors[3], label='West (3)')
        ]
        plt.legend(handles=legend_elements, loc='upper right')
        
        # Overlay known goals and traps
        if world_id_str in self.world_knowledge:
            # Plot goals
            if 'goals' in self.world_knowledge[world_id_str]:
                for goal_str in self.world_knowledge[world_id_str]['goals']:
                    try:
                        x, y = eval(goal_str)
                        plt.scatter(y, x, marker='*', s=300, color='white', edgecolor='black', 
                                   label='Goal' if 'Goal' not in plt.gca().get_legend_handles_labels()[1] else "")
                    except:
                        pass
            
            # Plot traps
            if 'traps' in self.world_knowledge[world_id_str]:
                for trap_pos_str in self.world_knowledge[world_id_str]['traps']:
                    try:
                        x, y = eval(trap_pos_str)
                        plt.scatter(y, x, marker='X', s=100, color='black', edgecolor='white',
                                   label='Trap' if 'Trap' not in plt.gca().get_legend_handles_labels()[1] else "")
                    except:
                        pass
        
        plt.title(f'Learned Policy for World {world_id}, Episode {episode_num}', fontsize=16)
        plt.xlabel('Y Coordinate')
        plt.ylabel('X Coordinate')
        plt.grid(True, linestyle='--', alpha=0.7)
        
        # Add a centered grid
        for i in range(0, self.width + 1, 5):
            plt.axvline(x=i - 0.5, color='gray', linestyle='-', alpha=0.3)
        for i in range(0, self.height + 1, 5):
            plt.axhline(y=i - 0.5, color='gray', linestyle='-', alpha=0.3)
            
        # Add coordinates every 5 steps
        plt.xticks(range(0, self.height, 5))
        plt.yticks(range(0, self.width, 5))
        
        # Save the visualization to a file (overwriting previous version)
        policy_path = os.path.join(self.plots_dir, f"world_{world_id}_policy.png")
        plt.tight_layout()
        plt.savefig(policy_path)
        plt.close()
        
        print(f"Saved policy visualization to {policy_path}")
        
        return policy

    def get_policy(self):
        """Extract greedy policy from learned Q-table."""
        policy = np.argmax(self.Q, axis=2)
        # policy[x,y] gives the best action index at (x,y)
        return policy
    
    def print_world_knowledge(self):
        """Print summary of world knowledge."""
        print("\n=== World Knowledge Summary ===")
        for world_id, data in self.world_knowledge.items():
            print(f"\nWorld {world_id}:")
            print(f"  Episodes completed: {data.get('episode_count', 0)}")
            print(f"  Goals found: {len(data.get('goals', []))}")
            for i, goal in enumerate(data.get('goals', [])):
                print(f"    Goal {i+1}: {goal}")
            
            print(f"  Trap positions: {len(data.get('traps', {}))}")
            for pos, actions in data.get('traps', {}).items():
                print(f"    Position {pos}: unsafe actions {actions}")
            
            print(f"  Visited positions: {len(data.get('visited', []))}")

    def is_boundary_position(self, x, y, boundary_size=1):
        """
        Check if a position is near the boundary/edge of the grid.
        
        Args:
            x, y: Position to check
            boundary_size: How many cells from the edge to consider as boundary
            
        Returns:
            Boolean indicating if the position is on or near a boundary
        """
        return (x < boundary_size or 
                y < boundary_size or 
                x >= self.width - boundary_size or 
                y >= self.height - boundary_size)
    
    def get_boundary_penalty(self, x, y):
        """
        Calculate a penalty for being at a boundary position.
        Higher penalty for corner positions.
        
        Args:
            x, y: Position to calculate penalty for
            
        Returns:
            A negative value as penalty (more negative for corners)
        """
        # Check if position is in a corner (adjacent to two boundaries)
        is_corner = ((x == 0 or x == self.width - 1) and 
                    (y == 0 or y == self.height - 1))
        
        # Check if position is on an edge but not a corner
        is_edge = self.is_boundary_position(x, y, 1) and not is_corner
        
        # Calculate penalty
        if is_corner:
            return -0.2  # Stronger penalty for corners
        elif is_edge:
            return -0.1  # Milder penalty for edges
        else:
            return 0.0  # No penalty for non-boundary positions

if __name__ == "__main__":
    # Example of manually specifying goal positions
    # manual_goals = {
    #     "3": [(35, 25)],  # Example goal position for world 3
    #     "4": [(20, 35), (30, 10)]  # Multiple goal positions for world 4
    # }
    
    # Set up agent with 1000 steps per episode and the manual goals
    agent = DynaQAgent(
        alpha=0.2,
        gamma=0.99,
        epsilon_start=1.0,
        epsilon_min=0.05,
        epsilon_decay=0.8,
        planning_steps=30,
        max_steps_per_episode=1000,
        save_dir="saved_models",
        plots_dir="plots",
    )
    
    # You can also add a goal later
    # agent.add_goal(world_id=5, goal_position=(12, 18))
    
    # Train on multiple worlds sequentially
    worlds_to_train = [7]  # Add more as needed
    episodes_per_world = 50
    
    for world_id in worlds_to_train:
        # Use the use_manual_goals parameter to enable/disable manual goal guidance
        agent.train_world(world_id=world_id, num_episodes=episodes_per_world, use_manual_goals=True)
    
    # Print summary of what the agent learned
    agent.print_world_knowledge()
    
    # Extract final policy
    policy = agent.get_policy()
    print("Learned policy (action indices):")
    # Print a more readable subset of the policy
    print(policy)
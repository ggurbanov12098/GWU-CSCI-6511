import requests
import json
import time
import random

class GridWorldAPI:
    """
    API wrapper for the GridWorld reinforcement learning environment.
    Handles communication with the external API endpoints.
    """
    
    def __init__(self, user_id="3676", api_key="2280990937bf6f34d1dc", team_id="1463"):
        """
        Initialize the API wrapper.
        
        Args:
            user_id: User ID for authentication
            api_key: API key for authentication
            team_id: Team ID for API requests
        """
        # Correct URLs for each endpoint
        self.gw_url = "https://www.notexponential.com/aip2pgaming/api/rl/gw.php"  # For location, enter world, make move
        self.score_url = "https://www.notexponential.com/aip2pgaming/api/rl/score.php"  # For get runs and get score
        
        # Fix headers - Remove Content-Type for GET requests to avoid security issues
        self.headers = {
            'User-Agent': 'GridWorldAgent/1.0',  # Add user agent
            'userid': user_id,
            'x-api-key': api_key
        }
        
        # Separate headers for POST requests
        self.post_headers = {
            'User-Agent': 'GridWorldAgent/1.0',  # Add user agent
            'userid': user_id,
            'x-api-key': api_key,
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        self.team_id = team_id
        
        # Keep track of last API call times to respect rate limits
        self.last_enter_time = 0
        self.last_move_time = 0
        
        # Current state
        self.current_world_id = -1
        self.current_run_id = None
        self.current_state = None
        
        # Actions mapping: 0=Up, 1=Right, 2=Down, 3=Left
        self.actions = ["N", "E", "S", "W"]
        
    def enter_world(self, world_id):
        """
        Enter a specific world.
        
        Args:
            world_id: ID of the world to enter (1-10)
            
        Returns:
            dict with initial state information or None if failed
        """
        # Respect rate limit (5 seconds between enter calls)
        current_time = time.time()
        time_since_last_enter = current_time - self.last_enter_time
        
        if time_since_last_enter < 5:  # Changed from 600 (10 minutes) to 5 seconds
            wait_time = 5 - time_since_last_enter
            print(f"Rate limit: Waiting {wait_time:.1f} seconds before entering world...")
            time.sleep(wait_time)
        
        # First, check if we're already in a world by getting location
        location = self.get_location()
        
        # If location check fails, we'll attempt to enter anyway
        if location and location.get('world') != '-1' and int(location.get('world', -1)) == world_id:
            print(f"Already in world {world_id}. Using current state.")
            
            # Parse state if available
            if location.get('state'):
                state_str = location.get('state')
                x, y = state_str.split(':')
                self.current_state = {'x': int(x), 'y': int(y)}
                self.current_world_id = int(location.get('world'))
                
                # Return a state representation that our environment can use
                return {
                    'agent_position': (self.current_state['x'], self.current_state['y']),
                    'walls': [],  # We don't know walls initially
                    'goals': [],  # We don't know goals initially
                    'traps': []   # We don't know traps initially
                }
        
        # Prepare the request
        payload = {
            'type': 'enter',
            'worldId': str(world_id),
            'teamId': self.team_id
        }
        
        try:
            # Make the request - Use POST headers for POST request
            print(f"Attempting to enter world {world_id}...")
            response = requests.post(self.gw_url, data=payload, headers=self.post_headers)
            
            # Check if we got a response
            if not response.text:
                print("Error: Empty response received from server when entering world")
                # Try again after a short delay
                time.sleep(5)
                response = requests.post(self.gw_url, data=payload, headers=self.post_headers)
                if not response.text:
                    print("Error: Second attempt to enter world failed with empty response")
                    return None
            
            # Parse the JSON response
            try:
                response_data = response.json()
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON when entering world: {str(e)[:50]}...")
                
                # If we get HTML instead of JSON, it might be a security issue
                if '<html' in response.text.lower() or '<body' in response.text.lower():
                    print("Received HTML response instead of JSON. Retrying with adjusted headers...")
                    
                    # Try with simplified headers
                    simple_headers = {
                        'userid': self.headers['userid'],
                        'x-api-key': self.headers['x-api-key'],
                    }
                    response = requests.post(self.gw_url, data=payload, headers=simple_headers)
                    
                    try:
                        response_data = response.json()
                    except:
                        print("Still couldn't parse JSON response when entering world")
                        return None
                else:
                    return None
            
            # Update last enter time
            self.last_enter_time = time.time()
            
            # Check for errors
            if response_data.get('code') == 'FAIL':
                print(f"Error entering world: {response_data.get('message')}")
                
                # Check if already in a world message
                message = response_data.get('message', '').lower()
                if "currently in world" in message:
                    # Extract current world from message
                    try:
                        # Extract from message like "Cannot enter the world. You are currently in world: 1"
                        current_world = int(message.split("world:")[-1].strip())
                        print(f"Already in world {current_world}. Using this world.")
                        self.current_world_id = current_world
                        
                        # Get current location to get state
                        location = self.get_location()
                        if location and location.get('state'):
                            state_str = location.get('state')
                            x, y = state_str.split(':')
                            self.current_state = {'x': int(x), 'y': int(y)}
                            
                            # Return a state representation
                            return {
                                'agent_position': (self.current_state['x'], self.current_state['y']),
                                'walls': [],
                                'goals': [],
                                'traps': []
                            }
                    except (ValueError, IndexError) as e:
                        print(f"Error extracting current world from message: {e}")
                
                return None
            
            # Parse successful response
            self.current_world_id = int(response_data.get('worldId'))
            self.current_run_id = response_data.get('runId')
            
            # Parse initial state
            state_str = response_data.get('state', '0:0')
            x, y = state_str.split(':')
            self.current_state = {'x': int(x), 'y': int(y)}
            
            print(f"Successfully entered world {self.current_world_id}, run ID: {self.current_run_id}")
            print(f"Initial state: x={self.current_state['x']}, y={self.current_state['y']}")
            
            # Return a state representation that our environment can use
            return {
                'agent_position': (self.current_state['x'], self.current_state['y']),
                'walls': [],  # We don't know walls initially
                'goals': [],  # We don't know goals initially
                'traps': []   # We don't know traps initially
            }
            
        except Exception as e:
            print(f"Error entering world: {e}")
            return None
    
    def make_move(self, action_idx):
        """
        Make a move in the current world.
        
        Args:
            action_idx: Index of the action to take (0-3)
            
        Returns:
            Tuple of (next_state, reward, done)
        """
        # Check if we're in a world
        if self.current_world_id == -1 or self.current_run_id is None:
            print("Error: Not in a world. Call enter_world first.")
            
            # Try to get current location to recover from this state
            location = self.get_location()
            if location and location.get('world') != '-1':
                print(f"Recovered: Found we're in world {location.get('world')}. Continuing.")
                
                # Update current world and state
                self.current_world_id = int(location.get('world'))
                
                # Parse state
                if location.get('state'):
                    state_str = location.get('state')
                    x, y = state_str.split(':')
                    self.current_state = {'x': int(x), 'y': int(y)}
            else:
                # Still not in a world, try to enter current_world_id or default to 1
                world_to_enter = self.current_world_id if self.current_world_id != -1 else 1
                print(f"Not in any world. Attempting to enter world {world_to_enter}...")
                result = self.enter_world(world_to_enter)
                if result is None:
                    # If enter fails, return error state
                    return None, 0, True
        
        # Store current position before moving (for error checking)
        prev_x, prev_y = self.current_state['x'], self.current_state['y']
        
        # Map action index to direction
        move = self.actions[action_idx]
        
        # Respect rate limit (1 seconds between move calls)
        current_time = time.time()
        time_since_last_move = current_time - self.last_move_time
        
        if time_since_last_move < 1:  # Changed from 10 to 1 seconds between moves
            wait_time = 1 - time_since_last_move
            print(f"Rate limit: Waiting {wait_time:.1f} seconds before moving...")
            time.sleep(wait_time)
        
        # Prepare the request
        payload = {
            'type': 'move',
            'teamId': self.team_id,
            'move': move,
            'worldId': str(self.current_world_id)
        }
        
        # Track the last reward to help detect goal states
        last_reward = getattr(self, 'previous_reward', 0)
        
        try:
            # Make the request - Use POST headers for POST request
            response = requests.post(self.gw_url, data=payload, headers=self.post_headers)
            
            # Check if we got a response
            if not response.text:
                print("Error: Empty response received from server when making move")
                # Return to current state with no reward
                return {
                    'agent_position': (self.current_state['x'], self.current_state['y']),
                    'walls': [],
                    'goals': [],
                    'traps': []
                }, 0, False
            
            # Parse the JSON response
            try:
                response_data = response.json()
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON for move: {str(e)[:50]}...")
                # Return current state with no reward
                return {
                    'agent_position': (self.current_state['x'], self.current_state['y']),
                    'walls': [],
                    'goals': [],
                    'traps': []
                }, 0, False
            
            # Update last move time
            self.last_move_time = time.time()
            
            # Check for errors
            if response_data.get('code') == 'FAIL':
                error_msg = response_data.get('message', 'Unknown error')
                print(f"Error making move: {error_msg}")
                
                # Check for unusual messages that might indicate rate limit issues
                if 'unusual' in error_msg.lower() or 'too fast' in error_msg.lower():
                    print("Rate limit issue detected. Waiting additional time...")
                    time.sleep(10)  # Wait 10 more seconds
                    # Try the move again - recursive call
                    return self.make_move(action_idx)
                
                # Check if this is a "Game Over" error
                if 'game over' in error_msg.lower():
                    # Return a done state
                    return {
                        'agent_position': (self.current_state['x'], self.current_state['y']),
                        'walls': [],
                        'goals': [],
                        'traps': []
                    }, 0, True
                
                # Check if not in a world error
                if 'not in a world' in error_msg.lower() or 'not in any world' in error_msg.lower():
                    # This is likely a trap state that kicked us out - return None to indicate trap
                    print("Hit a trap state! API says we're not in any world.")
                    # Return None to indicate a trap was hit
                    return None, -1.0, True
                
                # Return current state with small penalty
                return {
                    'agent_position': (self.current_state['x'], self.current_state['y']),
                    'walls': [],
                    'goals': [],
                    'traps': []
                }, -0.1, False
            
            # Parse response
            reward = float(response_data.get('reward', 0))
            score_increment = float(response_data.get('scoreIncrement', 0))
            
            # Store the previous reward if it exists to compare
            if hasattr(self, 'previous_reward'):
                previous_reward = self.previous_reward
                reward_ratio = reward / max(0.0001, abs(previous_reward))  # Avoid division by zero
                
                # If reward is 500+ times larger than previous move, it's likely a goal
                if reward > 0 and reward_ratio > 500:
                    print(f"GOAL STATE DETECTED: Current reward ({reward:.4f}) is {reward_ratio:.2f}x larger than previous reward ({previous_reward:.4f})")
                    done = True
                else:
                    done = False
            else:
                done = False
                
            # Store current reward for next comparison
            self.previous_reward = reward
            
            # Parse new state from API response
            new_state = response_data.get('newState')
            
            # Check if newState is null (None in Python) - this indicates a terminal state
            if new_state is None:
                print(f"Terminal state detected! API returned newState: null with reward: {reward}")
                # Return None as the next_state to indicate a terminal state
                # The calling code will check reward to determine if it's a goal (high positive) or trap (high negative)
                return None, reward, True
            
            # If we get here, new_state is not null, so process it into our next_state format
            # Handle both string and integer types for x and y
            x_val = new_state.get('x', 0)
            y_val = new_state.get('y', 0)
            
            # Convert to integers if they're strings
            x = int(x_val) if isinstance(x_val, str) else x_val
            y = int(y_val) if isinstance(y_val, str) else y_val
            
            # Update current state
            self.current_state = {'x': x, 'y': y}
            
            # Check if this is a terminal state (high reward might indicate goal)
            if not done and reward > 0.5:  # This threshold might need adjustment
                print(f"High reward ({reward}): Possible goal state reached")
                # Only treat as goal state if very high reward
                if reward > 5.0:
                    done = True
                    print(f"GOAL STATE: Reward {reward} exceeds threshold")
            
            # Check if this could be a delayed trap state (negative reward often indicates this)
            if reward <= -1.0:
                print(f"Negative reward detected ({reward}): Checking if we're still in the world...")
                # Verify we're still in the world by checking location
                location = self.get_location()
                if location is None or location.get('world') == '-1':
                    print("Confirmed trap state: Now out of the world after receiving negative reward")
                    # This is a trap, return None
                    return None, reward, True
            
            # Use scoreIncrement if available (may be more accurate than reward)
            final_reward = score_increment if score_increment != 0 else reward
            
            print(f"Moved {move}, new state: x={x}, y={y}, reward: {reward}, score increment: {score_increment}")
            
            # Return a state representation that our environment can use
            next_state = {
                'agent_position': (x, y),
                'walls': [],  # We don't know walls
                'goals': [],  # We don't know goals
                'traps': [],  # We don't know traps
                'score_increment': score_increment  # Include the score increment
            }
            
            return next_state, final_reward, done
            
        except Exception as e:
            print(f"Error making move: {e}")
            
            # Special handling for 'NoneType' object has no attribute 'get' error
            if "'NoneType' object has no attribute 'get'" in str(e):
                # This could be either a trap state or a goal state that ended the game
                
                # Check if we have a stored previous reward to help determine what happened
                prev_reward = getattr(self, 'previous_reward', None)
                
                # If the previous reward was high, this is likely a goal state
                if prev_reward is not None and prev_reward > 0.5:
                    print(f"GOAL STATE DETECTED at position ({prev_x}, {prev_y}) based on previous reward {prev_reward}")
                    # Return a done state with the positive reward
                    next_state = {
                        'agent_position': (prev_x, prev_y),
                        'walls': [],
                        'goals': [],
                        'traps': []
                    }
                    return next_state, prev_reward, True
                
                # Otherwise, treat it as a trap
                print("Detected potential trap state from NoneType error - agent may have been kicked out of the world")
                return None, -1.0, True
                
            # Return current state with no reward
            return {
                'agent_position': (self.current_state['x'], self.current_state['y']),
                'walls': [],
                'goals': [],
                'traps': []
            }, 0, False
    
    def reset(self, world=None):
        """
        Reset the environment by entering a world.
        
        Args:
            world: World ID to enter (1-10)
            
        Returns:
            Initial state
        """
        # If world is not specified, use current world or default to 1
        if world is None:
            world = self.current_world_id if self.current_world_id != -1 else 1
        
        # If we're already in a world, check if it's the requested world
        if self.current_world_id != -1:
            # Check if we're already in the requested world - if so, just get current location
            if self.current_world_id == world:
                location = self.get_location()
                if location and location.get('world') != '-1':
                    print(f"Already in world {world}. Using current state.")
                    
                    # Parse state
                    if location.get('state'):
                        state_str = location.get('state')
                        x, y = state_str.split(':')
                        self.current_state = {'x': int(x), 'y': int(y)}
                        
                        # Return a state representation
                        return {
                            'agent_position': (self.current_state['x'], self.current_state['y']),
                            'walls': [],
                            'goals': [],
                            'traps': []
                        }
        
        # Enter the world
        return self.enter_world(world)
    
    def step(self, action):
        """
        Take a step in the environment.
        
        Args:
            action: Action index (0-3)
            
        Returns:
            Tuple of (next_state, reward, done)
        """
        return self.make_move(action)
    
    def get_location(self):
        """
        Get current location from the API.
        
        Returns:
            Current world and state
        """
        params = {
            'type': 'location',
            'teamId': self.team_id
        }
        
        try:
            # Make the request - Use GET headers (no Content-Type) for GET request
            print("Checking current location...")
            response = requests.get(self.gw_url, params=params, headers=self.headers)
            
            # Check if we got a response
            if not response.text:
                print("Error: Empty response received from server when getting location")
                return None
            
            # Check for HTML error response
            if '<html' in response.text.lower() or '<body' in response.text.lower():
                print("Received HTML response instead of JSON. Retrying with adjusted headers...")
                
                # Try with simplified headers and parameters in URL
                simple_headers = {
                    'userid': self.headers['userid'],
                    'x-api-key': self.headers['x-api-key'],
                }
                
                # Try with params in URL to avoid security issues
                url_with_params = f"{self.gw_url}?type=location&teamId={self.team_id}"
                response = requests.get(url_with_params, headers=simple_headers)
            
            # Parse the JSON response
            try:
                response_data = response.json()
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON for location: {str(e)[:50]}...")
                
                # If retry with params in URL
                if '<html' in response.text.lower() or '<body' in response.text.lower():
                    print("Still getting HTML. Trying POST method for location...")
                    # Some APIs prefer POST for everything due to security configurations
                    response = requests.post(
                        self.gw_url, 
                        data={'type': 'location', 'teamId': self.team_id},
                        headers=self.post_headers
                    )
                    try:
                        response_data = response.json()
                    except:
                        print("Still couldn't parse JSON response for location")
                        return None
                else:
                    return None
            
            if response_data.get('code') == 'FAIL':
                print(f"Error getting location: {response_data.get('message')}")
                return None
            
            world = response_data.get('world')
            state = response_data.get('state')
            
            print(f"Current location: World {world}, State {state}")
            
            # Update current world and state
            if world != '-1':
                self.current_world_id = int(world)
                
                # Parse state
                if state:
                    x, y = state.split(':')
                    self.current_state = {'x': int(x), 'y': int(y)}
            
            return {
                'world': world,
                'state': state
            }
            
        except Exception as e:
            print(f"Error getting location: {e}")
            return None
    
    def get_runs(self, count=10):
        """
        Get the last X runs.
        
        Args:
            count: Number of runs to retrieve
            
        Returns:
            List of run data
        """
        params = {
            'type': 'runs',
            'teamId': self.team_id,
            'count': str(count)
        }
        
        try:
            # Make the request - Use GET headers (no Content-Type) for GET request
            print(f"Getting previous {count} runs...")
            response = requests.get(self.score_url, params=params, headers=self.headers)
            
            # Check for HTML error response
            if '<html' in response.text.lower() or '<body' in response.text.lower():
                print("Received HTML response instead of JSON. Retrying with adjusted headers...")
                
                # Try with simplified headers and parameters in URL
                simple_headers = {
                    'userid': self.headers['userid'],
                    'x-api-key': self.headers['x-api-key'],
                }
                
                # Try with params in URL
                url_with_params = f"{self.score_url}?type=runs&teamId={self.team_id}&count={count}"
                response = requests.get(url_with_params, headers=simple_headers)
            
            # Check if we got a response
            if not response.text:
                print("Error: Empty response received from server when getting runs")
                return None
            
            # Parse the JSON response
            try:
                response_data = response.json()
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON for runs: {str(e)[:50]}...")
                return None
            
            if response_data.get('code') == 'FAIL':
                print(f"Error getting runs: {response_data.get('message')}")
                return None
            
            runs = response_data.get('runs', [])
            
            print(f"Retrieved {len(runs)} previous runs")
            
            # Display run information in a clean format
            if runs:
                print("\nRecent runs:")
                for i, run in enumerate(runs[:5]):  # Show just the 5 most recent runs
                    print(f"  Run {i+1}: World {run.get('worldId')}, Score: {run.get('score')}, Steps: {run.get('steps')}")
                print("")  # Empty line for better readability
            
            return runs
            
        except Exception as e:
            print(f"Error getting runs: {e}")
            return None
    
    def get_score(self):
        """
        Get the team's current score.
        
        Returns:
            Current score
        """
        params = {
            'type': 'score',
            'teamId': self.team_id
        }
        
        try:
            # Make the request - Use GET headers (no Content-Type) for GET request
            print("Getting current team score...")
            response = requests.get(self.score_url, params=params, headers=self.headers)
            
            # Check for HTML error response
            if '<html' in response.text.lower() or '<body' in response.text.lower():
                print("Received HTML response instead of JSON. Retrying with adjusted headers...")
                
                # Try with simplified headers and parameters in URL
                simple_headers = {
                    'userid': self.headers['userid'],
                    'x-api-key': self.headers['x-api-key'],
                }
                
                # Try with params in URL
                url_with_params = f"{self.score_url}?type=score&teamId={self.team_id}"
                response = requests.get(url_with_params, headers=simple_headers)
            
            # Check if we got a response
            if not response.text:
                print("Error: Empty response received from server when getting score")
                return None
            
            # Parse the JSON response
            try:
                response_data = response.json()
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON for score: {str(e)[:50]}...")
                return None
            
            if response_data.get('code') == 'FAIL':
                print(f"Error getting score: {response_data.get('message')}")
                return None
            
            score = response_data.get('score')
            
            print(f"Current team score: {score}")
            
            return score
            
        except Exception as e:
            print(f"Error getting score: {e}")
            return None
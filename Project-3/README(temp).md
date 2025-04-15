# Advanced Tic Tac Toe AI Implementation

This project implements a sophisticated AI for playing N-in-a-row Tic Tac Toe on variable-sized boards. The AI employs multiple advanced game theory and search algorithms to make optimal decisions.

## Core AI Decision-Making Algorithms

### 1. Minimax with Alpha-Beta Pruning
- Implements the classic minimax algorithm with alpha-beta pruning optimization
- Searches game tree to find optimal moves by simulating future game states
- Alpha-beta pruning drastically reduces search space by eliminating branches that won't affect the final decision

### 2. Iterative Deepening
- Gradually increases search depth until time limit or maximum depth is reached
- Ensures more reliable results under time constraints
- Adjusts search depth dynamically based on board size and game phase

### 3. Move Evaluation and Ordering
- **Positional Scoring**: Prefers strategic positions (center, near-center) over edges and corners
- **Pattern Recognition**: Evaluates board patterns for potential threats and opportunities
- **Move Ordering**: Orders moves for more efficient alpha-beta pruning by examining promising moves first

### 4. Transposition Tables
- Caches previously evaluated positions to avoid redundant calculations
- Hash-based lookup system improves search efficiency
- Stores evaluation scores with depth information

### 5. Quiescence Search
- Extends search in "tactical" positions to avoid horizon effect
- Focused evaluation of moves that may dramatically change board state
- Prevents AI from making mistakes due to search depth limitations

### 6. Team1 (O) Specific Optimizations
- **Optimal First Move Selection**: Special handling for opening move when playing as O
- **Fork Detection**: Identifies and prioritizes moves that create multiple winning threats
- **Offensive Position Bonus**: Enhanced aggression when playing as first player (O)

### 7. Advanced Pattern Detection
- **Winning Pattern Detection**: Recognizes near-complete winning lines (n-1 in a row)
- **Blocking Pattern Detection**: Prioritizes blocking opponent's potential winning moves
- **Creating Pattern Detection**: Identifies opportunities to create strong positions (n-2 in a row)
- **Fork Detection**: Finds and prioritizes moves that create multiple threats

### 8. Position-Based Evaluation
- **Strategic Position Matrix**: 12x12 scoring matrix prioritizing central and strategic positions
- **Dynamic Position Calculation**: Proportional scoring based on distance from center for larger boards
- **Center and Corner Control**: Special bonus for controlling strategic board areas

### 9. Move History Tracking
- Maintains history of successful moves to inform future decisions
- Learns and adapts based on previous game patterns
- Local cache of played moves to prevent duplicate move attempts

## Memory Management and Performance Optimizations

- **Move Sampling**: On larger boards, uses intelligent sampling to avoid combinatorial explosion
- **Time Management**: Monitors search time and adjusts depth to ensure moves within time constraints
- **Pattern Frequency Analysis**: Tracks recurring patterns to inform move evaluation

## Implementation Details

The AI decision-making process involves:
1. Filtering out already played moves
2. Special case handling for first move as Team1 (O)
3. Dynamic depth adjustment based on board state
4. Iterative deepening search with alpha-beta pruning
5. Enhanced evaluation for Team1 (O) specific strategies
6. Positional scoring with strategic position weighting

This implementation can handle various board sizes and winning conditions, automatically adjusting its strategy to maximize performance in different game configurations. 
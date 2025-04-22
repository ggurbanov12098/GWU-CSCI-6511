# Generalized Tic Tac Toe AI

This is an implementation of a Generalized Tic Tac Toe game with an unbeatable AI using Minimax algorithm with Alpha-Beta pruning. The game supports both local play and online play through an API.

## Features

- Supports any board size (n×n)
- Configurable winning condition (m consecutive symbols)
- Minimax algorithm with Alpha-Beta pruning for optimal moves
- CLI interface with clear board visualization
- Support for both local play and API-based online matches
- Efficient pruning techniques to improve performance

## How to Play

1. Run the `GameController` class
2. Choose between local play or API mode
3. Enter the board size (n) and target length to win (m)
4. For API mode, you'll need to provide:
   - Your team ID
   - Opponent's team ID
5. Make moves using row,col coordinates (1-based)

## Algorithm Details

### Minimax with Alpha-Beta Pruning
The AI uses the Minimax algorithm with Alpha-Beta pruning to find the optimal move. The implementation includes:

- Depth-based scoring to prefer winning in fewer moves
- Early pruning of obviously bad moves
- Efficient board evaluation

### Heuristic Function
The evaluation function considers:
- Immediate wins/losses
- Depth of the game tree (prefers winning quickly/losing slowly)
- Position control (center and corners are valued higher)

### Performance Optimizations
- Alpha-Beta pruning to reduce search space
- Move ordering to improve pruning efficiency
- Early termination on winning positions

## Project Structure

- `TicTacToeGame.java`: Core game logic and AI implementation
- `GameController.java`: Game flow control and user interface
- `GameApiClient.java`: API integration for online play

## Requirements

- Java 8 or higher
- Internet connection (for API mode)
- Valid API credentials (for API mode)

## Building and Running

```bash
javac src/main/java/com/tictactoe/*.java
java -cp src/main/java com.tictactoe.GameController
```

## API Integration

The game can be played against other teams through the provided API. To use this feature:

1. Configure your API credentials
2. Choose API mode when starting the game
3. Enter your team ID and opponent's team ID
4. The game will automatically handle turns and board synchronization

## Contributing

Feel free to submit issues and enhancement requests! 
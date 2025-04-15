# Project-3

<details>
    <summary>Instructions</summary>
<br>
A generalized Tic Tac Toe is an n x n board game where each player chooses one of the parts X or O, and then plays in an alternate order to place his choice on the board. A player wins when they are able to place m consecutive symbols (0s or Xs) in a contiguous sequence (row, column or diagonal). The game may end in a draw when no one wins.

## Board Size (n) and Target (m)

Given m and n, the agent can play against another agent in an n*n board and tries to place m symbols (Xs or Os) in a row to win.

## What to Submit

Submit a 1 pager PDF per team by due date 1, via Blackboard.  The writeup should explain:  

- (i) your evaluation (heuristic) function  
- (ii) any key points that you want to make regarding your minimax/adversarial search algorithm  
- (iii) any tricks that you use to improve the performance of your search algorithm.

You will play games against other teams via an API, and the score will be automatically recorded.

## Use of API

We will play and record the games interactively with each other. Details of the API will be shared via Slack and discussed in class.

## Grading Rubrik

- **5 points:**  For the written submission by Due Date 1
- **2 points:** For meeting the “games” quorum, that is, >= 7 games, against >= 2 teams, completed by Due Date 2
- **Remaining 3 points:** On the basis of actual games score.  The game scores will be periodically wiped away until April 12th, so do not worry about any scores until then.  The games do count against quorum, so play early, play often, and don’t worry about winning or losing at least until then.

</details>


## 1. Evaluation (Heuristic) Function

The AI’s evaluation logic resides chiefly in AI.java. In particular, the evaluate(Board board) method yields an integer score reflecting how favorable a position is for the AI player:  

• Immediate Win/Loss Check  
- If the board’s getWinner() method indicates the AI player has already won, evaluate returns a large positive constant (WIN_SCORE = 100000).  
- If the board indicates the opponent has won, it returns the negative of that constant (-WIN_SCORE).
- A full board with no winner is scored as 0 (i.e., a draw).


• Heuristic Sum: generalizedHeuristic(playerAI) − generalizedHeuristic(playerOpponent)  

If the board is not terminal, the code proceeds to compute a more granular heuristic by separately calling generalizedHeuristic(board, playerAI) and generalizedHeuristic(board, playerOpponent) and subtracting one from the other. That difference ensures the AI’s progress is measured relative to the opponent’s progress.  
Within generalizedHeuristic, the AI examines specific factors:

1. Scan all possible lines (rows, columns, diagonals) up to the required target length:  
    - For each contiguous segment of length = target (e.g., 5 in a 10×10 board), the code counts how many positions belong to the AI versus how many belong to the opponent.  
    - If both AI and opponent marks appear within that segment, it contributes 0 (no immediate advantage).  
    - If only one player’s marks appear:  
        - A segment with (target − 1) marks of the AI and at least 1 empty cell is rewarded with a big partial score.
        - A segment with multiple AI marks also earns points on a rising scale (exponential in the code).  
        - Conversely, if the opponent nearly has a complete row (e.g., target − 1) and an empty cell, the AI heavily penalizes it (negative score).  

2. Positional Bias
    - The AI adds a bonus for occupying cells closer to the center. For each piece belonging to the player in question, the code calculates the Manhattan distance from the board’s center. The smaller the distance, the larger the bonus.

3. Fork Detection
    - The AI checks if placing an additional mark can create multiple winning threats, i.e., two or more immediate sequences that would each yield a win in the next move. If so, it adds (or subtracts) a fork bonus.  
    - If the AI can form forks, it adds points; if the opponent can form forks, it subtracts more heavily.

Overall, the AI’s generalizedHeuristic aggregates line scanning, positional considerations, and fork detection to produce a final integer heuristic for each player.


## 2. Minimax / Adversarial Search Key Points

### 2.1 Minimax with Alpha-Beta

In AI.java, the minimax procedure is invoked via:

```java
minimax(Board board, int depth, boolean isMaximizing, int alpha, int beta)
```

- Alpha-Beta Pruning: The code uses alpha and beta parameters to prune branches:
    - If beta <= alpha, it breaks out of the loop early, discarding paths that can’t alter the final decision.

- Terminal Checks: The algorithm checks if the board isTerminal() or if depth == 0. If so, it calls evaluate(board) to stop recursion and return an immediate score.

### 2.2 Memoization / Caching
A map called memo (a ConcurrentHashMap<String,Integer>) stores previously computed minimax evaluations indexed by:  

```java
board.toHashString() + depth + isMaximizing
```  

This effectively caches repeated board states at given depths in the search tree, preventing redundant calculations.

### 2.3 Top-Level Parallelization

In getBestMove():  
1. It first compiles a list of all legal moves.  
2. Each move is evaluated in parallel using Java concurrency (ExecutorService, Futures). The method evaluateMove(...) handles each proposed move and returns its predicted minimax value.

Hence, the top-level search for the best move is multi-threaded, which can significantly speed up exploration for boards with many possible moves, provided the system has multiple CPU cores.


## 3. Tricks & Performance Improvements

The following points in the provided code help optimize or speed up the AI’s decision-making:  

1. Move Ordering
    - Before diving into minimax, the list of legal moves is sorted by a quick heuristic, so the algorithm explores more promising moves first (and alpha-beta can prune more aggressively).

2. Caching/Memoization
    - As mentioned above, the AI caches minimax scores for states (including depth and maximizing/minimizing turn). Caching repeated states avoids recalculating entire branches.

3. Parallelization of Top-Level Moves
    - The AI launches a parallel evaluation for each possible next move, distributing the minimax computations among available CPU cores. This helps shorten the response time, especially on bigger boards.

4. Dynamic or Manual Depth (in OnlineGameController.java)
    - The user can select three modes:
        - A fixed single depth (depthMode = 0).
        - A dynamic depth (depthMode = 1) that, for example, starts shallow (depth=2) when the board is nearly empty, increases to a base depth after some moves, and then goes even deeper if many moves are on the board.
        - A manual depth (depthMode = 2) prompting the user to enter a new depth each turn.
    - This flexibility lets you experiment with deeper searches in critical late-game scenarios or keep it lower early in the game for speed.

5. Immediate Win/Loss Checks
    - Inside evaluateMove(...), the AI quickly checks if making a particular move yields an immediate win. That short-circuits further search and returns a maximum score right away.

6. Fork Detection
    - Rewarding or penalizing situations that create multiple threats (forks) helps the AI catch tricky multi-threat sequences. While not a strict pruning method, it’s a heuristic improvement that helps the AI search lead to stronger moves in fewer expansions.

# Summary
This solution implements a generalized Tic-Tac-Toe AI using a minimax algorithm with alpha-beta pruning, multi-threaded top-level search, and memoization. The evaluation function combines immediate terminal checks, line-based scoring for partial progress toward a target, center/positional bias, and fork detection. Furthermore, dynamic depth adjustment and manual depth override are supported, enhancing flexibility when facing large boards or strategic late-game scenarios.  

These methods together allow the AI to effectively search potentially large state spaces while prioritizing the most promising lines of play and pruning away fruitless branches.


















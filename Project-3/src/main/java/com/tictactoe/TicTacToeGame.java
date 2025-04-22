package com.tictactoe;

import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicReference;

public class TicTacToeGame {
    private final int n; // board size
    private final int m; // target length to win
    private char[][] board;
    private char currentPlayer;
    private static final char EMPTY = '.';
    private static final char PLAYER_X = 'X';
    private static final char PLAYER_O = 'O';
    private static final long TIME_LIMIT_MS = 5000;

    public TicTacToeGame(int boardSize, int target) {
        this.n = boardSize;
        this.m = target;
        this.board = new char[n][n];
        this.currentPlayer = PLAYER_O; // O starts first
        initializeBoard();
    }

    private void initializeBoard() {
        for (int i = 0; i < n; i++) {
            for (int j = 0; j < n; j++) {
                board[i][j] = EMPTY;
            }
        }
    }

    public boolean makeMove(int row, int col) {
        if (row < 0 || row >= n || col < 0 || col >= n || board[row][col] != EMPTY) {
            return false;
        }
        board[row][col] = currentPlayer;
        currentPlayer = (currentPlayer == PLAYER_X) ? PLAYER_O : PLAYER_X;
        return true;
    }

    public Move findBestMove() {
        long startTime = System.currentTimeMillis();
        AtomicBoolean timeUp = new AtomicBoolean(false);
        AtomicReference<Move> bestMoveRef = new AtomicReference<>(null);
        AtomicReference<Integer> bestScoreRef = new AtomicReference<>(Integer.MIN_VALUE);
        AtomicReference<Integer> finalDepthRef = new AtomicReference<>(0);

        // First check for immediate win
        for (int i = 0; i < n; i++) {
            for (int j = 0; j < n; j++) {
                if (board[i][j] == EMPTY) {
                    board[i][j] = currentPlayer;
                    if (evaluateBoard() != GameResult.IN_PROGRESS) {
                        board[i][j] = EMPTY;
                        return new Move(i, j);
                    }
                    board[i][j] = EMPTY;
                }
            }
        }

        // Then check for immediate block
        char opponent = (currentPlayer == PLAYER_X) ? PLAYER_O : PLAYER_X;
        for (int i = 0; i < n; i++) {
            for (int j = 0; j < n; j++) {
                if (board[i][j] == EMPTY) {
                    board[i][j] = opponent;
                    if (evaluateBoard() != GameResult.IN_PROGRESS) {
                        board[i][j] = EMPTY;
                        return new Move(i, j);
                    }
                    board[i][j] = EMPTY;
                }
            }
        }

        // Start iterative deepening search
        Thread searchThread = new Thread(() -> {
            int maxDepth = 1;
            while (!timeUp.get()) {
                long depthStartTime = System.currentTimeMillis();

                Move currentBestMove = null;
                int currentBestScore = Integer.MIN_VALUE;

                for (int i = 0; i < n && !timeUp.get(); i++) {
                    for (int j = 0; j < n && !timeUp.get(); j++) {
                        if (board[i][j] == EMPTY) {
                            board[i][j] = currentPlayer;
                            int score = minimax(board, 0, false, Integer.MIN_VALUE, Integer.MAX_VALUE, maxDepth);
                            board[i][j] = EMPTY;

                            if (score > currentBestScore) {
                                currentBestScore = score;
                                currentBestMove = new Move(i, j);
                            }
                        }
                    }
                }

                if (!timeUp.get()) {
                    bestMoveRef.set(currentBestMove);
                    bestScoreRef.set(currentBestScore);
                    finalDepthRef.set(maxDepth);
                    maxDepth++;
                }
            }
        });

        searchThread.start();

        // Wait for the search thread with timeout
        try {
            searchThread.join(TIME_LIMIT_MS);
            timeUp.set(true);
            searchThread.join(1000); // Give it a second to clean up
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }

        Move bestMove = bestMoveRef.get();
        if (bestMove == null) {
            // If no move was found, make a random move
            for (int i = 0; i < n; i++) {
                for (int j = 0; j < n; j++) {
                    if (board[i][j] == EMPTY) {
                        return new Move(i, j);
                    }
                }
            }
        }

        long endTime = System.currentTimeMillis();
        System.out.println("Final move: (" + bestMove.row + ", " + bestMove.col + ") at depth " + finalDepthRef.get()
                + " in " + (endTime - startTime) + "ms");
        return bestMove;
    }

    private int minimax(char[][] board, int depth, boolean isMaximizing, int alpha, int beta, int maxDepth) {
        GameResult result = evaluateBoard();

        if (result != GameResult.IN_PROGRESS) {
            return getScoreForResult(result, depth);
        }

        if (depth >= maxDepth) {
            return evaluatePosition();
        }

        if (isMaximizing) {
            int bestScore = Integer.MIN_VALUE;
            for (int i = 0; i < n; i++) {
                for (int j = 0; j < n; j++) {
                    if (board[i][j] == EMPTY) {
                        board[i][j] = currentPlayer;
                        int score = minimax(board, depth + 1, false, alpha, beta, maxDepth);
                        board[i][j] = EMPTY;
                        bestScore = Math.max(score, bestScore);
                        alpha = Math.max(alpha, score);
                        if (beta <= alpha)
                            break;
                    }
                }
            }
            return bestScore;
        } else {
            int bestScore = Integer.MAX_VALUE;
            for (int i = 0; i < n; i++) {
                for (int j = 0; j < n; j++) {
                    if (board[i][j] == EMPTY) {
                        board[i][j] = (currentPlayer == PLAYER_X) ? PLAYER_O : PLAYER_X;
                        int score = minimax(board, depth + 1, true, alpha, beta, maxDepth);
                        board[i][j] = EMPTY;
                        bestScore = Math.min(score, bestScore);
                        beta = Math.min(beta, score);
                        if (beta <= alpha)
                            break;
                    }
                }
            }
            return bestScore;
        }
    }

    private int evaluatePosition() {
        int score = 0;

        // Evaluate rows
        for (int i = 0; i < n; i++) {
            for (int j = 0; j <= n - m; j++) {
                score += evaluateLine(i, j, 0, 1);
            }
        }

        // Evaluate columns
        for (int j = 0; j < n; j++) {
            for (int i = 0; i <= n - m; i++) {
                score += evaluateLine(i, j, 1, 0);
            }
        }

        // Evaluate diagonals
        for (int i = 0; i <= n - m; i++) {
            for (int j = 0; j <= n - m; j++) {
                score += evaluateLine(i, j, 1, 1);
            }
        }

        // Evaluate anti-diagonals
        for (int i = 0; i <= n - m; i++) {
            for (int j = m - 1; j < n; j++) {
                score += evaluateLine(i, j, 1, -1);
            }
        }

        return score;
    }

    private int evaluateLine(int startRow, int startCol, int dRow, int dCol) {
        int playerCount = 0;
        int opponentCount = 0;
        char opponent = (currentPlayer == PLAYER_X) ? PLAYER_O : PLAYER_X;

        for (int i = 0; i < m; i++) {
            char cell = board[startRow + i * dRow][startCol + i * dCol];
            if (cell == currentPlayer) {
                playerCount++;
            } else if (cell == opponent) {
                opponentCount++;
            }
        }

        if (opponentCount == 0) {
            return (int) Math.pow(10, playerCount);
        } else if (playerCount == 0) {
            return -(int) Math.pow(10, opponentCount);
        }
        return 0;
    }

    private int getScoreForResult(GameResult result, int depth) {
        switch (result) {
            case X_WINS:
                return currentPlayer == PLAYER_X ? 100 - depth : depth - 100;
            case O_WINS:
                return currentPlayer == PLAYER_O ? 100 - depth : depth - 100;
            case DRAW:
                return 0;
            default:
                return 0;
        }
    }

    public GameResult evaluateBoard() {
        // Check rows
        for (int i = 0; i < n; i++) {
            for (int j = 0; j <= n - m; j++) {
                if (checkLine(i, j, 0, 1)) {
                    return board[i][j] == PLAYER_X ? GameResult.X_WINS : GameResult.O_WINS;
                }
            }
        }

        // Check columns
        for (int j = 0; j < n; j++) {
            for (int i = 0; i <= n - m; i++) {
                if (checkLine(i, j, 1, 0)) {
                    return board[i][j] == PLAYER_X ? GameResult.X_WINS : GameResult.O_WINS;
                }
            }
        }

        // Check diagonals
        for (int i = 0; i <= n - m; i++) {
            for (int j = 0; j <= n - m; j++) {
                if (checkLine(i, j, 1, 1)) {
                    return board[i][j] == PLAYER_X ? GameResult.X_WINS : GameResult.O_WINS;
                }
            }
        }

        // Check anti-diagonals
        for (int i = 0; i <= n - m; i++) {
            for (int j = m - 1; j < n; j++) {
                if (checkLine(i, j, 1, -1)) {
                    return board[i][j] == PLAYER_X ? GameResult.X_WINS : GameResult.O_WINS;
                }
            }
        }

        // Check for draw
        boolean hasEmpty = false;
        for (int i = 0; i < n; i++) {
            for (int j = 0; j < n; j++) {
                if (board[i][j] == EMPTY) {
                    hasEmpty = true;
                    break;
                }
            }
        }

        return hasEmpty ? GameResult.IN_PROGRESS : GameResult.DRAW;
    }

    private boolean checkLine(int startRow, int startCol, int dRow, int dCol) {
        char first = board[startRow][startCol];
        if (first == EMPTY)
            return false;

        for (int i = 1; i < m; i++) {
            if (board[startRow + i * dRow][startCol + i * dCol] != first) {
                return false;
            }
        }
        return true;
    }

    public char[][] getBoard() {
        return board;
    }

    public char getCurrentPlayer() {
        return currentPlayer;
    }

    public static class Move {
        public final int row;
        public final int col;

        public Move(int row, int col) {
            this.row = row;
            this.col = col;
        }
    }

    public enum GameResult {
        X_WINS,
        O_WINS,
        DRAW,
        IN_PROGRESS
    }
}
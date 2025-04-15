package com.tictactoe;

import java.util.*;

public class Board {
    public static final int EMPTY = 0;
    public static final int PLAYER_X = 1;  // AI
    public static final int PLAYER_O = -1; // Human

    private final int[][] grid;
    private final int size;
    private final int target; // number of marks in a row to win
    private int movesMade = 0;

    public Board(int size, int target) {
        this.size = size;
        this.target = target;
        this.grid = new int[size][size];
    }

    public int getCell(int row, int col) {
        return grid[row][col];
    }

    public void applyMove(Move move, int player) {
        grid[move.row][move.col] = player;
        movesMade++;
    }

    public void undoMove(Move move) {
        grid[move.row][move.col] = EMPTY;
        movesMade--;
    }

    public boolean isLegalMove(Move move) {
        return isInBounds(move.row, move.col) && grid[move.row][move.col] == EMPTY;
    }

    public List<Move> getLegalMoves() {
        List<Move> moves = new ArrayList<>();
        for (int i = 0; i < size; i++) {
            for (int j = 0; j < size; j++) {
                if (grid[i][j] == EMPTY) {
                    moves.add(new Move(i, j));
                }
            }
        }
        return moves;
    }

    public boolean isFull() {
        return movesMade == size * size;
    }

    public boolean isTerminal() {
        return getWinner() != 0 || isFull();
    }

    /**
     * Returns:
     *   PLAYER_X if X has won,
     *   PLAYER_O if O has won,
     *   0 if no one has won yet.
     */
    public int getWinner() {
        // Check all possible horizontal lines
        for (int r = 0; r < size; r++) {
            for (int c = 0; c <= size - target; c++) {
                int line = checkLine(r, c, 0, 1);
                if (line != 0) {
                    return line;
                }
            }
        }

        // Check all possible vertical lines
        for (int c = 0; c < size; c++) {
            for (int r = 0; r <= size - target; r++) {
                int line = checkLine(r, c, 1, 0);
                if (line != 0) {
                    return line;
                }
            }
        }

        // Check all possible diagonal lines
        for (int r = 0; r <= size - target; r++) {
            for (int c = 0; c <= size - target; c++) {
                int diag = checkDiagonalsFrom(r, c);
                if (diag != 0) {
                    return diag;
                }
            }
        }

        return 0; // No winner yet
    }

    private int checkLine(int startRow, int startCol, int dr, int dc) {
        int first = grid[startRow][startCol];
        if (first == EMPTY) {
            return 0;
        }
        // Attempt to match 'target' cells
        for (int k = 1; k < target; k++) {
            int r = startRow + dr * k;
            int c = startCol + dc * k;
            if (!isInBounds(r, c) || grid[r][c] != first) {
                return 0;
            }
        }
        return first; // All 'target' matched
    }

    private int checkDiagonalsFrom(int row, int col) {
        // Main diagonal
        int main = checkLine(row, col, 1, 1);
        if (main != 0) {
            return main;
        }

        // Anti-diagonal
        if (col + target - 1 < size) {
            int anti = checkLine(row, col + target - 1, 1, -1);
            if (anti != 0) {
                return anti;
            }
        }
        return 0;
    }

    private boolean isInBounds(int row, int col) {
        return row >= 0 && row < size && col >= 0 && col < size;
    }

    public Board deepCopy() {
        Board copy = new Board(size, target);
        for (int i = 0; i < size; i++) {
            System.arraycopy(this.grid[i], 0, copy.grid[i], 0, size);
        }
        copy.movesMade = this.movesMade;
        return copy;
    }

    public int getSize() {
        return size;
    }

    public int getTarget() {
        return target;
    }

    public String toHashString() {
        StringBuilder sb = new StringBuilder();
        for (int[] row : grid) {
            for (int cell : row) {
                sb.append(cell);
            }
        }
        return sb.toString();
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        for (int[] row : grid) {
            for (int cell : row) {
                sb.append(cellSymbol(cell)).append(" ");
            }
            sb.append("\n");
        }
        return sb.toString();
    }

    private char cellSymbol(int val) {
        switch (val) {
            case PLAYER_X:
                return 'X';
            case PLAYER_O:
                return 'O';
            default:
                return '.';
        }
    }
}

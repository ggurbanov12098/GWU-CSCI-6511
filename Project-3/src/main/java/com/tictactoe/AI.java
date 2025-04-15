package com.tictactoe;

import java.util.*;
import java.util.concurrent.*;

/**
 * AI with configurable or dynamic/manual settable maxDepth.
 */
public class AI {
    private volatile int maxDepth; // can be changed at runtime
    private final int playerAI;
    private final int playerOpponent;
    private final Map<String, Integer> memo;

    private static final int WIN_SCORE = 100000;
    private static final int LOSS_SCORE = -WIN_SCORE;

    public AI(int aiPlayer, int initialDepth) {
        this.playerAI = aiPlayer;
        this.playerOpponent = -aiPlayer;
        this.maxDepth = initialDepth;
        this.memo = new ConcurrentHashMap<>();
    }

    public void setMaxDepth(int newDepth) {
        this.maxDepth = newDepth;
    }

    public Move getBestMove(Board board) {
        memo.clear();
        List<Move> legalMoves = board.getLegalMoves();
        if (legalMoves.isEmpty()) {
            return null;
        }

        // If the board is empty, pick center
        if (legalMoves.size() == board.getSize() * board.getSize()) {
            int center = board.getSize() / 2;
            return new Move(center, center);
        }

        // Sort moves by a quick heuristic so we explore good moves first
        List<Move> orderedMoves = orderMoves(board, legalMoves, playerAI);

        // Use a fixed thread pool
        int numThreads = Math.max(1, Runtime.getRuntime().availableProcessors() - 1);
        ExecutorService executor = Executors.newFixedThreadPool(numThreads);

        Move bestMove = orderedMoves.get(0);
        int bestValue = Integer.MIN_VALUE;

        try {
            List<Future<MoveScore>> futures = new ArrayList<>();
            for (Move move : orderedMoves) {
                futures.add(executor.submit(() -> evaluateMove(board, move)));
            }

            for (Future<MoveScore> fut : futures) {
                MoveScore ms;
                try {
                    ms = fut.get();
                } catch (InterruptedException | ExecutionException e) {
                    e.printStackTrace();
                    continue;
                }
                if (ms.score > bestValue) {
                    bestValue = ms.score;
                    bestMove = ms.move;
                }
            }
        } finally {
            executor.shutdownNow();
        }

        return bestMove;
    }

    private MoveScore evaluateMove(Board board, Move move) {
        Board copy = board.deepCopy();
        copy.applyMove(move, playerAI);

        // Quick check if it wins immediately
        if (copy.getWinner() == playerAI) {
            return new MoveScore(move, WIN_SCORE);
        }

        // If letting the opponent place in that spot is a forced immediate win for them, rank it slightly lower
        Board blockTest = board.deepCopy();
        blockTest.applyMove(move, playerOpponent);
        if (blockTest.getWinner() == playerOpponent) {
            return new MoveScore(move, WIN_SCORE - 1);
        }

        int value = minimax(copy, maxDepth - 1, false, Integer.MIN_VALUE, Integer.MAX_VALUE);
        return new MoveScore(move, value);
    }

    private List<Move> orderMoves(Board board, List<Move> moves, int player) {
        moves.sort((a, b) -> {
            Board copyA = board.deepCopy();
            copyA.applyMove(a, player);
            int scoreA = evaluate(copyA);

            Board copyB = board.deepCopy();
            copyB.applyMove(b, player);
            int scoreB = evaluate(copyB);

            return Integer.compare(scoreB, scoreA); // descending
        });
        return moves;
    }

    private int minimax(Board board, int depth, boolean isMaximizing, int alpha, int beta) {
        String key = board.toHashString() + depth + isMaximizing;
        Integer cached = memo.get(key);
        if (cached != null) {
            return cached;
        }

        int result;
        if (board.isTerminal() || depth == 0) {
            result = evaluate(board);
        } else {
            List<Move> legalMoves = board.getLegalMoves();
            if (isMaximizing) {
                int maxEval = Integer.MIN_VALUE;
                for (Move move : legalMoves) {
                    Board copy = board.deepCopy();
                    copy.applyMove(move, playerAI);
                    int eval = minimax(copy, depth - 1, false, alpha, beta);
                    maxEval = Math.max(maxEval, eval);
                    alpha = Math.max(alpha, eval);
                    if (beta <= alpha) {
                        break;
                    }
                }
                result = maxEval;
            } else {
                int minEval = Integer.MAX_VALUE;
                for (Move move : legalMoves) {
                    Board copy = board.deepCopy();
                    copy.applyMove(move, playerOpponent);
                    int eval = minimax(copy, depth - 1, true, alpha, beta);
                    minEval = Math.min(minEval, eval);
                    beta = Math.min(beta, eval);
                    if (beta <= alpha) {
                        break;
                    }
                }
                result = minEval;
            }
        }

        memo.put(key, result);
        return result;
    }

    private int evaluate(Board board) {
        int winner = board.getWinner();
        if (winner == playerAI) {
            return WIN_SCORE;
        }
        if (winner == playerOpponent) {
            return LOSS_SCORE;
        }
        if (board.isFull()) {
            return 0;
        }
        return generalizedHeuristic(board, playerAI) - generalizedHeuristic(board, playerOpponent);
    }

    private int generalizedHeuristic(Board board, int player) {
        int score = 0;
        int size = board.getSize();
        int target = board.getTarget();

        // Rows & columns
        for (int i = 0; i < size; i++) {
            score += scanLine(board, player, i, 0, 0, 1);
            score += scanLine(board, player, 0, i, 1, 0);
        }

        // Diagonals
        for (int r = 0; r <= size - target; r++) {
            for (int c = 0; c <= size - target; c++) {
                score += scanLine(board, player, r, c, 1, 1);
                score += scanLine(board, player, r, c + target - 1, 1, -1);
            }
        }

        // Some positional bias
        score += positionalBias(board, player);

        // Fork detection
        int forks = detectForks(board, player);
        if (player == playerAI) {
            score += forks * 500;
        } else {
            score -= forks * 1500;
        }

        return score;
    }

    private int scanLine(Board board, int player, int r, int c, int dr, int dc) {
        int opponent = -player;
        int size = board.getSize();
        int target = board.getTarget();

        List<Integer> cells = new ArrayList<>();
        for (int i = 0; i < target; i++) {
            int rr = r + dr * i;
            int cc = c + dc * i;
            if (rr < 0 || rr >= size || cc < 0 || cc >= size) {
                return 0;
            }
            cells.add(board.getCell(rr, cc));
        }

        long playerCount = cells.stream().filter(x -> x == player).count();
        long oppCount = cells.stream().filter(x -> x == opponent).count();
        long emptyCount = cells.stream().filter(x -> x == Board.EMPTY).count();

        // If both appear, no direct threat
        if (playerCount > 0 && oppCount > 0) {
            return 0;
        }

        int openEnds = 0;
        int startRow = r - dr, startCol = c - dc;
        int endRow = r + dr * target, endCol = c + dc * target;
        if (inBoundsEmpty(board, startRow, startCol)) {
            openEnds++;
        }
        if (inBoundsEmpty(board, endRow, endCol)) {
            openEnds++;
        }

        int lineScore = 0;
        if (playerCount > 0 && oppCount == 0) {
            if (playerCount == target - 1 && emptyCount >= 1) {
                lineScore = WIN_SCORE / 10;
            } else {
                lineScore = (int) Math.pow(10, playerCount);
            }
        } else if (oppCount > 0 && playerCount == 0) {
            if (oppCount == target - 1 && emptyCount >= 1) {
                lineScore = -(WIN_SCORE / 5);
            } else if (oppCount >= target - 2 && (oppCount + emptyCount) >= target) {
                lineScore = -(int) Math.pow(10, oppCount + 1);
            } else {
                lineScore = -(int) Math.pow(10, oppCount);
            }
        }

        lineScore *= (1 + 0.5 * openEnds);
        return lineScore;
    }

    private boolean inBoundsEmpty(Board board, int r, int c) {
        return r >= 0 && r < board.getSize() &&
               c >= 0 && c < board.getSize() &&
               board.getCell(r, c) == Board.EMPTY;
    }

    private int positionalBias(Board board, int player) {
        int size = board.getSize();
        int center = size / 2;
        int total = 0;
        for (int r = 0; r < size; r++) {
            for (int c = 0; c < size; c++) {
                if (board.getCell(r, c) == player) {
                    int dist = Math.abs(center - r) + Math.abs(center - c);
                    total += (size - dist);
                }
            }
        }
        return total;
    }

    private int detectForks(Board board, int player) {
        int threshold = 2; // # of immediate winning threats from a single move
        int forkCount = 0;
        List<Move> legals = board.getLegalMoves();
        for (Move m : legals) {
            Board sim = board.deepCopy();
            sim.applyMove(m, player);
            int threats = 0;
            for (Move n : sim.getLegalMoves()) {
                Board sim2 = sim.deepCopy();
                sim2.applyMove(n, player);
                if (sim2.getWinner() == player) {
                    threats++;
                }
            }
            if (threats >= threshold) {
                forkCount++;
            }
        }
        return forkCount;
    }

    private static class MoveScore {
        public final Move move;
        public final int score;

        public MoveScore(Move move, int score) {
            this.move = move;
            this.score = score;
        }
    }
}

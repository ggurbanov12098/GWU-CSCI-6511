package com.tictactoe;

import com.tictactoe.api.GameApiClient;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

import java.io.IOException;
import java.util.Scanner;

/**
 * OnlineGameController that offers:
 * 1) single/fixed depth
 * 2) dynamic depth
 * 3) manual depth per move
 */
public class OnlineGameController {
    private final Board board;
    private final AI ai;
    private final String gameId;
    private final String teamId;
    private final Scanner scanner;

    // 0 = normal single depth, 1 = dynamic, 2 = manual
    private final int depthMode;
    private final int baseDepth;

    public OnlineGameController(String gameId, String teamId, int initialDepth, int depthMode) {
        this.gameId = gameId;
        this.teamId = teamId;
        this.baseDepth = initialDepth; // user-chosen max depth
        this.depthMode = depthMode;
        this.scanner = new Scanner(System.in);

        try {
            // Get game details
            JsonObject gameDetails = GameApiClient.getGameDetails(gameId);
            if (!gameDetails.has("game")) {
                System.err.println("Error: 'game' field missing in response: " + gameDetails);
                throw new RuntimeException("Invalid game details response");
            }
            String gameJson = gameDetails.get("game").getAsString();
            JsonObject game = JsonParser.parseString(gameJson).getAsJsonObject();

            int boardSize = game.get("boardsize").getAsInt();
            int target = game.get("target").getAsInt();

            this.board = new Board(boardSize, target);
            this.ai = new AI(Board.PLAYER_X, initialDepth);

            updateBoardFromAPI();
        } catch (IOException | InterruptedException e) {
            throw new RuntimeException("Failed to initialize game: " + e.getMessage());
        }
    }

    private void updateBoardFromAPI() throws IOException, InterruptedException {
        try {
            JsonObject movesResponse = GameApiClient.getMoves(gameId, 100);

            // Clear local board
            for (int i = 0; i < board.getSize(); i++) {
                for (int j = 0; j < board.getSize(); j++) {
                    board.applyMove(new Move(i, j), Board.EMPTY);
                }
            }

            // Apply existing moves
            if (movesResponse.has("moves") && movesResponse.get("moves").isJsonArray()) {
                JsonArray movesArray = movesResponse.getAsJsonArray("moves");
                for (int i = 0; i < movesArray.size(); i++) {
                    JsonObject moveObj = movesArray.get(i).getAsJsonObject();
                    String moveStr = moveObj.get("move").getAsString();
                    String[] coords = moveStr.split(",");
                    int row = Integer.parseInt(coords[0]);
                    int col = Integer.parseInt(coords[1]);
                    String moveTeamId = moveObj.get("teamId").getAsString();

                    int player = moveTeamId.equals(teamId) ? Board.PLAYER_X : Board.PLAYER_O;
                    board.applyMove(new Move(row, col), player);
                }
            }
        } catch (RuntimeException re) {
            if (re.getMessage() != null && re.getMessage().contains("No moves")) {
                System.out.println("No moves yet. Starting empty board...");
                for (int i = 0; i < board.getSize(); i++) {
                    for (int j = 0; j < board.getSize(); j++) {
                        board.applyMove(new Move(i, j), Board.EMPTY);
                    }
                }
            } else {
                throw re;
            }
        }
    }

    public boolean startGame() {
        System.out.println("🎮 Online Tic-Tac-Toe Game");
        System.out.println("Game ID: " + gameId);
        System.out.println("Team ID: " + teamId);
        printBoard();

        boolean gameOver = false;
        boolean encounteredGoAway = false;

        while (!gameOver) {
            try {
                // Check local winner
                if (checkLocalWinner()) {
                    gameOver = true;
                    break;
                }

                // Check server status
                JsonObject gameDetails = GameApiClient.getGameDetails(gameId);
                if (!gameDetails.has("game")) {
                    System.err.println("No 'game' field in details. Exiting...");
                    break;
                }
                String gameJson = gameDetails.get("game").getAsString();
                JsonObject game = JsonParser.parseString(gameJson).getAsJsonObject();

                if (game.has("status") && game.get("status").getAsString().equals("DONE")) {
                    updateBoardFromAPI();
                    printBoard();
                    printResult();
                    break;
                }

                if (isMyTurn()) {
                    // Possibly adjust AI depth
                    adjustAIDepth(); // see method below

                    System.out.println("🤖 AI (depth " + getCurrentDepth() + ") is thinking...");
                    Move move = ai.getBestMove(board);
                    System.out.println("🤖 AI picked move: " + move);

                    // Attempt move
                    try {
                        GameApiClient.makeMove(gameId, teamId, move.row, move.col);
                        board.applyMove(move, Board.PLAYER_X);

                        // Check local winner
                        if (checkLocalWinner()) {
                            gameOver = true;
                            break;
                        }
                    } catch (RuntimeException re) {
                        System.err.println("❌ Move rejected by server: " + re.getMessage());
                        updateBoardFromAPI();
                        Thread.sleep(2000);
                    }
                } else {
                    System.out.println("Waiting for opponent's move...");
                    Thread.sleep(2000);
                    updateBoardFromAPI();

                    if (checkLocalWinner()) {
                        gameOver = true;
                        break;
                    }
                }

                printBoard();

            } catch (IOException e) {
                if (e.getMessage() != null && e.getMessage().contains("GOAWAY")) {
                    System.err.println("Server closed connection (GOAWAY). Rejoining...");
                    encounteredGoAway = true;
                    break;
                } else {
                    System.err.println("Error during game loop: " + e.getMessage());
                    break;
                }
            } catch (InterruptedException ie) {
                System.err.println("Interrupted: " + ie.getMessage());
                break;
            }
        }

        return encounteredGoAway;
    }

    /**
     * For the dynamic/manual depth usage.
     *  depthMode:
     *    0 = normal single depth
     *    1 = dynamic
     *    2 = manual each move
     */
    private void adjustAIDepth() {
        int movesSoFar = countMovesOnBoard();

        if (depthMode == 1) {
            // Example dynamic scheme:
            // if <8 total moves => depth=2
            // if <16 => depth=baseDepth
            // else => baseDepth+2
            if (movesSoFar < 8) {
                ai.setMaxDepth(2);
            } else if (movesSoFar < 16) {
                ai.setMaxDepth(baseDepth);
            } else {
                ai.setMaxDepth(baseDepth + 2);
            }
        } else if (depthMode == 2) {
            // manual
            System.out.print("Enter next depth to use for AI's move: ");
            Scanner sc = new Scanner(System.in);
            int chosenDepth = sc.nextInt();
            ai.setMaxDepth(chosenDepth);
        } else {
            // 0 => normal, just keep baseDepth
            ai.setMaxDepth(baseDepth);
        }
    }

    private int getCurrentDepth() {
        // For demonstration, returning just baseDepth. 
        // Or you can store the AI's current depth in a separate variable, or have "public int getMaxDepth()" in AI.
        return this.baseDepth;
    }

    private int countMovesOnBoard() {
        int movesCount = 0;
        int size = board.getSize();
        for (int r = 0; r < size; r++) {
            for (int c = 0; c < size; c++) {
                if (board.getCell(r, c) != Board.EMPTY) {
                    movesCount++;
                }
            }
        }
        return movesCount;
    }

    private boolean checkLocalWinner() {
        int w = board.getWinner();
        if (w != 0) {
            printBoard();
            printResult();
            return true;
        }
        return false;
    }

    private boolean isMyTurn() throws IOException, InterruptedException {
        JsonObject details = GameApiClient.getGameDetails(gameId);
        if (!details.has("game")) {
            return false;
        }
        String gameJson = details.get("game").getAsString();
        JsonObject game = JsonParser.parseString(gameJson).getAsJsonObject();

        if (game.has("turnteamid")) {
            String turnTeamId = game.get("turnteamid").getAsString();
            return turnTeamId.equals(teamId);
        }
        return fallbackLastMoveCheck();
    }

    private boolean fallbackLastMoveCheck() throws IOException, InterruptedException {
        try {
            JsonObject movesResponse = GameApiClient.getMoves(gameId, 1);
            if (!movesResponse.has("moves") || !movesResponse.get("moves").isJsonArray()
                || movesResponse.getAsJsonArray("moves").size() == 0) {
                return true; // no moves => we go first
            }
            JsonObject lastMove = movesResponse.getAsJsonArray("moves").get(0).getAsJsonObject();
            String lastTeamId = lastMove.get("teamId").getAsString();
            return !lastTeamId.equals(teamId);
        } catch (RuntimeException e) {
            if (e.getMessage() != null && e.getMessage().contains("No moves")) {
                return true;
            }
            throw e;
        }
    }

    private void printBoard() {
        System.out.println(board);
    }

    private void printResult() {
        int winner = board.getWinner();
        if (winner == Board.PLAYER_X) {
            System.out.println("🤖 AI wins!");
        } else if (winner == Board.PLAYER_O) {
            System.out.println("😔 Opponent wins!");
        } else {
            System.out.println("🤝 It's a draw!");
        }
    }

    public static void main(String[] args) {
        Scanner setup = new Scanner(System.in);

        System.out.println("1. Create new game (single/fixed depth)");
        System.out.println("2. Join existing game (single/fixed depth)");
        System.out.println("3. Create/Join game with DYNAMIC depth");
        System.out.println("4. Create/Join game with MANUAL per-move depth");
        System.out.print("Choice: ");
        int choice = setup.nextInt();

        boolean createNewGame = (choice == 1 || choice == 3);
        boolean dynamic = (choice == 3);
        boolean manual = (choice == 4);

        String gameId;
        String myTeamId;
        int baseDepth;

        if (createNewGame) {
            System.out.print("Enter board size: ");
            int size = setup.nextInt();
            System.out.print("Enter win target: ");
            int target = setup.nextInt();
            System.out.print("Enter your team ID: ");
            myTeamId = setup.next();
            System.out.print("Enter opponent's team ID: ");
            String opponentId = setup.next();

            try {
                gameId = GameApiClient.createGame(myTeamId, opponentId, size, target);
                System.out.println("Game created! ID: " + gameId);
            } catch (IOException | InterruptedException e) {
                System.err.println("Failed to create game: " + e.getMessage());
                return;
            }
        } else {
            System.out.print("Enter game ID: ");
            gameId = setup.next();
            System.out.print("Enter your team ID: ");
            myTeamId = setup.next();
        }

        System.out.print("Set base AI search depth (e.g., 4-8): ");
        baseDepth = setup.nextInt();

        int depthMode = 0; // default: single
        if (dynamic) {
            depthMode = 1; // dynamic
        } else if (manual) {
            depthMode = 2; // manual
        }

        while (true) {
            OnlineGameController controller = new OnlineGameController(gameId, myTeamId, baseDepth, depthMode);
            boolean goAway = controller.startGame();
            if (goAway) {
                System.out.println("Re-joining game " + gameId + " after GOAWAY...");
                try {
                    Thread.sleep(3000);
                } catch (InterruptedException ie) {
                    System.err.println("Interrupted while waiting to re-join: " + ie.getMessage());
                    break;
                }
            } else {
                break;
            }
        }

        System.out.println("Exiting program now.");
    }
}

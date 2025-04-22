package com.tictactoe;

import com.tictactoe.api.GameApiClient;
import com.tictactoe.config.Config;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.Scanner;

public class GameController {
    private TicTacToeGame game;
    private final Scanner scanner;
    private final boolean isApiMode;
    private String gameId;
    private String teamId;
    private boolean humanPlaysFirst;
    private boolean isHumanTurn;
    private boolean isPlayerO; // If we created the game, we are O (first); else X
    private final List<String> knownMoveIds = new ArrayList<>(); // Keep track of all moves we've seen

    public GameController(boolean isApiMode) {
        this.scanner = new Scanner(System.in);
        this.isApiMode = isApiMode;
        this.teamId = Config.getTeamId();
    }

    public void start() {
        if (isApiMode) {
            setupApiGame();
        } else {
            setupLocalGame();
        }
        playGame();
    }

    private void setupLocalGame() {
        System.out.println("Enter board size (n): ");
        int n = scanner.nextInt();

        System.out.println("Enter target length to win (m): ");
        int m = scanner.nextInt();

        System.out.println("Do you want to play first? (y/n): ");
        scanner.nextLine(); // Consume leftover newline
        humanPlaysFirst = scanner.nextLine().trim().equalsIgnoreCase("y");

        game = new TicTacToeGame(n, m);

        isHumanTurn = humanPlaysFirst; // initialize whose turn it is
    }

    private void setupApiGame() {
        try {
            System.out.println("Your team ID: " + teamId);
            System.out.println("Choose an option:");
            System.out.println("1. Create a new game");
            System.out.println("2. Join an existing game");
            System.out.print("Enter choice (1 or 2): ");

            int choice = scanner.nextInt();
            scanner.nextLine(); // consume newline

            if (choice == 1) {
                createNewGame();
            } else if (choice == 2) {
                joinExistingGame();
            } else {
                System.out.println("Invalid choice. Exiting...");
                System.exit(1);
            }

            // Load existing moves so our local board is fully up to date
            loadInitialMoves();

        } catch (IOException | InterruptedException e) {
            System.err.println("Failed to setup API game: " + e.getMessage());
            System.exit(1);
        }
    }

    private void createNewGame() throws IOException, InterruptedException {
        System.out.println("Enter opponent team ID: ");
        String opponentId = scanner.nextLine();

        System.out.println("Enter board size (n): ");
        int n = scanner.nextInt();

        System.out.println("Enter target length to win (m): ");
        int m = scanner.nextInt();

        gameId = GameApiClient.createGame(teamId, opponentId, n, m);
        game = new TicTacToeGame(n, m);

        System.out.println("Game created! Game ID: " + gameId);
    }

    private void joinExistingGame() throws IOException, InterruptedException {
        // Prompt the user to enter the game ID directly
        System.out.println("Enter the game ID to join: ");
        gameId = scanner.nextLine();

        // We'll fetch game details to get the board size & target
        JsonObject detailsResponse = GameApiClient.getGameDetails(gameId);
        JsonObject details = JsonParser.parseString(detailsResponse.get("game").getAsString()).getAsJsonObject();
        int n = details.get("boardsize").getAsInt();
        int m = details.get("target").getAsInt();

        // Determine if the player is X or O based on the status
        String status = details.get("status").getAsString();
        if ("O".equals(status)) {
            isPlayerO = true; // Player is O (first player)
            System.out.println("You are playing as O (the first player).");
        } else {
            isPlayerO = false; // Player is X (second player)
            System.out.println("You are playing as X (the second player).");
        }

        game = new TicTacToeGame(n, m);

        System.out.println("Joined game! Game ID: " + gameId);
    }

    /**
     * Fetch all existing moves from the API (with a large count) so our local board
     * matches the current game state, and we store those moveIds in knownMoveIds.
     */
    private void loadInitialMoves() {
        try {
            // Fetch, say, up to 1000 previous moves (adjust as needed)
            if (knownMoveIds.isEmpty()) {
                System.out.println("No moves have been made yet.");
                return; // Skip API call if no moves exist
            }
            JsonObject movesResponse = GameApiClient.getMoves(gameId, 100);
            if (!movesResponse.has("moves"))
                return;

            var movesArray = movesResponse.getAsJsonArray("moves");
            for (int i = 0; i < movesArray.size(); i++) {
                var moveObj = movesArray.get(i).getAsJsonObject();
                String moveId = moveObj.get("moveId").getAsString();
                if (knownMoveIds.contains(moveId)) {
                    continue; // skip any duplicates
                }
                knownMoveIds.add(moveId);

                int row = moveObj.get("moveX").getAsInt();
                int col = moveObj.get("moveY").getAsInt();
                game.makeMove(row, col);
            }
        } catch (IOException | InterruptedException e) {
            e.printStackTrace();
        }
    }

    private void playGame() {
        // Loop until we detect a winner or a draw
        while (true) {
            displayBoard();
            TicTacToeGame.GameResult result = game.evaluateBoard();
            if (result != TicTacToeGame.GameResult.IN_PROGRESS) {
                announceResult(result);
                break;
            }

            if (isApiMode) {
                handleApiGameTurn();
            } else {
                handleLocalGameTurn();
            }
        }
    }

    private void handleLocalGameTurn() {
        if (isHumanTurn) {
            getAndMakeHumanMove();
        } else {
            TicTacToeGame.Move aiMove = game.findBestMove();
            System.out.println("AI plays at: " + aiMove.row + "," + aiMove.col);
            game.makeMove(aiMove.row, aiMove.col);
        }
        isHumanTurn = !isHumanTurn; // Switch turn
    }

    /**
     * In API mode, we check whose turn it is by calling the gameDetails endpoint.
     * If it's our turn, we make our AI move.
     * Otherwise, we wait for the opponent to make a move (poll last move).
     */
    private void handleApiGameTurn() {
        try {
            // Check game status from the server
            JsonObject detailsFull = GameApiClient.getGameDetails(gameId);
            JsonObject details = JsonParser.parseString(detailsFull.get("game").getAsString()).getAsJsonObject();

            String turnTeamId = details.get("turnteamid").getAsString();
            String winnerTeamId = details.get("winnerteamid").isJsonNull()
                    ? null
                    : details.get("winnerteamid").getAsString();

            // Check if someone has already won
            if (winnerTeamId != null) {
                System.out.println("Game over! Winner is team: " + winnerTeamId);
                System.exit(0); // or break from the loop
            }

            // If it's our turn, do the AI move
            if (turnTeamId.trim().equalsIgnoreCase(teamId.trim())) {
                TicTacToeGame.Move aiMove = game.findBestMove();
                String newMoveId = GameApiClient.makeMove(gameId, teamId, aiMove.row, aiMove.col);
                knownMoveIds.add(newMoveId);
                game.makeMove(aiMove.row, aiMove.col);
                System.out.println("You made a move at: " + aiMove.row + "," + aiMove.col);
            } else {
                // Otherwise, wait for opponent to move
                waitForOpponentMove();
            }
        } catch (IOException | InterruptedException e) {
            System.err.println("Error during API game turn: " + e.getMessage());
        }
    }

    /**
     * Poll the "moves" endpoint (count=1) every second until a NEW move is found
     * that we haven't already applied. Then apply it to the board.
     */
    private void waitForOpponentMove() throws IOException, InterruptedException {
        System.out.println("Waiting for opponent's move...");
        while (true) {
            Thread.sleep(1000); // Poll once per second
            JsonObject movesResponse = GameApiClient.getMoves(gameId, 1);
            if (!movesResponse.has("moves")) {
                continue;
            }

            var movesArr = movesResponse.getAsJsonArray("moves");
            if (movesArr.size() == 0) {
                continue; // No moves returned
            }

            // The first element in the array is the most recent move
            var mostRecentMove = movesArr.get(0).getAsJsonObject();
            String moveId = mostRecentMove.get("moveId").getAsString();

            // If we already know about it, keep waiting
            if (knownMoveIds.contains(moveId)) {
                continue;
            }
            // Record it so we don't apply it twice
            knownMoveIds.add(moveId);

            // Apply the opponent's move
            String moveTeamId = mostRecentMove.get("teamId").getAsString();
            int row = mostRecentMove.get("moveX").getAsInt();
            int col = mostRecentMove.get("moveY").getAsInt();

            // If the move is from the opponent, apply it
            if (!moveTeamId.equals(teamId)) {
                game.makeMove(row, col);
                System.out.println("Opponent placed at: (" + (row + 1) + "," + (col + 1) + ")");
                break; // done waiting
            }
        }
    }

    private void getAndMakeHumanMove() {
        while (true) {
            System.out.println("Enter your move (row,col), 0-based: ");
            String[] input = scanner.next().split(",");
            try {
                int row = Integer.parseInt(input[0]);
                int col = Integer.parseInt(input[1]);
                if (game.makeMove(row, col)) {
                    break;
                }
                System.out.println("Invalid move, try again.");
            } catch (Exception e) {
                System.out.println("Invalid input format. Use row,col (e.g. 0,0)");
            }
        }
    }

    private void displayBoard() {
        char[][] board = game.getBoard();
        System.out.println("\nCurrent board:");

        // Print column headers
        System.out.print("  ");
        for (int j = 0; j < board.length; j++) {
            System.out.print(j + " ");
        }
        System.out.println();

        // Print rows
        for (int i = 0; i < board.length; i++) {
            System.out.print(i + " ");
            for (int j = 0; j < board[i].length; j++) {
                System.out.print(board[i][j] + " ");
            }
            System.out.println();
        }
        System.out.println();
    }

    private void announceResult(TicTacToeGame.GameResult result) {
        switch (result) {
            case X_WINS:
                System.out.println("X wins!");
                break;
            case O_WINS:
                System.out.println("O wins!");
                break;
            case DRAW:
                System.out.println("It's a draw!");
                break;
            default:
                // Shouldn't happen
                break;
        }
    }

    public static void main(String[] args) {
        System.out.println("Welcome to Generalized Tic Tac Toe!");
        System.out.print("Play against API? (y/n): ");
        Scanner scanner = new Scanner(System.in);
        boolean isApiMode = scanner.next().trim().equalsIgnoreCase("y");

        GameController controller = new GameController(isApiMode);
        controller.start();
    }
}

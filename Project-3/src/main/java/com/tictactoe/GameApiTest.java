package com.tictactoe;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.tictactoe.api.GameApiClient;

import java.util.List;

public class GameApiTest {
    public static void main(String[] args) {
        try {
            // Example usage with default values
            String gameId = GameApiClient.createGame("123", "456", 12, 6);
            System.out.println("Game created with ID: " + gameId);

            // Example usage with custom values
            gameId = GameApiClient.createGame("123", "456", 20, 10);
            System.out.println("Game created with ID: " + gameId);

            // Get all my games
            System.out.println("\nGetting all my games:");
            List<String> myGames = GameApiClient.getMyGames();
            System.out.println("My games: " + String.join(", ", myGames));

            // Get my open games
            System.out.println("\nGetting my open games:");
            List<String> myOpenGames = GameApiClient.getMyOpenGames();
            System.out.println("My open games: " + String.join(", ", myOpenGames));

            // Make a move in the game
            System.out.println("\nMaking a move in game " + gameId);
            String moveId = GameApiClient.makeMove(gameId, "123", 0, 0);
            System.out.println("Move made with ID: " + moveId);

            // Try making an invalid move
            try {
                System.out.println("\nAttempting invalid move:");
                moveId = GameApiClient.makeMove(gameId, "123", -1, 0);
                System.out.println("Move made with ID: " + moveId);
            } catch (Exception e) {
                System.out.println("Expected error: " + e.getMessage());
            }

            // Get the most recent moves
            System.out.println("\nGetting the most recent moves:");
            JsonObject movesResponse = GameApiClient.getMoves(gameId, 5);
            if (movesResponse != null && movesResponse.has("moves")) {
                JsonArray moves = movesResponse.getAsJsonArray("moves");
                System.out.println("Recent moves: " + moves);
            }

            // Get game details
            System.out.println("\nGetting game details:");
            JsonObject gameDetails = GameApiClient.getGameDetails(gameId);
            System.out.println("Game details: " + gameDetails);

            // Extract board state if it exists
            if (gameDetails.has("board")) {
                String boardState = gameDetails.get("board").getAsString();
                System.out.println("Board state: " + boardState);

                // Print the board in a more readable format
                int boardSize = gameDetails.get("boardSize").getAsInt();
                printBoard(boardState, boardSize);

                // Work directly with the board string
                System.out.println("\nAnalyzing board string directly:");

                // Example: Find all X positions
                System.out.println("X positions:");
                for (int i = 0; i < boardSize; i++) {
                    for (int j = 0; j < boardSize; j++) {
                        int index = i * boardSize + j;
                        if (index < boardState.length() && boardState.charAt(index) == 'X') {
                            System.out.println("X at position: " + i + "," + j);
                        }
                    }
                }

                // Example: Count empty cells
                int emptyCells = 0;
                for (int i = 0; i < boardSize; i++) {
                    for (int j = 0; j < boardSize; j++) {
                        int index = i * boardSize + j;
                        char cell = (index < boardState.length()) ? boardState.charAt(index) : ' ';
                        if (cell == ' ' || cell == '_' || cell == '-') {
                            emptyCells++;
                        }
                    }
                }
                System.out.println("Number of empty cells: " + emptyCells);
            }
        } catch (Exception e) {
            System.err.println("Error: " + e.getMessage());
            e.printStackTrace();
        }
    }

    private static void printBoard(String boardState, int size) {
        System.out.println("\nCurrent board:");
        for (int i = 0; i < size; i++) {
            for (int j = 0; j < size; j++) {
                int index = i * size + j;
                char cell = (index < boardState.length()) ? boardState.charAt(index) : ' ';
                System.out.print(cell + " ");
            }
            System.out.println();
        }
    }
}
package com.tictactoe.api;

import com.tictactoe.config.Config;
import com.google.gson.Gson;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.util.HashMap;
import java.util.Map;
import java.util.Arrays;
import java.util.List;

public class GameApiClient {
    private static final HttpClient client = HttpClient.newHttpClient();
    private static final Gson gson = new Gson();
    private static final String API_URL = "https://www.notexponential.com/aip2pgaming/api/index.php";

    // Simplified HTTP request handler for GET requests
    private static JsonObject executeGetRequest(Map<String, String> params) throws IOException, InterruptedException {
        String url = API_URL + "?" + buildQueryString(params);

        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(url))
                .header("x-api-key", Config.getApiKey())
                .header("userId", Config.getUserId())
                .GET()
                .build();

        return processResponse(client.send(request, HttpResponse.BodyHandlers.ofString()));
    }

    // Simplified HTTP request handler for POST requests
    private static JsonObject executePostRequest(Map<String, String> params) throws IOException, InterruptedException {
        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(API_URL))
                .header("x-api-key", Config.getApiKey())
                .header("userId", Config.getUserId())
                .header("Content-Type", "application/x-www-form-urlencoded")
                .POST(HttpRequest.BodyPublishers.ofString(buildQueryString(params)))
                .build();

        return processResponse(client.send(request, HttpResponse.BodyHandlers.ofString()));
    }

    // Common response processing logic
    private static JsonObject processResponse(HttpResponse<String> response) {
        if (response.statusCode() != 200) {
            throw new RuntimeException("API request failed with status code: " + response.statusCode());
        }

        JsonObject jsonResponse = JsonParser.parseString(response.body()).getAsJsonObject();
        if (jsonResponse.has("code") && jsonResponse.get("code").getAsString().equals("FAIL")) {
            throw new RuntimeException("API request failed: " + jsonResponse.get("message").getAsString());
        }

        return jsonResponse;
    }

    // Utility method to build query parameters
    private static String buildQueryString(Map<String, String> parameters) {
        StringBuilder queryString = new StringBuilder();
        for (Map.Entry<String, String> entry : parameters.entrySet()) {
            if (queryString.length() > 0) {
                queryString.append("&");
            }
            queryString.append(entry.getKey())
                    .append("=")
                    .append(entry.getValue());
        }
        return queryString.toString();
    }

    // Create a new game
    // Changed param names to match the API docs: team1Id, team2Id.
    public static String createGame(String team1Id, String team2Id, int boardSize, int target)
            throws IOException, InterruptedException {
        Map<String, String> params = new HashMap<>();
        params.put("type", "game");
        params.put("teamId1", team1Id);
        params.put("teamId2", team2Id);
        params.put("gameType", "TTT");
        params.put("boardSize", String.valueOf(boardSize));
        params.put("target", String.valueOf(target));

        JsonObject response = executePostRequest(params);
        return response.get("gameId").getAsString();
    }

    // Make a move in a game (multipart form-data)
    public static String makeMove(String gameId, String teamId, int row, int col)
            throws IOException, InterruptedException {
        String boundary = "Boundary" + System.currentTimeMillis();
        String CRLF = "\r\n";
        StringBuilder body = new StringBuilder();

        // type=move
        body.append("--").append(boundary).append(CRLF);
        body.append("Content-Disposition: form-data; name=\"type\"").append(CRLF).append(CRLF);
        body.append("move").append(CRLF);

        // gameId
        body.append("--").append(boundary).append(CRLF);
        body.append("Content-Disposition: form-data; name=\"gameId\"").append(CRLF).append(CRLF);
        body.append(gameId).append(CRLF);

        // teamId
        body.append("--").append(boundary).append(CRLF);
        body.append("Content-Disposition: form-data; name=\"teamId\"").append(CRLF).append(CRLF);
        body.append(teamId).append(CRLF);

        // move row,col
        body.append("--").append(boundary).append(CRLF);
        body.append("Content-Disposition: form-data; name=\"move\"").append(CRLF).append(CRLF);
        body.append(row).append(",").append(col).append(CRLF);

        body.append("--").append(boundary).append("--").append(CRLF);

        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(API_URL))
                .header("x-api-key", Config.getApiKey())
                .header("userId", Config.getUserId())
                .header("Content-Type", "multipart/form-data; boundary=" + boundary)
                .POST(HttpRequest.BodyPublishers.ofString(body.toString()))
                .build();

        JsonObject response = processResponse(client.send(request, HttpResponse.BodyHandlers.ofString()));
        return response.has("moveId") ? response.get("moveId").getAsString() : "Move successful";
    }

    // Get moves for a game
    public static JsonObject getMoves(String gameId, int count) throws IOException, InterruptedException {
        Map<String, String> params = new HashMap<>();
        params.put("type", "moves");
        params.put("gameId", gameId);
        params.put("count", String.valueOf(count));

        return executeGetRequest(params);
    }

    // Get details of a game
    public static JsonObject getGameDetails(String gameId) throws IOException, InterruptedException {
        Map<String, String> params = new HashMap<>();
        params.put("type", "gameDetails");
        params.put("gameId", gameId);

        return executeGetRequest(params);
    }

    // Get the current board as a string
    public static String getBoardString(String gameId) throws IOException, InterruptedException {
        Map<String, String> params = new HashMap<>();
        params.put("type", "boardString");
        params.put("gameId", gameId);

        JsonObject response = executeGetRequest(params);

        if (response.has("output")) {
            return response.get("output").getAsString();
        } else if (response.has("board")) {
            return response.get("board").getAsString();
        }

        throw new RuntimeException("Board string not found in response");
    }
}

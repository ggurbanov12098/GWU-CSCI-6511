package com.tictactoe.config;

import java.io.FileInputStream;
import java.io.IOException;
import java.util.Properties;

public class Config {
    private static final Properties properties = new Properties();
    private static boolean initialized = false;
    private static final String ENV_FILE = ".env";

    private static void initializeIfNeeded() {
        if (!initialized) {
            try {
                properties.load(new FileInputStream(ENV_FILE));
                initialized = true;
            } catch (IOException e) {
                System.err.println("Warning: .env file not found. Using environment variables.");
                // Fall back to environment variables
                String apiKey = System.getenv("API_KEY");
                String userId = System.getenv("USER_ID");
                String teamId = System.getenv("TEAM_ID");
                if (apiKey != null && userId != null && teamId != null) {
                    properties.setProperty("API_KEY", apiKey);
                    properties.setProperty("USER_ID", userId);
                    properties.setProperty("TEAM_ID", teamId);
                    initialized = true;
                } else {
                    throw new RuntimeException(
                            "No API credentials found. Please set API_KEY, USER_ID, and TEAM_ID environment variables or create .env file");
                }
            }
        }
    }

    public static String getApiKey() {
        initializeIfNeeded();
        return properties.getProperty("API_KEY");
    }

    public static String getUserId() {
        initializeIfNeeded();
        return properties.getProperty("USER_ID");
    }

    public static String getTeamId() {
        initializeIfNeeded();
        return properties.getProperty("TEAM_ID");
    }

    public static String getApiBaseUrl() {
        initializeIfNeeded();
        return properties.getProperty("API_BASE_URL", "https://www.notexponential.com/aip2pgaming/api/index.php");
    }
}

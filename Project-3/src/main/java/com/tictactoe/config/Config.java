package com.tictactoe.config;

import java.io.FileInputStream;
import java.io.IOException;
import java.util.Properties;

/**
 * Loads .env properties: API_KEY, USER_ID, etc.
 */
public class Config {
    private static final Properties properties = new Properties();
    private static final String ENV_FILE = ".env";

    static {
        try {
            properties.load(new FileInputStream(ENV_FILE));
        } catch (IOException e) {
            System.err.println("Error loading .env file: " + e.getMessage());
        }
    }

    public static String getApiKey() {
        return properties.getProperty("API_KEY");
    }

    public static String getUserId() {
        return properties.getProperty("USER_ID");
    }

    public static String getApiBaseUrl() {
        return properties.getProperty("API_BASE_URL");
    }
}

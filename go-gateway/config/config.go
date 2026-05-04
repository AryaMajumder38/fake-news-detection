package config

import (
    "log"
    "os"
    "github.com/joho/godotenv"
)

type Config struct {
    RedisURL     string
    MLServiceURL string
    APIKey       string
    OpenAIAPIKey string
    QdrantURL    string
    Port         string
}

func Load() Config {
    godotenv.Load() 
    redisURL := os.Getenv("REDIS_URL")
    // if redisURL == "" {
    //     log.Fatal("REDIS_URL environment variable is not set")
    // }

    mlServiceURL := os.Getenv("ML_SERVICE_URL")
    if mlServiceURL == "" {
        log.Fatal("ML_SERVICE_URL environment variable is not set")
    }

    apiKey := os.Getenv("API_KEY")
    // if apiKey == "" {
    //     log.Fatal("API_KEY environment variable is not set")
    // }

    openAIKey := os.Getenv("OPENAI_API_KEY")
    // if openAIKey == "" {
    //     log.Fatal("OPENAI_API_KEY environment variable is not set")
    // }

    qdrantURL := os.Getenv("QDRANT_URL")
    // if qdrantURL == "" {
    //     log.Fatal("QDRANT_URL environment variable is not set")
    // }

    port := os.Getenv("PORT")
    if port == "" {
        port = "8080" // sensible default
    }

    return Config{
        RedisURL:     redisURL,
        MLServiceURL: mlServiceURL,
        APIKey:       apiKey,
        OpenAIAPIKey: openAIKey,
        QdrantURL:    qdrantURL,
        Port:         port,
    }
}
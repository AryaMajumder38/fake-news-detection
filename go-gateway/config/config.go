package config

import (
	"log"
	"os"
	"time"

	"github.com/joho/godotenv"
)

type Config struct {
	RedisURL        string
	MLServiceURL    string
	APIKey          string
	IngestSecret    string
	OpenAIAPIKey    string
	QdrantURL       string
	Port            string
	MLClientTimeout time.Duration
}

func Load() Config {
	godotenv.Load()

	redisURL := os.Getenv("REDIS_URL")
	if redisURL == "" {
		log.Fatal("REDIS_URL must be set (e.g. rediss://default:password@host:port)")
	}

	mlServiceURL := os.Getenv("ML_SERVICE_URL")
	if mlServiceURL == "" {
		log.Fatal("ML_SERVICE_URL environment variable is not set")
	}

	apiKey := os.Getenv("API_KEY")
	if apiKey == "" {
		log.Fatal("API_KEY must be set (same value clients send as Bearer token)")
	}

	ingestSecret := os.Getenv("INGEST_SECRET")

	mlTimeout := 120 * time.Second
	if v := os.Getenv("ML_CLIENT_TIMEOUT"); v != "" {
		if d, err := time.ParseDuration(v); err == nil && d > 0 {
			mlTimeout = d
		}
	}

	openAIKey := os.Getenv("OPENAI_API_KEY")
	qdrantURL := os.Getenv("QDRANT_URL")

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	return Config{
		RedisURL:        redisURL,
		MLServiceURL:    mlServiceURL,
		APIKey:          apiKey,
		IngestSecret:    ingestSecret,
		OpenAIAPIKey:    openAIKey,
		QdrantURL:       qdrantURL,
		Port:            port,
		MLClientTimeout: mlTimeout,
	}
}

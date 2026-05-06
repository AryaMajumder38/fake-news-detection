package main

import (
	"context"
	"log"
	"net/http"
	"strings"
	"time"

	"github.com/AryaMajumder38/fake-news-detection/go-gateway/config"
	"github.com/AryaMajumder38/fake-news-detection/go-gateway/circuitbreaker"
	"github.com/AryaMajumder38/fake-news-detection/go-gateway/server"
	"github.com/redis/go-redis/v9"
)

func main() {
	cfg := config.Load()
	if cfg.MLServiceURL == "" {
		log.Fatal("ML_SERVICE_URL not set")
	}

	rdb := redis.NewClient(&redis.Options{
		Addr: cfg.RedisURL,
	})

	if err := rdb.Ping(context.Background()).Err(); err != nil {
		log.Fatalf("failed to connect to redis: %v", err)
	}

	cb := circuitbreaker.NewCircuitBreaker("ml-service", circuitbreaker.Config{
		FailureThreshold: 5,
		SuccessThreshold: 2,
		Timeout:          30 * time.Second,
	})

	ingestClient := &http.Client{Timeout: 2 * time.Minute}
	go scheduleIngestion(cfg, ingestClient)

	log.Println("Starting gateway...")
	server.Start(cfg, rdb, cb)
}

func scheduleIngestion(cfg config.Config, client *http.Client) {
	ticker := time.NewTicker(20 * time.Hour)
	for range ticker.C {
		ingestURL := strings.TrimRight(cfg.MLServiceURL, "/") + "/ingest"
		ctx, cancel := context.WithTimeout(context.Background(), 90*time.Second)
		req, err := http.NewRequestWithContext(ctx, http.MethodPost, ingestURL, nil)
		if err != nil {
			log.Println("ingest: build request:", err)
			cancel()
			continue
		}
		req.Header.Set("Content-Type", "application/json")
		if cfg.IngestSecret != "" {
			req.Header.Set("X-Ingest-Secret", cfg.IngestSecret)
		}
		resp, err := client.Do(req)
		cancel()
		if err != nil {
			log.Println("scheduled ingestion request failed:", err)
			continue
		}
		resp.Body.Close()
		log.Println("scheduled ingestion triggered:", resp.StatusCode)
	}
}

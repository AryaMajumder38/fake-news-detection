package main




import (
    "log"
    "time"
	"context"
    "net/http"

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

    go func() {
        ticker := time.NewTicker(20 * time.Hour)
        for range ticker.C {
            http.Post(cfg.MLServiceURL+"/ingest", "application/json", nil)
            log.Println("Scheduled ingestion triggered")
        }
    }()

    log.Println("Starting gateway...")
    server.Start(cfg, rdb, cb)
    
}
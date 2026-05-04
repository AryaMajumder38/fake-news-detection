package server

import (
    "encoding/json"
    "log"
    "net/http"

    "github.com/AryaMajumder38/fake-news-detection/go-gateway/auth"
    "github.com/AryaMajumder38/fake-news-detection/go-gateway/cache"
    "github.com/AryaMajumder38/fake-news-detection/go-gateway/circuitbreaker"
    "github.com/AryaMajumder38/fake-news-detection/go-gateway/config"
    "github.com/AryaMajumder38/fake-news-detection/go-gateway/models"
    "github.com/AryaMajumder38/fake-news-detection/go-gateway/proxy"
    "github.com/AryaMajumder38/fake-news-detection/go-gateway/ratelimit"
    "github.com/redis/go-redis/v9"
)

func analyzeHandler(cfg config.Config, cb *circuitbreaker.CircuitBreaker) http.HandlerFunc {
    return func(w http.ResponseWriter, r *http.Request) {
        var req models.AnalyzeRequest
        if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
            http.Error(w, "invalid request", http.StatusBadRequest)
            return
        }

        var result *models.AnalyzeResponse

        err := cb.Execute(func() error {
            resp, err := proxy.Forward(r.Context(), cfg.MLServiceURL, req)
            if err != nil {
                return err
            }
            result = resp
            return nil
        })

        if err != nil {
            http.Error(w, "service unavailable", http.StatusServiceUnavailable)
            return
        }

        w.Header().Set("Content-Type", "application/json")
        json.NewEncoder(w).Encode(result)
    }
}

func Start(cfg config.Config, rdb *redis.Client, cb *circuitbreaker.CircuitBreaker) {
    // 1. Create handler
    handler := analyzeHandler(cfg, cb)

    // 2. Wrap with middlewares (inside out)
	var wrapped http.Handler = handler
    wrapped = cache.Middleware(rdb)(wrapped)
    wrapped = ratelimit.Middleware(rdb)(wrapped)
    wrapped = auth.APIKeyMiddleware(cfg.APIKey)(wrapped)

    // 3. Register route
    mux := http.NewServeMux()
	mux.Handle("POST /predict", wrapped)

    // 4. Start server
    log.Printf("Gateway listening on :%s", cfg.Port)
    log.Fatal(http.ListenAndServe(":"+cfg.Port, mux))
}
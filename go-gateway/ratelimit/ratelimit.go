package ratelimit

import (
	"context"
	"net/http"
	"strconv"
	"time"
	"log"
	"strings"

	"github.com/redis/go-redis/v9"
)

const (
    maxTokens  = 10.0
    refillRate = 2.0
)


var tokenBucketScript = redis.NewScript(`
    local key = KEYS[1]
    local now = tonumber(ARGV[1])
    local max_tokens = tonumber(ARGV[2])
    local refill_rate = tonumber(ARGV[3])

    local data = redis.call("HMGET", key, "tokens", "lastRefill")
    local tokens = tonumber(data[1]) or max_tokens
    local lastRefill = tonumber(data[2]) or now

    local elapsed = now - lastRefill
    tokens = math.min(max_tokens, tokens + elapsed * refill_rate)

    if tokens < 1 then
        return {0, math.floor(tokens)}
    end

    tokens = tokens - 1

    redis.call("HSET", key, "tokens", tokens, "lastRefill", now)
    redis.call("EXPIRE", key, 3600)

    return {1, math.floor(tokens)}
`)

func Allow (rdb *redis.Client, ctx context.Context, key string) (bool, int, error){
	
	
	now:= float64(time.Now().Unix())

    result, err := tokenBucketScript.Run(ctx, rdb, []string{key},
        now, maxTokens, refillRate).Int64Slice()

    if err != nil {
        return true, 0, err  // fail open
    }

    allowed := result[0] == 1
    remaining := int(result[1])

    return allowed, remaining, nil

} 

func Middleware(rdb *redis.Client) func(http.Handler) http.Handler{
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			token := strings.TrimPrefix(r.Header.Get("Authorization"), "Bearer ")
			if token == "" {
				http.Error(w, "missing API key", http.StatusUnauthorized)
				return
			}
			key := "ratelimit:" + token

			allowed, remaining, err := Allow(rdb, r.Context(), key)

			if err != nil {
				log.Println("Redis error:", err)
				next.ServeHTTP(w, r)
				return
			}

			w.Header().Set("X-RateLimit-Remaining", strconv.Itoa(remaining))

			if !allowed {
				http.Error(w, "rate limit exceeded", http.StatusTooManyRequests)
				return
			}

			next.ServeHTTP(w, r)
		})
	}
}
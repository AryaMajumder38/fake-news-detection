package cache

import (
	"context"
	"crypto/md5"
	"encoding/json"
	"fmt"
	"log"
	"time"
	"net/http"
	"bytes"
	"io"

	"github.com/AryaMajumder38/fake-news-detection/go-gateway/models"
	"github.com/redis/go-redis/v9"
)

const (
	ttl = 1 * time.Hour
)

type responseRecorder struct {
    http.ResponseWriter  // embedded interface
    body bytes.Buffer
	status int 
}

func (rec *responseRecorder) Write (b []byte)(int , error){
	rec.body.Write(b)
	return rec.ResponseWriter.Write(b) 
}

func (rec *responseRecorder) WriteHeader(statusCode int) {
	rec.status = statusCode
	rec.ResponseWriter.WriteHeader(statusCode)
}


func CacheKey(text, source string) string {
	hash := md5.Sum([]byte(text + source))
	return fmt.Sprintf("cache:%x", hash)
}

func Get(ctx context.Context, rdb *redis.Client, key string) (*models.AnalyzeResponse, error){

	value, err := rdb.Get(ctx,key).Result()	
	if err == redis.Nil {
		return nil,nil   // key doesnt exist
	}

	if err != nil {
        return nil, err
    }

	
	log.Print("cache hit:", key)

	var resp models.AnalyzeResponse

	err = json.Unmarshal([]byte(value),&resp)

	if err != nil{
		log.Print("failed to unmarshall response")
		return nil,err
	}

	return &resp, nil

}

func Set(ctx context.Context, rdb *redis.Client, key string, resp *models.AnalyzeResponse) error {
    // marshal to JSON, store in Redis with TTL

	data, err := json.Marshal(resp)
	if err != nil{
		log.Print("failed to marshal response")
		return err
	}

	err = rdb.Set(ctx,key,data,ttl).Err()
	if err != nil {
		log.Print("redis set error",err)
		return err
	}

	
	log.Print("setting the response in cache is successful")
	
	return nil

}

func Middleware(rdb *redis.Client) func(http.Handler) http.Handler {
    return func(next http.Handler) http.Handler {
        return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {

			bodyBytes, err := io.ReadAll(r.Body)
			if err != nil {
   			 http.Error(w, "invalid request", http.StatusBadRequest)
   			 return
			}

			r.Body = io.NopCloser(bytes.NewBuffer(bodyBytes)) // restore for next handler

			var req models.AnalyzeRequest
			if err := json.Unmarshal(bodyBytes, &req); err != nil {
    		http.Error(w, "invalid request", http.StatusBadRequest)
    		return
			}

			text:= req.Text

			ctx :=r.Context()

			key := CacheKey(text, req.SourceURL)

			resp, err := Get(ctx, rdb,key)
			if err != nil {
                log.Println("cache error:", err)
            }

			if resp != nil{
				log.Println("key present ")
				w.Header().Set("Content-Type", "application/json")
				json.NewEncoder(w).Encode(resp)
				return
			}

			recorder := &responseRecorder{
				ResponseWriter: w,
				status: http.StatusOK,
			}

			next.ServeHTTP(recorder, r)

			if recorder.status != http.StatusOK {
				return // do NOT cache errors
			}
	
			var respo models.AnalyzeResponse
			if err := json.Unmarshal(recorder.body.Bytes(), &respo); err != nil {
				log.Println("cache: failed to unmarshal response for storing")
				return
			}
			if err := Set(ctx, rdb, key, &respo); err != nil {
				log.Println("cache set failed:", err)
			}
           
        })
    }
}





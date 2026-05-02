package circuitbreaker

import (
	"fmt"
	"sync"
	"time"
	"net/http"
	"bytes"


	//"golang.org/x/text/cases"
)
const (
    StateClosed   int32 = 0
    StateOpen     int32 = 1
    StateHalfOpen int32 = 2
)

type responseRecorder struct {
    http.ResponseWriter  // embedded interface
    body bytes.Buffer
	status int 
}

func (rec *responseRecorder) Write(b []byte) (int, error) {
    rec.body.Write(b)
    return rec.ResponseWriter.Write(b)
}

func (rec *responseRecorder) WriteHeader(statusCode int) {
    rec.status = statusCode
    rec.ResponseWriter.WriteHeader(statusCode)
}


type CircuitBreaker struct {
	name string

	mutex sync.Mutex
	state int32

	failureCount int32
	successCount int32

	failureThreshold int32
	successThreshold int32

	timeout time.Duration
	lastFailureTime time.Time

	halfOpenInFlight bool

}


type Config struct {
	FailureThreshold int32
	SuccessThreshold int32
	Timeout          time.Duration
}

func NewCircuitBreaker(name string, cfg Config) *CircuitBreaker {
	if cfg.FailureThreshold <= 0 {
		cfg.FailureThreshold = 5
	}
	if cfg.SuccessThreshold <= 0 {
		cfg.SuccessThreshold = 1
	}
	if cfg.Timeout <= 0 {
		cfg.Timeout = 5 * time.Second
	}

	if name == "" {
		name = "default"
	}

	return &CircuitBreaker{
		name:             name,
		state:            StateClosed,
		failureThreshold: cfg.FailureThreshold,
		successThreshold: cfg.SuccessThreshold,
		timeout:          cfg.Timeout,
		lastFailureTime:  time.Time{},
	}
}


func (cb *CircuitBreaker) Execute(fn func() error) error {
	cb.mutex.Lock()

	if cb.state == StateOpen {
		if time.Since(cb.lastFailureTime) > cb.timeout {
			cb.state = StateHalfOpen
			cb.successCount = 0
			cb.halfOpenInFlight = false
		} else {
			cb.mutex.Unlock()
			return fmt.Errorf("circuit breaker %s is open", cb.name)
		}
	}

	if cb.state == StateHalfOpen {
		if cb.halfOpenInFlight {
			cb.mutex.Unlock()
			return fmt.Errorf("circuit breaker %s half-open (busy)", cb.name)
		}
		cb.halfOpenInFlight = true
	}

	cb.mutex.Unlock()

	err := fn()

	cb.mutex.Lock()
	if cb.state == StateHalfOpen {
		cb.halfOpenInFlight = false
	}
	cb.mutex.Unlock()


	if err != nil {
		cb.onFailure()
		return err
	}

	cb.onSuccess()
	return nil
}

func (cb *CircuitBreaker) onFailure(){
	cb.mutex.Lock()
	defer cb.mutex.Unlock()
	cb.failureCount++
	

	if (cb.failureCount)>=  cb.failureThreshold{
		cb.state=StateOpen
		cb.lastFailureTime=time.Now()
	}	
}

func (cb *CircuitBreaker) onSuccess(){
	cb.mutex.Lock()
	defer cb.mutex.Unlock()

	if cb.state == StateHalfOpen {
    cb.successCount++
    if cb.successCount >= cb.successThreshold {
        cb.state = StateClosed
        cb.failureCount = 0
        cb.successCount = 0
    	}
	} else {
    cb.failureCount = 0
	}
}


func Middleware(cb *CircuitBreaker) func(http.Handler) http.Handler {
    return func(next http.Handler) http.Handler {
        return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {

            err := cb.Execute(func() error {
                recorder := &responseRecorder{ResponseWriter: w, status: http.StatusOK}
                next.ServeHTTP(recorder, r)
                if recorder.status >= 500 {
                    return fmt.Errorf("downstream returned %d", recorder.status)
                }
                return nil
            })

            if err != nil {
                http.Error(w, "service unavailable", http.StatusServiceUnavailable)
                return
            }
        })
    }
}
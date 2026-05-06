package proxy

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"

	"github.com/AryaMajumder38/fake-news-detection/go-gateway/models"
)

const bodyErrMax = 512

// Forward POSTs the analyze request to the ML service /predict endpoint using mlHTTP.
// mlHTTP must use a non-zero Timeout (RAG can run tens of seconds).
func Forward(ctx context.Context, mlHTTP *http.Client, mlURL string, req models.AnalyzeRequest) (*models.AnalyzeResponse, error) {
	if mlHTTP == nil {
		return nil, fmt.Errorf("ml http client is nil")
	}

	data, err := json.Marshal(req)
	if err != nil {
		return nil, err
	}

	url := strings.TrimRight(mlURL, "/") + "/predict"

	httpReq, err := http.NewRequestWithContext(ctx, http.MethodPost, url, bytes.NewReader(data))
	if err != nil {
		return nil, err
	}

	httpReq.Header.Set("Content-Type", "application/json")

	resp, err := mlHTTP.Do(httpReq)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}

	if resp.StatusCode < 200 || resp.StatusCode > 299 {
		return nil, fmt.Errorf("ml service %s: status %d: %s", url, resp.StatusCode, truncateForErr(body))
	}

	var out models.AnalyzeResponse
	if err := json.Unmarshal(body, &out); err != nil {
		return nil, fmt.Errorf("ml service: decode response: %w", err)
	}

	return &out, nil
}

func truncateForErr(b []byte) string {
	s := string(b)
	if len(s) <= bodyErrMax {
		return s
	}
	return s[:bodyErrMax] + "…"
}

package proxy

import (
	"bytes"
	"context"
	"encoding/json"
	"net/http"
	"io"
	"fmt"
	"strings"
	"github.com/AryaMajumder38/fake-news-detection/go-gateway/models"
)


func Forward(ctx context.Context, mlURL string, req models.AnalyzeRequest) (*models.MLResponse, error) {
	data, err := json.Marshal(req)
	if err != nil {
		return nil, err
	}

	url := strings.TrimRight(mlURL, "/") + "/predict"

	httpReq, err := http.NewRequestWithContext(
		ctx,
		"POST",
		url,
		bytes.NewBuffer(data),
	)
	if err != nil {
		return nil, err
	}

	httpReq.Header.Set("Content-Type", "application/json")

	client := &http.Client{}

	resp, err := client.Do(httpReq)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 500 {
		return nil, fmt.Errorf("ml service error: %d", resp.StatusCode)
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}

	var mlResp models.MLResponse
	if err := json.Unmarshal(body, &mlResp); err != nil {
		return nil, err
	}

	return &mlResp, nil
}
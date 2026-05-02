package models

// AnalyzeRequest is what the Chrome extension sends to the gateway
type AnalyzeRequest struct {
	Text        string `json:"text"`
	SourceURL   string `json:"source_url"`
	ArticleDate string `json:"article_date"`
}

// MLRequest is what the gateway forwards to the Python ML service
type MLRequest struct {
	Text string `json:"text"`
    SourceURL string `json:"source_url"`
}

// MLResponse is what the Python ML service sends back
type MLResponse struct {
	Verdict          string  `json:"verdict"`
	Confidence       float64 `json:"confidence"`
	CredibilityScore float64 `json:"credibility_score"`
}

// FactCheck represents a single fact-check result from Qdrant
type FactCheck struct {
    Title     string `json:"title"`
    URL       string `json:"url"`
    Publisher string `json:"publisher"`
    Published string `json:"published"`
    Claimant  string `json:"claimant"`
    Verdict   string `json:"verdict"`
}
// RelatedArticle represents a related real news article from Qdrant
type RelatedArticle struct {
	Title  string `json:"title"`
	URL    string `json:"url"`
	Source string `json:"source"`
}

// AnalyzeResponse is the enriched response sent back to the Chrome extension
type AnalyzeResponse struct {
	Verdict          string           `json:"verdict"`
	Confidence       float64          `json:"confidence"`
	CredibilityScore float64          `json:"credibility_score"`
	Domain           string           `json:"domain"`
	ArticleDate      string           `json:"article_date"`
	StaleWarning     bool             `json:"stale_warning"`
	Reasoning        string           `json:"reasoning"`
	FlaggedSentences []string         `json:"flagged_sentences"`
	FactChecks       []FactCheck      `json:"fact_checks"`
	RelatedArticles  []RelatedArticle `json:"related_articles"`
}
from urllib.parse import urlparse

DOMAIN_SCORES = {
    # International wire services
    "reuters.com": 0.95,
    "apnews.com": 0.95,
    "ptinews.com": 0.95,

    # International news
    "bbc.com": 0.90,
    "bbc.co.uk": 0.90,
    "theguardian.com": 0.90,
    "aljazeera.com": 0.88,
    "nytimes.com": 0.85,
    "washingtonpost.com": 0.85,
    "thehill.com": 0.80,
    "cnn.com": 0.80,
    "foxnews.com": 0.70,
    "politico.com": 0.80,

    # Indian news
    "thehindu.com": 0.90,
    "indianexpress.com": 0.90,
    "ndtv.com": 0.85,
    "hindustantimes.com": 0.85,
    "ddnews.gov.in": 0.90,

    # Official sources
    "who.int": 0.98,
    "cdc.gov": 0.98,
    "un.org": 0.95,

    # Fact-checkers
    "snopes.com": 0.95,
    "factcheck.org": 0.95,
    "politifact.com": 0.93,
    "boomlive.in": 0.95,
    "altnews.in": 0.95,
    "vishvasnews.com": 0.90,

    # Known misinformation
    "infowars.com": 0.05,
    "naturalnews.com": 0.05,
    "breitbart.com": 0.20,
    "thegatewaypundit.com": 0.05,
    "dailywire.com": 0.30,
    "beforeitsnews.com": 0.05,
    "yournewswire.com": 0.05,
}

def normalize_domain(domain: str) -> str:
    domain = domain.lower()

    if domain.startswith("www."):
        domain = domain[4:]

    # remove port if present
    domain = domain.split(":")[0]

    return domain

def get_credibility_score(url: str) -> float:
    parsed_url = urlparse(url)
    domain = normalize_domain(parsed_url.netloc)
    return DOMAIN_SCORES.get(domain, 0.4)


if __name__ == "__main__":
    test_urls = [
        "https://reuters.com/article/123",
        "https://www.bbc.com/news/world",
        "https://infowars.com/fake-story",
        "https://unknownsite.com/article",
        "https://boomlive.in/fact-check/123",
    ]
    
    for url in test_urls:
        score = get_credibility_score(url)
        print(f"{url} → {score}")
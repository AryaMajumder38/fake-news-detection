import feedparser


def parse_rss(url: str, source_name: str) -> list[dict]:
    feed = feedparser.parse(url)
    articles = []
    for entry in feed.entries:
        articles.append({
            "source": source_name,
            "url": entry.link,
            "title": entry.title,
            "published": getattr(entry, "published", None),
            "summary": getattr(entry, "summary", None),
        })
    return articles



if __name__ == "__main__":
    articles = parse_rss(
        "http://feeds.bbci.co.uk/news/rss.xml",
        "BBC"
    )
    print(f"Fetched {len(articles)} articles")
    print(articles[0])
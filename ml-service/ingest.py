import requests
from sentence_transformers import SentenceTransformer
from app.rss_parser import parse_rss

from qdrant_client.models import PointStruct
import os
from dotenv import load_dotenv
from collections import Counter
import hashlib
import spacy
from collections import OrderedDict
from qdrant_client.models import VectorParams, Distance
from qdrant_conn import get_qdrant_client

NEWS_API_KEY = os.getenv("NEWS_API_KEY")

client = get_qdrant_client()

#load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_FACT_CHECK_API_KEY")

model = None

def get_model():
    global model
    if model is None:
        model = SentenceTransformer("all-MiniLM-L6-v2")
    return model

def url_to_id(url: str) -> int:
    return int(hashlib.md5(url.encode()).hexdigest()[:8], 16)

RSS_SOURCES = [
    ("https://feeds.reuters.com/reuters/topNews", "Reuters"),
    ("http://feeds.bbci.co.uk/news/rss.xml", "BBC"),
    ("https://www.aljazeera.com/xml/rss/all.xml", "Al Jazeera"),
    ("https://feeds.npr.org/1001/rss.xml", "NPR"),
    ("https://rss.app/feeds/tVJ8bEoFBXaA0YHb.xml", "AP News"),
    ("https://www.theguardian.com/world/rss", "The Guardian"),
    ("https://www.who.int/rss-feeds/news-english.xml", "WHO"),
     ("https://tools.cdc.gov/api/v2/resources/media/316422.rss", "CDC"),
    ("https://www.who.int/rss-feeds/news-english.xml", "WHO"),
    ("https://tools.cdc.gov/api/v2/resources/media/403372.rss", "CDC"),
    ("https://feeds.bbci.co.uk/news/health/rss.xml", "BBC"),
    ("https://www.reutersagency.com/feed/?best-topics=health", "Reuters"),
    ("https://news.google.com/rss/search?q=measles+outbreak", "Google News"),
    ("https://news.google.com/rss/search?q=health+outbreak", "Google News"),
    ("https://feeds.foxnews.com/foxnews/latest", "Fox News"),
    ("https://www.cbsnews.com/latest/rss/main", "CBS News"),
    ("https://abcnews.go.com/abcnews/topstories", "ABC News"),
    ("https://feeds.washingtonpost.com/rss/world", "Washington Post"),
    ("https://www.cnbc.com/id/100003114/device/rss/rss.html", "CNBC"),
    ("https://feeds.feedburner.com/time/topstories", "TIME"),
    ("https://www.economist.com/the-world-this-week/rss.xml", "The Economist"),
    
    # Indian news
    ("https://www.thehindu.com/news/feeder/default.rss", "The Hindu"),
    ("https://indianexpress.com/feed/", "Indian Express"),
    ("https://feeds.feedburner.com/ndtvnews-top-stories", "NDTV"),
    ("https://www.hindustantimes.com/feeds/rss/world-news/rssfeed.xml", "Hindustan Times"),
    
    # Fact-checkers
    ("https://www.snopes.com/feed/", "Snopes"),
    ("https://www.factcheck.org/feed/", "FactCheck.org"),
    ("https://www.politifact.com/rss/all/", "PolitiFact"),
    ("https://www.boomlive.in/fact-check/feed/", "Boom Live"),
    ("https://www.altnews.in/feed/", "Alt News"),
    
    # Health / official
    ("https://www.cdc.gov/media/rss/all-cdc-rss-feeds.html", "CDC"),
    ("https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/press-releases/rss.xml", "FDA"),
    
    # Tech / science
    ("https://www.scientificamerican.com/feed", "Scientific American"),
    ("https://feeds.npr.org/1004/rss.xml", "NPR Science"),
]


COMMON_MISINFO_TOPICS = [
    "election fraud", "voting machines", "dominion",
    "covid vaccine", "mrna", "vaccine side effects",
    "5g coronavirus", "bill gates microchip",
    "climate change hoax", "global warming fake",
    "ukraine russia war", "biolabs ukraine",
    "moon landing", "flat earth",
    "chemtrails", "fluoride conspiracy",
    "reptilians", "great reset",
    "ai deepfake", "ai election",
    "vaccine autism", "vaccine deaths",
    "hunter biden laptop", "trump indictment",
    "covid origin lab leak", "wuhan",
    "mass shooting hoax", "crisis actors",
    "9/11 conspiracy", "deep state",
    "epstein client list", "clinton emails",
]


def fetch_newsapi_articles():
    if not NEWS_API_KEY:
        print("No NEWS_API_KEY found")
        return []

    url = "https://newsapi.org/v2/everything"

    queries = ["health outbreak", "measles", "vaccine", "disease"]

    articles = []

    for query in queries:
        params = {
            "q": query,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": 20,
            "apiKey": NEWS_API_KEY,
        }

        try:
            res = requests.get(url, params=params, timeout=5)
            res.raise_for_status()
            data = res.json()
        except Exception as e:
            print(f"NewsAPI failed for {query}: {e}")
            continue

        for item in data.get("articles", []):
            text = (item.get("title") or "") + " " + (item.get("description") or "")

            embedding = get_model().encode(text).tolist()

            articles.append({
                "text": text,
                "embedding": embedding,
                "source": item.get("source", {}).get("name", "NewsAPI"),
                "url": item.get("url"),
                "title": item.get("title"),
                "published": item.get("publishedAt"),
                "entry_type": "news",
            })

    print(f"Fetched {len(articles)} NewsAPI articles")
    return articles


def ingest():
    all_articles=[]

    for url,source_name in RSS_SOURCES:
        articles=parse_rss(url,source_name)
        for article in articles:
            text=article['title']+" "+(article['summary']or "")
            embedding=get_model().encode(text).tolist()
            entry_type = classify_source(article['source'])
            all_articles.append({
                "text": text,
                "embedding": embedding,
                "source": article['source'],
                "url": article['url'],
                "title": article['title'],
                "published": article['published'],
                "entry_type": entry_type,
            })
    print(f"Fetched and embedded {len(all_articles)} articles")

    newsapi_articles = fetch_newsapi_articles()
    all_articles.extend(newsapi_articles)
    return all_articles


def ensure_collection():
    collections = client.get_collections().collections
    names = [c.name for c in collections]

    if "knowledge_base" not in names:
        print("Creating collection...")
        client.create_collection(
            collection_name="knowledge_base",
            vectors_config=VectorParams(
                size=384,  # all-MiniLM-L6-v2
                distance=Distance.COSINE,
            ),
        )



def upsert_to_qdrant(articles):
    points = []
    for i, article in enumerate(articles):
        points.append(
            PointStruct(
                id=url_to_id(article['url']),
                vector=article['embedding'],
                payload={
                    "text": article['text'],
                    "source": article['source'],
                    "url": article['url'],
                    "title": article['title'],
                    "published": article['published'],
                    "verdict": article.get('verdict', None),
                    "publisher": article.get('publisher', None),
                    "entry_type": article.get('entry_type', "unknown"),
                }
            )
        )
    
    client.upsert(
        collection_name="knowledge_base",
        points=points,
        wait=True
    )
    print(f"Upserted {len(points)} points to Qdrant")



def fetch_fact_checks(topics: list[str]) -> list[dict]:
    all_claims = []
    
    for topic in topics:
        url = "https://factchecktools.googleapis.com/v1alpha1/claims:search"
        params = {
            "query": topic,
            "key": GOOGLE_API_KEY,
            "pageSize": 10,
            "languageCode": "en"
        }
        try:
            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            print(f"Fact check API failed for topic {topic}: {e}")
            continue
        
        for claim in data.get("claims", []):
            review = claim.get("claimReview", [{}])[0]
            text=claim.get("text","")
            embedding= get_model().encode(text).tolist()
            all_claims.append({
                "text": claim.get("text", ""),
                "embedding": embedding,
                "title": text[:100],
                "claimant": claim.get("claimant", ""),
                "verdict": review.get("textualRating", ""),
                "publisher": review.get("publisher", {}).get("name", ""),
                "url": review.get("url", ""),
                "source": "Google Fact Check",
                "published": review.get("reviewDate", None),
                "entry_type": "fact-check",   
            })
    
    print(f"Fetched {len(all_claims)} fact-checked claims")
    return all_claims





nlp = spacy.load("en_core_web_sm")

def extract_topics(articles: list[dict], top_n: int = 20) -> list[str]:
    topics = []
    for article in articles:
        title = article.get('title', '')
        doc = nlp(title)
        for ent in doc.ents:
            if ent.label_ in ("PERSON", "ORG", "GPE", "EVENT", "NORP", "LOC"):
                topics.append(ent.text.lower())
    
    counts = Counter(topics)
    return [topic for topic, _ in counts.most_common(top_n)]


def get_existing_topics(top_n: int = 20) -> list[str]:
    try:
        existing_titles = []
        next_page = None

        while True:
            results, next_page = client.scroll(
                collection_name="knowledge_base",
                limit=100,
                offset=next_page,
                with_payload=True,
                with_vectors=False
            )
            for point in results:
                title = point.payload.get("title", "")
                if title:
                    existing_titles.append({"title": title})

            if next_page is None:
                break

        return extract_topics(existing_titles, top_n=top_n)

    except Exception:
        # ✅ If collection doesn't exist → just return empty
        return []

def classify_source(source: str) -> str:
    s = source.lower()

    if "who" in s or "cdc" in s:
        return "official"

    return "news"



if __name__ == "__main__":
    articles = ingest()

    ensure_collection()

    
    new_topics = extract_topics(articles)
    existing_topics = get_existing_topics()
    
    
    combined_topics = list(dict.fromkeys(new_topics + existing_topics))[:30]
    print(f"Combined topics: {combined_topics}")
    
    fact_checks = fetch_fact_checks(combined_topics)
    
    all_data = articles + fact_checks
    upsert_to_qdrant(all_data)
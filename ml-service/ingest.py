import requests
from sentence_transformers import SentenceTransformer
from app.rss_parser import parse_rss
from init_qdrant import client
from qdrant_client.models import PointStruct
import os
from dotenv import load_dotenv
from collections import Counter
import hashlib
import spacy
from collections import OrderedDict

load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_FACT_CHECK_API_KEY")

model = SentenceTransformer("all-MiniLM-L6-v2")

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
]


def ingest():
    all_articles=[]

    for url,source_name in RSS_SOURCES:
        articles=parse_rss(url,source_name)
        for article in articles:
            text=article['title']+" "+(article['summary']or "")
            embedding=model.encode(text).tolist()
            all_articles.append({
                "text": text,
                "embedding": embedding,
                "source": article['source'],
                "url": article['url'],
                "title": article['title'],
                "published": article['published'],
            })
    print(f"Fetched and embedded {len(all_articles)} articles")
    return all_articles



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
        response = requests.get(url, params=params)
        data = response.json()
        
        for claim in data.get("claims", []):
            review = claim.get("claimReview", [{}])[0]
            text=claim.get("text","")
            embedding= model.encode(text).tolist()
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



if __name__ == "__main__":
    articles = ingest()
    
    new_topics = extract_topics(articles)
    existing_topics = get_existing_topics()
    
    
    combined_topics = list(dict.fromkeys(new_topics + existing_topics))[:30]
    print(f"Combined topics: {combined_topics}")
    
    fact_checks = fetch_fact_checks(combined_topics)
    
    all_data = articles + fact_checks
    upsert_to_qdrant(all_data)
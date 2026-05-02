from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

client = QdrantClient(host="qdrant", port=6333)

def init_collection():
    if client.collection_exists(collection_name="knowledge_base"):
        print("Collection already exists — skipping creation")
        return

    client.create_collection(
        collection_name="knowledge_base",
        vectors_config=VectorParams(size=384, distance=Distance.COSINE),
    )

    print("Collection created")

if __name__ == "__main__":
    init_collection()
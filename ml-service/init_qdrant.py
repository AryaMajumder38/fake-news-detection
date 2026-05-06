from qdrant_client.models import Distance, VectorParams

from qdrant_conn import get_qdrant_client

client = get_qdrant_client()

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
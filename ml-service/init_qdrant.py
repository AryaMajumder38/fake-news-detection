from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

client = QdrantClient(url="http://localhost:6333")

def init_collection():

    if client.collection_exists(collection_name="knowledge_base"):
        client.delete_collection(collection_name="knowledge_base")

    client.create_collection(
        collection_name="knowledge_base",
        vectors_config=VectorParams(size=384, distance=Distance.COSINE),
    )

    print("Collection created")

if __name__ == "__main__":
    init_collection()
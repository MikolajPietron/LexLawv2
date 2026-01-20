from qdrant_client import QdrantClient
from qdrant_client.models import PayloadSchemaType
from dotenv import load_dotenv
import os

load_dotenv()

client = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY")
)

# Dodaj indeks na origin_id (integer)
client.create_payload_index(
    collection_name="polish_law_e5",
    field_name="origin_id",
    field_schema=PayloadSchemaType.INTEGER
)

print("✅ Indeks origin_id dodany!")
import json
import os
os.environ["HF_HOME"] = "E:\\hf_cache"

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from tqdm import tqdm
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

load_dotenv()

# Konfiguracja - ZMIEŃ NA NOWY VPS
NEW_QDRANT_URL = os.getenv("QDRANT_URL")  # lub nowe IP
NEW_QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

DATA_PATH = "full_dataset.jsonl"
COLLECTION_NAME = "polish_law_e5"

client = QdrantClient(url=NEW_QDRANT_URL, api_key=NEW_QDRANT_API_KEY, timeout=120)

def get_existing_origin_ids():
    """Pobiera wszystkie origin_id które już są w bazie."""
    print("📊 Pobieram listę istniejących dokumentów...")
    
    existing_ids = set()
    offset = None
    
    while True:
        results, offset = client.scroll(
            collection_name=COLLECTION_NAME,
            limit=10000,
            offset=offset,
            with_payload=["origin_id"]
        )
        
        for point in results:
            existing_ids.add(point.payload.get("origin_id"))
        
        if offset is None:
            break
    
    print(f"✅ Znaleziono {len(existing_ids):,} unikalnych dokumentów w bazie")
    return existing_ids

def count_missing_documents(existing_ids):
    """Liczy ile dokumentów trzeba jeszcze dodać."""
    total = 0
    missing = 0
    
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                total += 1
                doc = json.loads(line)
                if doc["id"] not in existing_ids:
                    missing += 1
    
    print(f"📂 Wszystkich dokumentów: {total:,}")
    print(f"📂 Brakujących: {missing:,}")
    return missing

# Sprawdź co trzeba dodać
existing = get_existing_origin_ids()
missing = count_missing_documents(existing)

print(f"\n🚀 Do dodania: {missing:,} dokumentów")
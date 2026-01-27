import os
from qdrant_client import QdrantClient
from qdrant_client.models import OptimizersConfigDiff
from dotenv import load_dotenv

load_dotenv()

client = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY"),
    timeout=300
)

print("🔧 Wymuszam przebudowę indeksu...")

# Ustaw indexing_threshold na 0 - wymusi natychmiastowe indeksowanie
client.update_collection(
    collection_name="polish_law_e5",
    optimizer_config=OptimizersConfigDiff(
        indexing_threshold=0
    )
)

print("✅ Konfiguracja zaktualizowana")
print("⏳ Sprawdzam czy indeksowanie ruszyło...")

import time
for i in range(10):
    time.sleep(15)
    info = client.get_collection("polish_law_e5")
    print(f"[{i+1}] Status: {info.status} | Indexed: {info.indexed_vectors_count:,}/{info.points_count:,}")
    
    if info.status == "green":
        print("\n✅ GOTOWE!")
        break
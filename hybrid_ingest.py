import json
import os
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct, PayloadSchemaType
from tqdm import tqdm
import re
from dotenv import load_dotenv
import torch
from sentence_transformers import SentenceTransformer

load_dotenv()

# --- KONFIGURACJA ---
DATA_PATH = "data/full_dataset.json"
COLLECTION_NAME = "polish_law_e5"  # Nowa kolekcja dla nowego modelu
MODEL_NAME = "intfloat/multilingual-e5-large"  # Lepszy model!
VECTOR_SIZE = 1024  # E5-large ma 1024 wymiarów

CHUNK_SIZE = 512
CHUNK_OVERLAP = 128
MIN_CHUNK_SIZE = 50
BATCH_SIZE = 32  # Mniejszy batch dla większego modelu (VRAM)

# Sprawdź GPU
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print(f"🖥️ Używam: {DEVICE.upper()}")

def clean_legal_text(text):
    """Czyści tekst prawniczy."""
    if not text:
        return ""
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^\w\s\.\,\;\:\-\(\)\[\]§„"\"\'\/\%\@\+\=\!\?\*\#]+', '', text)
    return text.strip()

def smart_legal_chunker(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """Inteligentny podział na chunki."""
    if len(text) <= chunk_size:
        return [text] if len(text) >= MIN_CHUNK_SIZE else []
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        if end >= len(text):
            chunk = text[start:]
            if len(chunk) >= MIN_CHUNK_SIZE:
                chunks.append(chunk)
            break
        
        safe_end = end
        for sep in ['. ', '.\n', '; ', ':\n']:
            pos = text.rfind(sep, start + chunk_size // 2, end)
            if pos != -1:
                safe_end = pos + len(sep)
                break
        
        chunk = text[start:safe_end].strip()
        if len(chunk) >= MIN_CHUNK_SIZE:
            chunks.append(chunk)
        
        start = safe_end - overlap
    
    return chunks

def create_enriched_text(chunk, doc):
    """Wzbogaca chunk o metadane do embeddingu.
    
    Dla E5 używamy prefixu 'passage:' dla dokumentów.
    """
    context_parts = []
    
    court_map = {
        "COMMON": "sąd powszechny",
        "SUPREME": "Sąd Najwyższy",
        "CONSTITUTIONAL_TRIBUNAL": "Trybunał Konstytucyjny"
    }
    if doc.get("court_type") in court_map:
        context_parts.append(court_map[doc["court_type"]])
    
    jtype_map = {
        "SENTENCE": "wyrok",
        "DECISION": "postanowienie",
        "RESOLUTION": "uchwała",
        "REASONS": "uzasadnienie"
    }
    if doc.get("judgment_type") in jtype_map:
        context_parts.append(jtype_map[doc["judgment_type"]])
    
    keywords = doc.get("keywords", [])[:3]
    context_parts.extend(keywords)
    
    # E5 wymaga prefixu "passage:" dla dokumentów
    if context_parts:
        return f"passage: [{' | '.join(context_parts)}] {chunk}"
    return f"passage: {chunk}"

def main():
    print("📂 Ładowanie danych...")
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        documents = json.load(f)
    print(f"✅ Załadowano {len(documents)} dokumentów")
    
    print(f"🔧 Ładowanie modelu: {MODEL_NAME}")
    print("⏳ To może potrwać chwilę przy pierwszym uruchomieniu...")
    
    model = SentenceTransformer(MODEL_NAME, device=DEVICE)
    model.max_seq_length = 512  # Limit dla E5
    print(f"✅ Model załadowany na {DEVICE.upper()}")
    
    print("🗄️ Łączenie z Qdrant Cloud...")
    client = QdrantClient(
        url=os.getenv("QDRANT_URL"), 
        api_key=os.getenv("QDRANT_API_KEY"),
        timeout=120
    )
    
    if client.collection_exists(COLLECTION_NAME):
        print("🗑️ Usuwanie starej kolekcji...")
        client.delete_collection(COLLECTION_NAME)
    
    print("📦 Tworzenie nowej kolekcji...")
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE)
    )
    
    # Indeksy payload
    for field in ["court_type", "judgment_type", "judgment_date"]:
        client.create_payload_index(
            collection_name=COLLECTION_NAME,
            field_name=field,
            field_schema=PayloadSchemaType.KEYWORD
        )
    
    print("📝 Przetwarzanie dokumentów...")
    all_chunks = []
    all_payloads = []
    
    for doc in tqdm(documents, desc="Chunking"):
        text = clean_legal_text(doc.get("text", ""))
        if len(text) < MIN_CHUNK_SIZE:
            continue
        
        chunks = smart_legal_chunker(text)
        
        for chunk in chunks:
            enriched = create_enriched_text(chunk, doc)
            all_chunks.append(enriched)
            
            all_payloads.append({
                "page_content": chunk,
                "origin_id": doc["id"],
                "signature": doc["signature"],
                "judgment_date": doc.get("judgment_date", ""),
                "court_type": doc.get("court_type", ""),
                "court_name": doc.get("court_name", ""),
                "judgment_type": doc.get("judgment_type", ""),
                "keywords": doc.get("keywords", []),
                "judges": [j.get("name", "") for j in doc.get("judges", [])],
                "full_document": text
            })
    
    print(f"📊 Utworzono {len(all_chunks)} chunków")
    
    print("🚀 Generowanie embeddingów i upload do Qdrant Cloud...")
    point_id = 0
    failed_batches = []
    
    for i in tqdm(range(0, len(all_chunks), BATCH_SIZE), desc="Batches"):
        batch_chunks = all_chunks[i:i+BATCH_SIZE]
        batch_payloads = all_payloads[i:i+BATCH_SIZE]
        
        # Generuj embeddingi na GPU
        vectors = model.encode(
            batch_chunks,
            normalize_embeddings=True,  # Ważne dla E5!
            show_progress_bar=False
        )
        
        points = [
            PointStruct(
                id=point_id + j,
                vector=vectors[j].tolist(),
                payload=batch_payloads[j]
            )
            for j in range(len(vectors))
        ]
        
        # Upload z retry
        for attempt in range(3):
            try:
                client.upsert(collection_name=COLLECTION_NAME, points=points)
                break
            except Exception as e:
                if attempt == 2:
                    print(f"\n⚠️ Batch {i//BATCH_SIZE} failed: {e}")
                    failed_batches.append(i)
                else:
                    import time
                    time.sleep(5)
        
        point_id += len(points)
    
    if failed_batches:
        print(f"\n⚠️ {len(failed_batches)} batches failed")
    
    print(f"\n✅ ZAKOŃCZONO! Zaindeksowano {point_id} chunków w '{COLLECTION_NAME}'")

if __name__ == "__main__":
    main()
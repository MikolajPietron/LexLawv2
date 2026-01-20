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
COLLECTION_NAME = "polish_law_e5"
MODEL_NAME = "intfloat/multilingual-e5-large"
VECTOR_SIZE = 1024

CHUNK_SIZE = 512
CHUNK_OVERLAP = 128
MIN_CHUNK_SIZE = 50
BATCH_SIZE = 32

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print(f"🖥️ Używam: {DEVICE.upper()}")


def clean_legal_text(text):
    """Czyści tekst prawniczy."""
    if not text:
        return ""
    text = re.sub(r'\s+', ' ', text)
    text = text.replace('(...)', '').replace('( ... )', '').replace('[]', '')
    text = re.sub(r'\s([rRzZtT])\s\.', r' \1.', text)
    text = re.sub(r'(art|sygn)\s\.', r'\1.', text)
    text = re.sub(r'[^\w\s\.\,\;\:\-\(\)\[\]§„"\"\'\/\%\@\+\=\!\?\*\#]+', '', text)
    return text.strip()


def find_safe_boundaries(text):
    """
    Znajduje bezpieczne miejsca do cięcia tekstu.
    Zwraca listę pozycji gdzie można ciąć (końce zdań).
    """
    boundaries = [0]
    
    # Szukamy końców zdań: . ! ? + spacja + duża litera
    for match in re.finditer(r'[.!?]\s+(?=[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźżA-ZĄĆĘŁŃÓŚŹŻ])', text):
        pos = match.end()
        before = text[max(0, match.start()-10):match.start()+1]
        
        # Pomiń jeśli to inicjał (pojedyncza litera przed kropką)
        if re.search(r'\s[A-ZĄĆĘŁŃÓŚŹŻ]\.$', before):
            continue
        
        # Pomiń jeśli to skrót prawniczy
        if re.search(r'(art|sygn|poz|ust|pkt|nr|r|z|k|s|t|j|lit|zd|par|ust)\.$', before, re.IGNORECASE):
            continue
        
        boundaries.append(pos)
    
    boundaries.append(len(text))
    return sorted(set(boundaries))


def smart_legal_chunker(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """
    Inteligentny chunker - dzieli na granicach zdań, scala małe fragmenty.
    """
    text = text.strip()
    if not text:
        return []
    
    if len(text) <= chunk_size:
        return [{"text": text, "start_char": 0, "end_char": len(text)}]
    
    boundaries = find_safe_boundaries(text)
    
    if len(boundaries) < 2:
        boundaries = list(range(0, len(text), chunk_size)) + [len(text)]
        boundaries = sorted(list(set(boundaries)))
    
    chunks = []
    start_idx = 0
    max_iterations = len(boundaries) * 3
    iterations = 0
    
    while start_idx < len(boundaries) - 1 and iterations < max_iterations:
        iterations += 1
        
        chunk_start = boundaries[start_idx]
        
        # Szukamy końca chunka (max chunk_size znaków)
        end_idx = start_idx + 1
        for j in range(start_idx + 1, len(boundaries)):
            if boundaries[j] - chunk_start <= chunk_size:
                end_idx = j
            else:
                break
        
        chunk_end = boundaries[end_idx]
        chunk_text = text[chunk_start:chunk_end].strip()
        
        # Merge małych fragmentów do poprzedniego chunka
        if len(chunk_text) < MIN_CHUNK_SIZE:
            if chunks:
                last_chunk = chunks[-1]
                new_end = chunk_end
                merged_text = text[last_chunk["start_char"]:new_end].strip()
                chunks[-1]["text"] = merged_text
                chunks[-1]["end_char"] = new_end
            else:
                chunks.append({
                    "text": chunk_text,
                    "start_char": chunk_start,
                    "end_char": chunk_end
                })
        else:
            chunks.append({
                "text": chunk_text,
                "start_char": chunk_start,
                "end_char": chunk_end
            })
        
        # Overlap - cofamy się do granicy zdania
        if end_idx >= len(boundaries) - 1:
            break
        
        target_pos = chunk_end - overlap
        next_start_idx = end_idx
        
        for j in range(end_idx, start_idx, -1):
            if boundaries[j] <= target_pos:
                next_start_idx = j
                break
        
        if next_start_idx <= start_idx:
            next_start_idx = start_idx + 1
        
        start_idx = next_start_idx
    
    return chunks


def create_enriched_text(chunk_text, doc):
    """Wzbogaca chunk o metadane dla E5."""
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
    
    if context_parts:
        return f"passage: [{' | '.join(context_parts)}] {chunk_text}"
    return f"passage: {chunk_text}"


def main():
    print("📂 Ładowanie danych...")
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        documents = json.load(f)
    print(f"✅ Załadowano {len(documents)} dokumentów")
    
    print(f"🔧 Ładowanie modelu: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME, device=DEVICE)
    model.max_seq_length = 512
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
    
    # Indeksy
    client.create_payload_index(COLLECTION_NAME, "origin_id", PayloadSchemaType.INTEGER)
    client.create_payload_index(COLLECTION_NAME, "signature", PayloadSchemaType.KEYWORD)
    client.create_payload_index(COLLECTION_NAME, "court_type", PayloadSchemaType.KEYWORD)
    client.create_payload_index(COLLECTION_NAME, "judgment_type", PayloadSchemaType.KEYWORD)
    client.create_payload_index(COLLECTION_NAME, "judgment_date", PayloadSchemaType.KEYWORD)
    
    print("📝 Przetwarzanie dokumentów...")
    all_chunks = []
    all_payloads = []
    
    for doc in tqdm(documents, desc="Chunking"):
        text = clean_legal_text(doc.get("text", ""))
        if len(text) < MIN_CHUNK_SIZE:
            continue
        
        chunks = smart_legal_chunker(text)
        
        for chunk_info in chunks:
            chunk_text = chunk_info["text"]
            enriched = create_enriched_text(chunk_text, doc)
            all_chunks.append(enriched)
            
            all_payloads.append({
                "page_content": chunk_text,
                "origin_id": doc["id"],
                "signature": doc["signature"],
                "judgment_date": doc.get("judgment_date", ""),
                "court_type": doc.get("court_type", ""),
                "court_name": doc.get("court_name", ""),
                "judgment_type": doc.get("judgment_type", ""),
                "keywords": doc.get("keywords", []),
                "judges": [j.get("name", "") for j in doc.get("judges", [])],
                "start_char": chunk_info["start_char"],
                "end_char": chunk_info["end_char"],
            })
    
    print(f"📊 Utworzono {len(all_chunks)} chunków")
    
    print("🚀 Generowanie embeddingów i upload...")
    point_id = 0
    
    for i in tqdm(range(0, len(all_chunks), BATCH_SIZE), desc="Batches"):
        batch_chunks = all_chunks[i:i+BATCH_SIZE]
        batch_payloads = all_payloads[i:i+BATCH_SIZE]
        
        vectors = model.encode(
            batch_chunks,
            normalize_embeddings=True,
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
        
        for attempt in range(3):
            try:
                client.upsert(collection_name=COLLECTION_NAME, points=points)
                break
            except Exception as e:
                if attempt == 2:
                    print(f"\n⚠️ Batch failed: {e}")
                else:
                    import time
                    time.sleep(5)
        
        point_id += len(points)
    
    print(f"\n✅ ZAKOŃCZONO! Zaindeksowano {point_id} chunków w '{COLLECTION_NAME}'")


if __name__ == "__main__":
    main()
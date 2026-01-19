import json
import os
import hashlib
import re
import torch
from tqdm import tqdm
from qdrant_client import QdrantClient
from qdrant_client.http import models
from sentence_transformers import SentenceTransformer

# --- KONFIGURACJA ---
DATA_FILE = "data/clean_dataset.json"
DB_PATH = "qdrant_db"
COLLECTION_NAME = "polish_law_hybrid"
MODEL_NAME = "sdadas/st-polish-paraphrase-from-distilroberta"

CHUNK_SIZE = 512      
CHUNK_OVERLAP = 128   
MIN_CHUNK_SIZE = 50   


def clean_legal_text(text):
    """Czyszczenie tekstu prawniczego."""
    if not text: return ""
    text = re.sub(r'\s+', ' ', text)
    text = text.replace('(...)', '').replace('( ... )', '').replace('[]', '')
    text = re.sub(r'\s([rRzZtT])\s\.', r' \1.', text)
    text = re.sub(r'(art|sygn)\s\.', r'\1.', text)
    return text.strip()


def find_safe_boundaries(text):
    """
    Znajduje bezpieczne miejsca do cięcia tekstu.
    Zwraca listę pozycji gdzie można ciąć.
    """
    boundaries = [0]
    
    # Szukamy końców zdań: . ! ? + spacja + duża litera (min 2 znaki słowa)
    for match in re.finditer(r'[.!?]\s+(?=[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźżA-ZĄĆĘŁŃÓŚŹŻ])', text):
        pos = match.end()
        before = text[max(0, match.start()-10):match.start()+1]
        
        # Pomiń jeśli to inicjał (pojedyncza litera przed kropką)
        if re.search(r'\s[A-ZĄĆĘŁŃÓŚŹŻ]\.$', before):
            continue
        
        # Pomiń jeśli to skrót
        if re.search(r'(art|sygn|poz|ust|pkt|nr|r|z|k|s)\.$', before, re.IGNORECASE):
            continue
        
        boundaries.append(pos)
    
    boundaries.append(len(text))
    return sorted(set(boundaries))


def smart_legal_chunker(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """
    Poprawiony chunker: zamiast usuwać małe fragmenty, dokleja je do poprzednich.
    """
    text = text.strip()
    if not text:
        return []
        
    # Szybka ścieżka dla krótkich tekstów
    if len(text) <= chunk_size:
        return [{"text": text, "start_char": 0, "end_char": len(text)}]
    
    boundaries = find_safe_boundaries(text)
    
    # Zabezpieczenie na wypadek braku granic
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
        
        # 1. Szukamy końca chunka
        end_idx = start_idx + 1
        for j in range(start_idx + 1, len(boundaries)):
            if boundaries[j] - chunk_start <= chunk_size:
                end_idx = j
            else:
                break
        
        chunk_end = boundaries[end_idx]
        chunk_text = text[chunk_start:chunk_end].strip()
        
        # 2. LOGIKA NAPRAWCZA (MERGE)
        # Jeśli chunk jest za mały...
        if len(chunk_text) < MIN_CHUNK_SIZE:
            # A) Jeśli mamy już jakieś chunki, doklej ten mały fragment do ostatniego
            if chunks:
                last_chunk = chunks[-1]
                # Aktualizujemy tekst i pozycję końcową ostatniego chunka
                new_end = chunk_end
                # Pobieramy tekst od początku poprzedniego chunka do końca obecnego małego
                merged_text = text[last_chunk["start_char"]:new_end].strip()
                
                chunks[-1]["text"] = merged_text
                chunks[-1]["end_char"] = new_end
            # B) Jeśli to pierwszy chunk i jest mały, trudno - musimy go dodać, żeby nie zgubić
            else:
                 chunks.append({
                    "text": chunk_text,
                    "start_char": chunk_start,
                    "end_char": chunk_end
                })
        else:
            # Jeśli rozmiar jest OK, dodajemy normalnie
            chunks.append({
                "text": chunk_text,
                "start_char": chunk_start,
                "end_char": chunk_end
            })
        
        # 3. Obliczanie następnego startu (Overlap)
        next_start_idx = end_idx
        
        # Jeśli jesteśmy na końcu, przerywamy
        if end_idx >= len(boundaries) - 1:
            break

        # Cofamy się o overlap
        target_pos = chunk_end - overlap
        for j in range(end_idx, start_idx, -1):
            if boundaries[j] <= target_pos:
                next_start_idx = j
                break
        
        # Zabezpieczenie przed pętlą w miejscu (zawsze idź min. 1 krok do przodu)
        if next_start_idx <= start_idx:
            next_start_idx = start_idx + 1
            
        start_idx = next_start_idx
    
    return chunks


def main():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"🚀 Tryb pracy: {device.upper()}")

    if not os.path.exists(DATA_FILE):
        print(f"❌ Brak pliku '{DATA_FILE}'!")
        return

    print("📂 Wczytywanie danych...")
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    print(f"🧠 Ładowanie modelu '{MODEL_NAME}'...")
    encoder = SentenceTransformer(MODEL_NAME, device=device)

    all_chunks = []
    metadatas = []
    ids = []
    
    print("✂️  Inteligentne dzielenie tekstu...")
    
    for item in tqdm(raw_data, desc="Przetwarzanie dokumentów"):
        clean_content = clean_legal_text(item["text"])
        
        if len(clean_content) < MIN_CHUNK_SIZE:
            continue

        chunks = smart_legal_chunker(clean_content)
        
        if not chunks:
            continue
        
        total_chunks = len(chunks)
        
        for chunk_id, chunk_info in enumerate(chunks):
            all_chunks.append(chunk_info["text"])
            metadatas.append({
                "page_content": chunk_info["text"],
                "full_document": clean_content,
                "signature": item["signature"],
                "date": item["date"],
                "origin_id": item["id"],
                "chunk_id": chunk_id,
                "total_chunks": total_chunks,
                "start_char": chunk_info["start_char"],
                "end_char": chunk_info["end_char"],
            })
            ids.append(f"{item['id']}_chunk_{chunk_id}")

    print(f"📊 Utworzono {len(all_chunks)} fragmentów z {len(raw_data)} dokumentów.")

    client = QdrantClient(path=DB_PATH)
    
    if client.collection_exists(COLLECTION_NAME):
        client.delete_collection(collection_name=COLLECTION_NAME)
    
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=models.VectorParams(size=768, distance=models.Distance.COSINE)
    )
    
    client.create_payload_index(COLLECTION_NAME, "origin_id", models.PayloadSchemaType.INTEGER)
    client.create_payload_index(COLLECTION_NAME, "signature", models.PayloadSchemaType.KEYWORD)

    BATCH_SIZE = 256
    print("🔥 Zapisywanie do bazy Qdrant...")
    
    for i in tqdm(range(0, len(all_chunks), BATCH_SIZE), desc="Indeksowanie"):
        batch_texts = all_chunks[i:i + BATCH_SIZE]
        batch_metas = metadatas[i:i + BATCH_SIZE]
        batch_ids = ids[i:i + BATCH_SIZE]
        
        if not batch_texts:
            continue
            
        embeddings = encoder.encode(batch_texts, show_progress_bar=False)
        
        points = [
            models.PointStruct(
                id=hashlib.md5(uid.encode()).hexdigest(),
                vector=vec.tolist(),
                payload=meta
            )
            for uid, vec, meta in zip(batch_ids, embeddings, batch_metas)
        ]
        
        client.upsert(collection_name=COLLECTION_NAME, points=points)

    print(f"\n✅ SUKCES! Baza '{COLLECTION_NAME}' gotowa.")


if __name__ == "__main__":
    main()
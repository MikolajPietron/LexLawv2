import json
import os
import hashlib
import re
import torch
from tqdm import tqdm
from langchain_experimental.text_splitter import SemanticChunker
from langchain_huggingface import HuggingFaceEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.http import models

# --- KONFIGURACJA ---
DATA_FILE = "data/clean_dataset.json"
DB_PATH = "qdrant_db"
COLLECTION_NAME = "polish_law_semantic" # Nowa nazwa kolekcji, żeby odróżnić od starej
MODEL_NAME = "sdadas/st-polish-paraphrase-from-distilroberta"

def clean_legal_text(text):
    """
    Nawet przy AI musimy posprzątać podstawowe śmieci.
    """
    if not text: return ""
    text = re.sub(r'\s+', ' ', text)
    text = text.replace('(...)', '').replace('[]', '')
    # Naprawa dat i skrótów nadal się przydaje, żeby model lepiej rozumiał zdania
    text = re.sub(r'\s([rRzZtT])\s\.', r' \1.', text)
    text = re.sub(r'(art)\s\.', r'art.', text)
    return text.strip()

def main():
    # Sprawdzenie GPU
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"🚀 Tryb pracy: {device.upper()} (RTX 4060 ready!)")

    if not os.path.exists(DATA_FILE):
        print(f"❌ Brak pliku '{DATA_FILE}'!")
        return

    print("📂 Wczytywanie danych...")
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    # 1. ŁADOWANIE MODELU DO VRAM
    print(f"🧠 Ładowanie modelu AI '{MODEL_NAME}' na GPU...")
    # Ten model posłuży nam ZARÓWNO do cięcia tekstu, jak i do bazy Qdrant
    embeddings = HuggingFaceEmbeddings(
        model_name=MODEL_NAME,
        model_kwargs={'device': device} # Tu wymuszamy pracę na karcie
    )

    # 2. KONFIGURACJA SEMANTYCZNEGO SPLITTERA
    print("⚙️  Konfiguracja Semantic Chunkera...")
    # To jest serce "Agentic/AI Chunking".
    # breakpoint_threshold_type="percentile" oznacza:
    # "Tnij tylko wtedy, gdy zmiana tematu jest silniejsza niż w 90% przypadków"
    text_splitter = SemanticChunker(
        embeddings,
        breakpoint_threshold_type="percentile",
        breakpoint_threshold_amount=90 # Możesz eksperymentować (80 = więcej kawałków, 95 = większe kawałki)
    )

    all_chunks = []
    metadatas = []
    ids = []
    
    print("✂️  Analiza semantyczna i dzielenie tekstu (to chwilę potrwa)...")
    
    # Tutaj niestety nie da się zrobić batchowania tak łatwo jak w Qdrancie,
    # bo SemanticChunker analizuje spójność pojedynczego dokumentu.
    # Ale dzięki RTX 4060 embeddingi liczą się błyskawicznie.
    
    for item in tqdm(raw_data, desc="AI analizuje dokumenty"):
        clean_content = clean_legal_text(item["text"])
        if len(clean_content) < 50: continue

        try:
            # MAGIA: Model decyduje, gdzie ciąć
            chunks = text_splitter.split_text(clean_content)
        except Exception as e:
            # Czasem pusty tekst może wywalić błąd
            continue
        
        for i, chunk_text in enumerate(chunks):
            if len(chunk_text) < 20: continue
            
            all_chunks.append(chunk_text)
            metadatas.append({
                "page_content": chunk_text,
                "signature": item["signature"],
                "date": item["date"],
                "origin_id": item["id"],
                "chunk_id": i,
                "type": "semantic" # Znacznik, że to wersja inteligentna
            })
            ids.append(f"{item['id']}_sem_{i}")

    print(f"📊 Utworzono {len(all_chunks)} inteligentnych fragmentów.")

    # 3. ZAPIS DO QDRANT
    client = QdrantClient(path=DB_PATH)
    
    if client.collection_exists(COLLECTION_NAME):
        client.delete_collection(collection_name=COLLECTION_NAME)
    
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=models.VectorParams(
            size=768,
            distance=models.Distance.COSINE
        )
    )

    # Ponowne użycie modelu (już załadowanego w pamięci) do wygenerowania wektorów dla bazy
    # Używamy klienta sentence-transformers bezpośrednio dla prędkości batchowania
    from sentence_transformers import SentenceTransformer
    encoder = SentenceTransformer(MODEL_NAME, device=device)

    BATCH_SIZE = 256 # RTX 4060 lubi duże paczki
    print("🔥 Zapisywanie do bazy Qdrant (GPU)...")
    
    for i in tqdm(range(0, len(all_chunks), BATCH_SIZE), desc="Indeksowanie", unit="batch"):
        batch_texts = all_chunks[i : i + BATCH_SIZE]
        batch_metas = metadatas[i : i + BATCH_SIZE]
        batch_ids_raw = ids[i : i + BATCH_SIZE]
        
        if not batch_texts: continue
            
        embeddings_batch = encoder.encode(batch_texts, show_progress_bar=False)
        
        points = []
        for uid, vec, meta in zip(batch_ids_raw, embeddings_batch, batch_metas):
            id_hash = hashlib.md5(uid.encode()).hexdigest()
            points.append(models.PointStruct(
                id=id_hash,
                vector=vec.tolist(),
                payload=meta
            ))
        client.upsert(collection_name=COLLECTION_NAME, points=points)

    print(f"\n✅ SUKCES! Baza semantyczna '{COLLECTION_NAME}' gotowa.")

if __name__ == "__main__":
    main()
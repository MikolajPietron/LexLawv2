import json
import os
import hashlib
import re
from tqdm import tqdm
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
from qdrant_client.http import models
from sentence_transformers import SentenceTransformer
import torch

# --- KONFIGURACJA ---
DATA_FILE = "data/clean_dataset.json"
DB_PATH = "qdrant_db"
COLLECTION_NAME = "polish_law"
MODEL_NAME = "sdadas/st-polish-paraphrase-from-distilroberta"

def clean_legal_text(text):
    """
    Funkcja czyszcząca tekst przed wrzuceniem do modelu.
    """
    if not text:
        return ""
    
    # 1. Spłaszczanie białych znaków
    text = re.sub(r'\s+', ' ', text)
    
    # 2. Usuwanie śmieci
    text = text.replace('(...)', '').replace('( ... )', '').replace('[]', '')
    
    # 3. Inteligentne sklejanie skrótów (np. "2003 r ." -> "2003 r.")
    text = re.sub(r'\s([rRzZtT])\s\.', r' \1.', text)
    text = re.sub(r'(art)\s\.', r'art.', text)
    text = re.sub(r'(sygn)\s\.', r'sygn.', text)
    
    return text.strip()

def main():
    # Sprawdzenie GPU dla pewności
    if torch.cuda.is_available():
        print(f"🚀 WYKRYTO GPU: {torch.cuda.get_device_name(0)}")
    else:
        print("⚠️ UWAGA: Nie wykryto GPU! Skrypt pójdzie na CPU (będzie wolniej).")

    if not os.path.exists(DATA_FILE):
        print(f"❌ Brak pliku '{DATA_FILE}'!")
        return

    print("📂 Wczytywanie danych...")
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    # 1. ŁADOWANIE MODELU NA KARTĘ GRAFICZNĄ
    print(f"🧠 Ładowanie modelu '{MODEL_NAME}' do VRAM...")
    try:
        # device="cuda" to klucz do prędkości
        encoder = SentenceTransformer(MODEL_NAME, device="cuda")
    except Exception as e:
        print(f"❌ Błąd ładowania na GPU: {e}. Przełączam na CPU.")
        encoder = SentenceTransformer(MODEL_NAME, device="cpu")
    
    # 2. PRZYGOTOWANIE CHUNKÓW
    print("✂️  Dzielenie tekstu (CPU)...")
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1200,
        chunk_overlap=250,
        separators=["\n\n", ". ", " ", ""]
    )
    
    all_chunks = []
    metadatas = []
    ids = []
    
    # Pętla przygotowawcza (to nadal robi procesor, bo to operacje na stringach)
    for item in tqdm(raw_data, desc="Parsowanie tekstu"):
        clean_content = clean_legal_text(item["text"])
        if len(clean_content) < 50:
            continue

        chunks = text_splitter.split_text(clean_content)
        
        for i, chunk_text in enumerate(chunks):
            # Drobna kosmetyka kropkowa
            chunk_text = chunk_text.strip()
            if chunk_text.startswith("."):
                chunk_text = chunk_text[1:].strip()
            
            if len(chunk_text) > 30:
                all_chunks.append(chunk_text)
                metadatas.append({
                    "page_content": chunk_text,
                    "signature": item["signature"],
                    "date": item["date"],
                    "origin_id": item["id"],
                    "chunk_id": i
                })
                ids.append(f"{item['id']}_{i}")

    print(f"📊 Do przemielenia: {len(all_chunks)} fragmentów.")

    # 3. SETUP QDRANT
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

    # 4. WEKTORYZACJA NA GPU (TU BĘDZIE OGIEŃ)
    # Zwiększamy BATCH_SIZE bo RTX 4060 ma 8GB pamięci i lubi duże paczki
    BATCH_SIZE = 256 
    
    print("🔥 Uruchamianie silników GPU...")
    
    for i in tqdm(range(0, len(all_chunks), BATCH_SIZE), desc="Obliczenia GPU", unit="batch"):
        batch_texts = all_chunks[i : i + BATCH_SIZE]
        batch_metas = metadatas[i : i + BATCH_SIZE]
        batch_ids_raw = ids[i : i + BATCH_SIZE]
        
        if not batch_texts: continue
            
        # To jest moment, gdzie karta graficzna robi robotę
        embeddings = encoder.encode(batch_texts, show_progress_bar=False)
        
        points = []
        for uid, vec, meta in zip(batch_ids_raw, embeddings, batch_metas):
            id_hash = hashlib.md5(uid.encode()).hexdigest()
            points.append(models.PointStruct(
                id=id_hash,
                vector=vec.tolist(),
                payload=meta
            ))
            
        client.upsert(collection_name=COLLECTION_NAME, points=points)

    print(f"\n✅ SUKCES! Baza gotowa w folderze '{DB_PATH}'.")

if __name__ == "__main__":
    main()
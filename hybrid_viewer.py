import streamlit as st
import json
import os
from qdrant_client import QdrantClient
from qdrant_client.http import models
from dotenv import load_dotenv

load_dotenv()

# --- KONFIGURACJA ---
COLLECTION_NAME = "polish_law_e5"
DATA_FILE = "data/full_dataset.json"

st.set_page_config(page_title="Przeglądarka Chunków", layout="wide")
st.title("🔍 Inspektor Chunków - E5 Model")

# 1. Ładowanie listy wyroków z pliku JSON
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        raw_data = json.load(f)
    options = {f"{item['signature']} ({item.get('judgment_date', 'brak daty')})": item['id'] for item in raw_data}
else:
    st.error(f"❌ Brak pliku {DATA_FILE}!")
    st.stop()

# 2. Połączenie z Qdrant Cloud
try:
    client = QdrantClient(
        url=os.getenv("QDRANT_URL"),
        api_key=os.getenv("QDRANT_API_KEY")
    )
    if client.collection_exists(COLLECTION_NAME):
        collection_info = client.get_collection(COLLECTION_NAME)
        st.success(f"✅ Połączono z Qdrant Cloud | Punktów: {collection_info.points_count}")
    else:
        st.warning(f"⚠️ Kolekcja '{COLLECTION_NAME}' nie istnieje.")
        st.stop()
except Exception as e:
    st.error(f"❌ Błąd połączenia: {e}")
    st.stop()

# === WYBÓR WYROKU ===
selected_label = st.selectbox("Wybierz orzeczenie:", list(options.keys()))
selected_id = options[selected_label]

if st.button("📂 Pokaż wszystkie chunki"):
    st.divider()
    
    scroll_filter = models.Filter(
        must=[
            models.FieldCondition(
                key="origin_id",
                match=models.MatchValue(value=selected_id)
            )
        ]
    )
    
    all_points = []
    next_offset = None
    
    with st.spinner("Pobieranie chunków z Qdrant Cloud..."):
        while True:
            batch, next_offset = client.scroll(
                collection_name=COLLECTION_NAME,
                scroll_filter=scroll_filter,
                limit=100,
                offset=next_offset,
                with_payload=True
            )
            all_points.extend(batch)
            if next_offset is None:
                break
    
    points = all_points

    if not points:
        st.warning("Brak chunków dla tego dokumentu.")
    else:
        st.info(f"📊 Znaleziono **{len(points)}** chunków")
        
        # === STATYSTYKI ===
        col1, col2, col3 = st.columns(3)
        chunk_lengths = [len(p.payload.get('page_content', '')) for p in points]
        
        with col1:
            st.metric("Średnia długość", f"{sum(chunk_lengths)//len(chunk_lengths)} znaków")
        with col2:
            st.metric("Najkrótszy", f"{min(chunk_lengths)} znaków")
        with col3:
            st.metric("Najdłuższy", f"{max(chunk_lengths)} znaków")
        
        st.divider()
        
        # === CHUNKI ===
        for i, point in enumerate(points):
            content = point.payload.get('page_content', '')
            
            # Analiza początku chunka
            first_50 = content[:50]
            starts_mid_sentence = not content[0].isupper() if content else False
            
            status = "⚠️ UCIĘTY" if starts_mid_sentence else "✅ OK"
            
            with st.expander(f"Chunk #{i+1} | {len(content)} znaków | {status}"):
                # Pokaż początek
                st.markdown("**Początek:**")
                if starts_mid_sentence:
                    st.error(f"```{first_50}...```")
                else:
                    st.success(f"```{first_50}...```")
                
                # Pokaż koniec
                st.markdown("**Koniec:**")
                st.code(f"...{content[-50:]}")
                
                # Pełny tekst
                st.markdown("**Pełny chunk:**")
                st.text_area("", content, height=150, key=f"chunk_{i}", disabled=True)

# === PORÓWNANIE Z ORYGINAŁEM ===
st.divider()
if st.checkbox("📋 Pokaż oryginalny tekst z JSON"):
    original = next((item for item in raw_data if item['id'] == selected_id), None)
    if original:
        st.text_area("Oryginalny tekst:", original.get('text', ''), height=300)
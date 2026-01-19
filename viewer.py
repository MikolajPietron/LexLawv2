import streamlit as st
import json
import os
from qdrant_client import QdrantClient
from qdrant_client.http import models

# --- KONFIGURACJA ---
DB_PATH = "qdrant_db"
COLLECTION_NAME = "polish_law_semantic"
DATA_FILE = "data/clean_dataset.json"

st.set_page_config(page_title="Przeglądarka Wyroków", layout="wide")
st.title("📂 Inspektor Bazy Qdrant")

# 1. ŁADOWANIE LISTY DOSTĘPNYCH WYROKÓW
# Najszybciej pobrać listę sygnatur z pliku JSON, żeby zrobić ładną listę rozwijaną
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        raw_data = json.load(f)
    # Tworzymy słownik: "Sygnatura (Data)" -> ID
    options = {f"{item['signature']} (z dnia {item['date']})": item['id'] for item in raw_data}
else:
    st.error("Brak pliku clean_dataset.json! Nie mogę stworzyć listy wyroków.")
    st.stop()

# 2. WYBÓR WYROKU
selected_label = st.selectbox("Wybierz orzeczenie do podglądu:", list(options.keys()))
selected_id = options[selected_label]

if st.button("Pobierz wszystkie fragmenty z bazy"):
    st.divider()
    
    # 3. POŁĄCZENIE Z BAZĄ
    client = QdrantClient(path=DB_PATH)
    
    # 4. FILTROWANIE (To jest ta "magia")
    # Mówimy bazie: "Daj mi wszystkie punkty, gdzie pole 'origin_id' == wybrane ID"
    scroll_filter = models.Filter(
        must=[
            models.FieldCondition(
                key="origin_id",
                match=models.MatchValue(value=selected_id)
            )
        ]
    )
    
    # Używamy metody .scroll() - ona służy do wyciągania danych, a nie szukania podobieństw
    points, _ = client.scroll(
        collection_name=COLLECTION_NAME,
        scroll_filter=scroll_filter,
        limit=100,  # Zakładamy, że wyrok nie ma więcej niż 100 fragmentów
        with_payload=True
    )
    
    if not points:
        st.warning("Nie znaleziono fragmentów w bazie Qdrant dla tego ID. Czy uruchomiłeś ingest.py?")
    else:
        # 5. SORTOWANIE
        # Qdrant może zwrócić fragmenty w losowej kolejności. Musimy je poukładać wg 'chunk_id'.
        points.sort(key=lambda x: x.payload['chunk_id'])
        
        st.success(f"Znaleziono {len(points)} fragmentów (chunks) dla tego wyroku.")
        
        # Wyświetlanie
        full_text = ""
        for point in points:
            chunk_content = point.payload['page_content']
            chunk_id = point.payload['chunk_id']
            
            with st.expander(f"Fragment #{chunk_id}"):
                st.text(f"ID Wektora: {point.id}")
                st.write(chunk_content)
            
            # Sklejamy tekst do podglądu całości
            full_text += chunk_content + " "

        st.subheader("📝 Podgląd Scalony (Całość)")
        st.text_area("Pełna treść z bazy:", full_text, height=300)
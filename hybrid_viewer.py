import streamlit as st
import json
import os
from qdrant_client import QdrantClient
from qdrant_client.http import models

# --- KONFIGURACJA ---
DB_PATH = "qdrant_db"
COLLECTION_NAME = "polish_law_hybrid"
DATA_FILE = "data/clean_dataset.json"

st.set_page_config(page_title="Przeglądarka Chunków", layout="wide")
st.title("🔍 Inspektor Chunków - Hybrid (Pełny Widok)")

# 1. Ładowanie listy wyroków z pliku JSON
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        raw_data = json.load(f)
    # Tworzymy mapę: "Sygnatura (data)" -> ID
    options = {f"{item['signature']} (z dnia {item['date']})": item['id'] for item in raw_data}
else:
    st.error(f"❌ Brak pliku {DATA_FILE}!")
    st.stop()

# 2. Połączenie z bazą Qdrant
try:
    client = QdrantClient(path=DB_PATH)
    if client.collection_exists(COLLECTION_NAME):
        collection_info = client.get_collection(COLLECTION_NAME)
        st.success(f"✅ Połączono z bazą | Punktów w kolekcji: {collection_info.points_count}")
    else:
        st.warning(f"⚠️ Kolekcja '{COLLECTION_NAME}' nie istnieje. Uruchom najpierw skrypt ingest.")
        st.stop()
except Exception as e:
    st.error(f"❌ Błąd połączenia z bazą: {e}")
    st.stop()

# === WYBÓR WYROKU ===
selected_label = st.selectbox("Wybierz orzeczenie:", list(options.keys()))
selected_id = options[selected_label]

if st.button("📂 Pokaż wszystkie chunki"):
    st.divider()
    
    # Filtr: szukamy tylko chunków należących do wybranego dokumentu
    scroll_filter = models.Filter(
        must=[
            models.FieldCondition(
                key="origin_id",
                match=models.MatchValue(value=selected_id)
            )
        ]
    )
    
    # --- NOWA LOGIKA POBIERANIA (PĘTLA) ---
    all_points = []
    next_offset = None
    
    with st.spinner("Pobieranie danych z bazy wektorowej..."):
        while True:
            # Pobieramy paczkę (np. 200 sztuk)
            batch, next_offset = client.scroll(
                collection_name=COLLECTION_NAME,
                scroll_filter=scroll_filter,
                limit=200,          # Pobieraj po 200 na raz
                offset=next_offset, # Czytaj od miejsca gdzie skończyłeś
                with_payload=True
            )
            all_points.extend(batch)
            
            # Jeśli next_offset jest None, to koniec danych
            if next_offset is None:
                break
    
    points = all_points

    # --- WIZUALIZACJA ---
    if not points:
        st.warning("Brak chunków dla tego dokumentu. Uruchom najpierw skrypt ingest!")
    else:
        # Sortowanie po chunk_id (kluczowe dla poprawnego wyświetlania tekstu ciągłego)
        points.sort(key=lambda x: x.payload.get('chunk_id', 0))
        
        total_chunks_db = len(points)
        total_chunks_meta = points[0].payload.get('total_chunks', '?')
        
        st.info(f"📊 Znaleziono **{total_chunks_db}** chunków (Metadane mówią o: {total_chunks_meta})")
        
        if total_chunks_db != total_chunks_meta and total_chunks_meta != '?':
            st.warning("⚠️ Uwaga: Liczba znalezionych chunków różni się od liczby zapisanej w metadanych!")

        # === STATYSTYKI ===
        col1, col2, col3 = st.columns(3)
        chunk_lengths = [len(p.payload['page_content']) for p in points]
        
        with col1:
            avg_len = sum(chunk_lengths)//len(chunk_lengths) if chunk_lengths else 0
            st.metric("Średnia długość chunka", f"{avg_len} znaków")
        with col2:
            st.metric("Najkrótszy chunk", f"{min(chunk_lengths) if chunk_lengths else 0} znaków")
        with col3:
            st.metric("Najdłuższy chunk", f"{max(chunk_lengths) if chunk_lengths else 0} znaków")
        
        st.divider()
        
        # === TRYBY WIDOKU ===
        view_mode = st.radio("Tryb wyświetlania:", ["Pojedyncze chunki", "Pełny tekst z podziałem"], horizontal=True)
        
        if view_mode == "Pojedyncze chunki":
            for point in points:
                chunk_id = point.payload.get('chunk_id', '?')
                content = point.payload['page_content']
                start = point.payload.get('start_char', 'N/A')
                end = point.payload.get('end_char', 'N/A')
                
                with st.expander(f"🧩 Chunk #{chunk_id} | Znaki: {start}-{end} | Długość: {len(content)}"):
                    st.code(content, language=None)
                    st.caption(f"ID wektora: `{point.id}`")
        
        else:  # Pełny tekst z podziałem (HTML)
            st.subheader("📜 Pełny dokument z wizualizacją podziału")
            
            full_doc = points[0].payload.get('full_document', '')
            
            if full_doc:
                colors = ['#e3f2fd', '#fff3e0', '#e8f5e9', '#fce4ec', '#f3e5f5', '#e0f7fa']
                html_parts = []
                last_end = 0
                
                for i, point in enumerate(points):
                    start = point.payload.get('start_char', 0)
                    end = point.payload.get('end_char', 0)
                    color = colors[i % len(colors)]
                    
                    # Tekst "pomiędzy" chunkami (jeśli jest dziura - to pozwala wykryć błędy chunkera)
                    if start > last_end:
                        missing_text = full_doc[last_end:start]
                        # Zaznaczamy brakujący tekst na czerwono, żeby rzucał się w oczy
                        html_parts.append(f'<span style="background-color: #ffcdd2; color: red; text-decoration: line-through;" title="BRAKUJĄCY FRAGMENT!">{missing_text}</span>')
                    
                    # Chunk właściwy
                    # Zabezpieczenie na wypadek gdyby indeksy wychodziły poza zakres (powinno być ok)
                    chunk_text = full_doc[start:end] if end <= len(full_doc) else point.payload['page_content']
                    
                    html_parts.append(
                        f'<span style="background-color: {color}; padding: 2px; border-radius: 3px;" '
                        f'title="Chunk #{point.payload.get("chunk_id", i)} | Znaki: {start}-{end}">{chunk_text}</span>'
                    )
                    last_end = end
                
                # Reszta tekstu po ostatnim chunku
                if last_end < len(full_doc):
                    html_parts.append(f'<span style="color: gray;">{full_doc[last_end:]}</span>')
                
                full_html = f'''
                <div style="font-family: Georgia, serif; line-height: 1.8; white-space: pre-wrap; padding: 20px; border: 1px solid #ddd; border-radius: 5px;">
                {"".join(html_parts)}
                </div>
                '''
                st.markdown(full_html, unsafe_allow_html=True)
                st.caption("💡 Legenda: Każdy kolor to inny chunk. Czerwone tło oznacza 'zgubiony' tekst (jeśli występuje).")
            else:
                st.warning("Brak pełnego dokumentu w metadanych pierwszego chunka.")

# === SEKCJA PORÓWNANIA Z ORYGINAŁEM ===
st.divider()
if st.checkbox("📋 Pokaż oryginalny tekst z JSON (do porównania)"):
    original = next((item for item in raw_data if item['id'] == selected_id), None)
    if original:
        st.text_area("Oryginalny tekst:", original['text'], height=300)
import streamlit as st
from langchain_qdrant import QdrantVectorStore  # <--- NOWY IMPORT (zamiast langchain_community)
from langchain_huggingface import HuggingFaceEmbeddings
from qdrant_client import QdrantClient

# --- KONFIGURACJA ---
DB_PATH = "qdrant_db"
COLLECTION_NAME = "polish_law_semantic"
EMBEDDING_MODEL_NAME = "sdadas/st-polish-paraphrase-from-distilroberta"

st.set_page_config(page_title="Asystent Prawny AI", page_icon="⚖️")
st.title("⚖️ Polski Asystent Prawny (RAG)")
st.write("Zadaj pytanie, a system znajdzie odpowiednie orzecznictwo sądowe.")

@st.cache_resource
def load_db():
    print("Ładowanie modelu AI...")
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)
    
    client = QdrantClient(path=DB_PATH)
    
    # Używamy nowej klasy QdrantVectorStore
    db = QdrantVectorStore(
        client=client,
        collection_name=COLLECTION_NAME,
        embedding=embeddings,
    )
    return db

try:
    vector_store = load_db()
    st.success("✅ Baza wiedzy załadowana pomyślnie!")
except Exception as e:
    st.error(f"❌ Błąd ładowania bazy: {e}")
    st.stop()

query = st.text_input("Twoje pytanie prawne:", placeholder="Np. Czy można odwołać darowiznę z powodu rażącej niewdzięczności?")

if query:
    st.write("---")
    st.info(f"🔍 Szukam odpowiedzi w bazie dla: '{query}'...")
    
    # Ta metoda działa poprawnie w nowej bibliotece
    results = vector_store.similarity_search(query, k=4)
    
    if not results:
        st.warning("Nie znaleziono pasujących dokumentów.")
    else:
        st.subheader("Znalezione Orzecznictwo:")
        for i, doc in enumerate(results):
            with st.expander(f"Dokument #{i+1} - Sygnatura: {doc.metadata.get('signature', 'Brak')}"):
                st.markdown(f"**Data:** {doc.metadata.get('date', 'Nieznana')}")
                st.write(doc.page_content)
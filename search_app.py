import streamlit as st
from langchain_huggingface import HuggingFaceEmbeddings
from qdrant_client import QdrantClient
from sentence_transformers import CrossEncoder
from openai import OpenAI
import re

# --- KONFIGURACJA ---
DB_PATH = "qdrant_db"
COLLECTION_NAME = "polish_law_hybrid"
MODEL_NAME = "sdadas/st-polish-paraphrase-from-distilroberta"
RERANKER_MODEL = "sdadas/polish-reranker-large-ranknet"

# Słowa kluczowe związane z wyrokiem/karą
VERDICT_KEYWORDS = [
    "skazuje", "wymierza", "orzeka", "karę", "pozbawienia wolności",
    "grzywny", "lat", "miesięcy", "warunkowo", "zawieszeniu",
    "oskarżonego uznaje za winnego", "na mocy art"
]

QUERY_REWRITE_PROMPT = """Jesteś ekspertem od polskiego prawa. Użytkownik szuka orzeczeń sądowych w bazie danych.

Twoim zadaniem jest przekształcić zapytanie użytkownika na optymalną frazę do wyszukiwania semantycznego.

Zasady:
1. Usuń zbędne słowa typu "pokaż mi", "znajdź", "szukam"
2. Dodaj synonimy prawnicze i powiązane terminy
3. Dodaj odpowiednie artykuły kodeksu jeśli znasz (np. art. 286 kk dla oszustwa)
4. Odpowiedz TYLKO zoptymalizowaną frazą wyszukiwania, bez wyjaśnień
5. Fraza powinna mieć 5-20 słów

Przykłady:
- "Pokaż mi wyroki za kradzież" → "kradzież art. 278 kk zabór mienia kara pozbawienia wolności wyrok skazujący"
- "Co grozi za wyłudzenie kredytu?" → "wyłudzenie kredytu pożyczki oszustwo art. 286 kk art. 297 kk fałszywe dokumenty kara"
- "Szukam spraw o alimenty" → "alimenty świadczenia alimentacyjne obowiązek alimentacyjny art. 133 kro utrzymanie dziecka"

Zapytanie użytkownika: {query}

Zoptymalizowana fraza:"""

st.set_page_config(page_title="Wyszukiwarka Orzeczeń", page_icon="⚖️", layout="wide")
st.title("⚖️ Wyszukiwarka Polskich Orzeczeń Sądowych")

@st.cache_resource
def load_resources():
    """Ładuje modele - cache'owane."""
    embeddings = HuggingFaceEmbeddings(model_name=MODEL_NAME)
    client = QdrantClient(path=DB_PATH)
    reranker = CrossEncoder(RERANKER_MODEL, max_length=512)
    return embeddings, client, reranker

def get_openai_client():
    """Zwraca klienta OpenAI jeśli klucz jest dostępny."""
    api_key = st.session_state.get("openai_api_key", "")
    if api_key:
        return OpenAI(api_key=api_key)
    return None

def rewrite_query_with_llm(query, openai_client):
    """Przepisuje zapytanie używając LLM."""
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",  # Tańszy i szybszy, wystarczy do tego zadania
            messages=[
                {"role": "user", "content": QUERY_REWRITE_PROMPT.format(query=query)}
            ],
            max_tokens=100,
            temperature=0.3
        )
        rewritten = response.choices[0].message.content.strip()
        return rewritten
    except Exception as e:
        st.warning(f"⚠️ Błąd LLM: {e}. Używam oryginalnego zapytania.")
        return query

def extract_text_from_pdf(uploaded_file):
    """Wyodrębnia tekst z pliku PDF."""
    try:
        import pymupdf
        pdf_bytes = uploaded_file.read()
        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text.strip()
    except ImportError:
        st.error("❌ Brak biblioteki PyMuPDF. Zainstaluj: `pip install pymupdf`")
        return None
    except Exception as e:
        st.error(f"❌ Błąd odczytu PDF: {e}")
        return None

def contains_verdict(text):
    """Sprawdza czy tekst zawiera słowa kluczowe związane z wyrokiem."""
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in VERDICT_KEYWORDS)

def rerank_results(query, results, reranker, top_k):
    """Re-rankuje wyniki używając Cross-Encoder."""
    if not results:
        return results
    
    pairs = [(query, r.payload['page_content']) for r in results]
    rerank_scores = reranker.predict(pairs)
    
    reranked = sorted(
        zip(results, rerank_scores), 
        key=lambda x: x[1], 
        reverse=True
    )
    
    final_results = []
    for result, new_score in reranked[:top_k]:
        result.score = float(new_score)
        final_results.append(result)
    
    return final_results

def search_documents(query_vector, client, num_results, use_reranking, reranker, query_text):
    """Wyszukuje dokumenty z opcjonalnym re-rankingiem."""
    fetch_limit = num_results * 5 if use_reranking else num_results
    
    results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        limit=fetch_limit,
        with_payload=True
    ).points
    
    if use_reranking and results:
        results = rerank_results(query_text, results, reranker, num_results)
    else:
        results = results[:num_results]
    
    return results

def display_results(results, num_results, prioritize_verdict=False, is_reranked=False):
    """Wyświetla wyniki wyszukiwania."""
    
    if prioritize_verdict and results:
        with_verdict = [r for r in results if contains_verdict(r.payload.get('page_content', ''))]
        without_verdict = [r for r in results if not contains_verdict(r.payload.get('page_content', ''))]
        results = (with_verdict + without_verdict)[:num_results]
        
        if with_verdict:
            st.info(f"🎯 Znaleziono {len(with_verdict)} fragmentów zawierających wyroki/kary")
    
    if not results:
        st.warning("Brak wyników.")
        return
    
    score_label = "Trafność" if is_reranked else "Podobieństwo"
    st.subheader(f"📋 Znaleziono {len(results)} pasujących fragmentów:")
    
    seen_docs = set()
    doc_counter = 0
    
    for i, result in enumerate(results):
        payload = result.payload
        doc_id = payload['origin_id']
        
        if doc_id in seen_docs:
            continue
        seen_docs.add(doc_id)
        doc_counter += 1
        
        signature = payload['signature']
        date = payload['date']
        score = result.score
        
        full_doc = payload.get('full_document', payload['page_content'])
        matched_chunk = payload['page_content']
        
        is_verdict = contains_verdict(matched_chunk)
        verdict_badge = " 🔨" if is_verdict else ""
        
        st.markdown(f"### 📄 Dokument #{doc_counter}{verdict_badge}")
        
        if is_reranked:
            st.markdown(f"**Sygnatura:** `{signature}` | **Data:** {date} | **{score_label}:** {score:.3f}")
        else:
            st.markdown(f"**Sygnatura:** `{signature}` | **Data:** {date} | **{score_label}:** {score:.2%}")
        
        with st.expander("🎯 Pasujący fragment", expanded=True):
            bg_color = "#d4edda" if is_verdict else "#fff3cd"
            border_color = "#28a745" if is_verdict else "#ffc107"
            st.markdown(
                f'<div style="background-color: {bg_color}; padding: 15px; border-radius: 5px; border-left: 4px solid {border_color};">'
                f'{matched_chunk}'
                f'</div>',
                unsafe_allow_html=True
            )
        
        with st.expander("📜 Pokaż pełny dokument"):
            if matched_chunk in full_doc:
                idx = full_doc.find(matched_chunk)
                before = full_doc[:idx]
                after = full_doc[idx + len(matched_chunk):]
                
                highlighted_html = (
                    f'<div style="font-family: Georgia, serif; line-height: 1.8;">'
                    f'{before}'
                    f'<mark style="background-color: #ffff00; padding: 2px;">{matched_chunk}</mark>'
                    f'{after}'
                    f'</div>'
                )
                st.markdown(highlighted_html, unsafe_allow_html=True)
            else:
                st.text(full_doc)
        
        st.divider()

# --- SIDEBAR: Ustawienia API ---
with st.sidebar:
    st.header("⚙️ Ustawienia")
    
    api_key = st.text_input(
        "🔑 OpenAI API Key:",
        type="password",
        help="Opcjonalne. Pozwala na inteligentne przepisywanie zapytań.",
        key="openai_api_key"
    )
    
    if api_key:
        st.success("✅ API Key ustawiony")
    else:
        st.info("💡 Bez API Key system działa, ale bez inteligentnego przepisywania zapytań.")
    
    st.divider()
    st.markdown("""
    ### Jak działa system:
    1. **Bez LLM:** Bezpośrednie wyszukiwanie semantyczne
    2. **Z LLM:** GPT przepisuje zapytanie na optymalną frazę prawniczą
    3. **Re-ranking:** Dodatkowy model poprawia trafność
    """)

# --- ŁADOWANIE ZASOBÓW ---
try:
    with st.spinner("🔄 Ładowanie modeli..."):
        embeddings, client, reranker = load_resources()
    st.success("✅ System załadowany!")
except Exception as e:
    st.error(f"❌ Błąd: {e}")
    st.stop()

# === TABS ===
tab1, tab2 = st.tabs(["🔍 Wyszukiwanie tekstowe", "📄 Upload PDF"])

# --- TAB 1: Wyszukiwanie tekstowe ---
with tab1:
    query = st.text_input(
        "Wpisz zapytanie (możesz pisać naturalnie!):", 
        placeholder="Np. Pokaż mi sprawy o wyłudzenie pożyczki",
        key="text_query"
    )
    
    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
    with col1:
        num_results = st.slider("Liczba wyników:", 1, 10, 5, key="text_num")
    with col2:
        use_reranking = st.checkbox("🎯 Re-ranking", value=True, 
                                     help="Poprawia trafność wyników")
    with col3:
        prioritize_verdict = st.checkbox("🔨 Priorytet: wyroki", value=False)
    with col4:
        openai_client = get_openai_client()
        use_llm = st.checkbox(
            "🧠 Smart Query", 
            value=bool(openai_client),
            disabled=not openai_client,
            help="Używa GPT do optymalizacji zapytania" if openai_client else "Wymaga API Key w ustawieniach"
        )
    
    if query:
        st.divider()
        
        # === PRZEPISANIE ZAPYTANIA Z LLM ===
        search_query = query
        if use_llm and openai_client:
            with st.spinner("🧠 Analizuję zapytanie..."):
                search_query = rewrite_query_with_llm(query, openai_client)
            
            st.info(f"🔄 **Oryginalne:** {query}\n\n🎯 **Zoptymalizowane:** {search_query}")
        
        # === WYSZUKIWANIE ===
        with st.spinner("🔍 Wyszukiwanie..." + (" + re-ranking" if use_reranking else "")):
            query_vector = embeddings.embed_query(search_query)
            results = search_documents(
                query_vector, client, num_results, 
                use_reranking, reranker, search_query
            )
        
        display_results(results, num_results, prioritize_verdict, is_reranked=use_reranking)

# --- TAB 2: Upload PDF ---
with tab2:
    st.markdown("""
    ### 📤 Prześlij swoje orzeczenie
    Załaduj plik PDF z orzeczeniem sądowym, a system znajdzie podobne sprawy w bazie danych.
    """)
    
    uploaded_file = st.file_uploader(
        "Wybierz plik PDF:",
        type=["pdf"],
        help="Maksymalny rozmiar pliku: 200MB"
    )
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        num_results_pdf = st.slider("Liczba wyników:", 1, 10, 5, key="pdf_num")
    with col2:
        use_reranking_pdf = st.checkbox("🎯 Re-ranking", value=True, key="pdf_rerank")
    with col3:
        prioritize_verdict_pdf = st.checkbox("🔨 Priorytet: wyroki", value=False, key="pdf_verdict")
    
    if uploaded_file is not None:
        with st.spinner("📖 Odczytywanie PDF..."):
            extracted_text = extract_text_from_pdf(uploaded_file)
        
        if extracted_text:
            with st.expander("👁️ Podgląd wyodrębnionego tekstu", expanded=False):
                st.text_area(
                    "Tekst z PDF:",
                    extracted_text[:5000] + ("..." if len(extracted_text) > 5000 else ""),
                    height=200,
                    disabled=True
                )
            
            st.info(f"📊 Wyodrębniono {len(extracted_text)} znaków tekstu")
            
            if st.button("🔍 Znajdź podobne orzeczenia", type="primary"):
                st.divider()
                
                with st.spinner("🧠 Analizowanie dokumentu..."):
                    if len(extracted_text) <= 3000:
                        text_sample = extracted_text
                    else:
                        chunk_size = 1500
                        text_sample = (
                            extracted_text[:chunk_size] + " " +
                            extracted_text[len(extracted_text)//2 - chunk_size//2 : len(extracted_text)//2 + chunk_size//2] + " " +
                            extracted_text[-chunk_size:]
                        )
                    
                    query_vector = embeddings.embed_query(text_sample)
                    results = search_documents(
                        query_vector, client, num_results_pdf,
                        use_reranking_pdf, reranker, text_sample[:1000]
                    )
                
                st.success("✅ Wyszukiwanie zakończone!")
                display_results(results, num_results_pdf, prioritize_verdict_pdf, is_reranked=use_reranking_pdf)
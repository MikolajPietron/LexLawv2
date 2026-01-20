import streamlit as st
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, Range
from sentence_transformers import SentenceTransformer, CrossEncoder
from openai import OpenAI
import re
from dotenv import load_dotenv
import os
import torch

# Ładuj .env
load_dotenv()

# --- KONFIGURACJA ---
QDRANT_URL = os.getenv("QDRANT_URL")  
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = "polish_law_e5"  # Nowa kolekcja
MODEL_NAME = "intfloat/multilingual-e5-large"  # Nowy model
RERANKER_MODEL = "sdadas/polish-reranker-large-ranknet"

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# Słowa kluczowe związane z wyrokiem/karą
VERDICT_KEYWORDS = [
    "skazuje", "wymierza", "orzeka", "karę", "pozbawienia wolności",
    "grzywny", "lat", "miesięcy", "warunkowo", "zawieszeniu",
    "oskarżonego uznaje za winnego", "na mocy art"
]

# Mapowania typów (do wyświetlania)
COURT_TYPES = {
    "COMMON": "🏛️ Sąd powszechny",
    "SUPREME": "⚖️ Sąd Najwyższy",
    "CONSTITUTIONAL_TRIBUNAL": "📜 Trybunał Konstytucyjny",
    "NATIONAL_APPEAL_CHAMBER": "📋 KIO"
}

JUDGMENT_TYPES = {
    "SENTENCE": "📝 Wyrok",
    "DECISION": "📋 Postanowienie",
    "RESOLUTION": "📜 Uchwała",
    "REASONS": "📄 Uzasadnienie"
}

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


# === FUNKCJE POMOCNICZE ===

@st.cache_resource
def load_resources():
    """Ładuje modele - cache'owane."""
    # E5 model
    embedder = SentenceTransformer(MODEL_NAME, device=DEVICE)
    embedder.max_seq_length = 512
    
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    reranker = CrossEncoder(RERANKER_MODEL, max_length=512, device=DEVICE)
    
    return embedder, client, reranker


@st.cache_resource
def get_openai_client():
    """Zwraca klienta OpenAI z .env - cache'owane."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    return OpenAI(api_key=api_key)


def rewrite_query_with_llm(query, openai_client):
    """Przepisuje zapytanie używając LLM."""
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
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


def build_date_filter(date_from=None, date_to=None):
    """Buduje filtr Qdrant tylko na podstawie dat."""
    if not date_from and not date_to:
        return None
    
    range_params = {}
    if date_from:
        range_params["gte"] = date_from.strftime("%Y-%m-%d")
    if date_to:
        range_params["lte"] = date_to.strftime("%Y-%m-%d")
    
    return Filter(
        must=[
            FieldCondition(
                key="judgment_date",
                range=Range(**range_params)
            )
        ]
    )


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


def search_documents(query_vector, client, num_results, use_reranking, reranker, query_text,
                     date_from=None, date_to=None):
    """Wyszukuje dokumenty z re-rankingiem i filtrem dat."""
    fetch_limit = num_results * 5 if use_reranking else num_results
    
    # Filtr tylko po dacie
    date_filter = build_date_filter(date_from, date_to)
    
    results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        query_filter=date_filter,
        limit=fetch_limit,
        with_payload=True
    ).points
    
    if use_reranking and results:
        results = rerank_results(query_text, results, reranker, num_results)
    else:
        results = results[:num_results]
    
    return results


def display_results(results, num_results, prioritize_verdict=False, is_reranked=False):
    """Wyświetla wyniki wyszukiwania z metadanymi."""
    
    if prioritize_verdict and results:
        with_verdict = [r for r in results if contains_verdict(r.payload.get('page_content', ''))]
        without_verdict = [r for r in results if not contains_verdict(r.payload.get('page_content', ''))]
        results = (with_verdict + without_verdict)[:num_results]
        
        if with_verdict:
            st.info(f"🎯 Znaleziono {len(with_verdict)} fragmentów zawierających wyroki/kary")
    
    if not results:
        st.warning("Brak wyników dla podanych kryteriów.")
        return
    
    score_label = "Trafność" if is_reranked else "Podobieństwo"
    st.subheader(f"📋 Znaleziono {len(results)} pasujących fragmentów:")
    
    seen_docs = set()
    doc_counter = 0
    
    for i, result in enumerate(results):
        payload = result.payload
        doc_id = payload.get('origin_id', i)
        
        if doc_id in seen_docs:
            continue
        seen_docs.add(doc_id)
        doc_counter += 1
        
        # Podstawowe dane
        signature = payload.get('signature', 'Brak')
        date = payload.get('judgment_date', payload.get('date', 'Brak'))
        score = result.score
        
        # Metadane (do wyświetlenia, nie do filtrowania)
        court_type = payload.get('court_type', '')
        judgment_type = payload.get('judgment_type', '')
        court_name = payload.get('court_name', '')
        keywords = payload.get('keywords', [])
        judges = payload.get('judges', [])
        
        full_doc = payload.get('full_document', payload.get('page_content', ''))
        matched_chunk = payload.get('page_content', '')
        
        is_verdict = contains_verdict(matched_chunk)
        verdict_badge = " 🔨" if is_verdict else ""
        
        # === NAGŁÓWEK DOKUMENTU ===
        st.markdown(f"### 📄 Dokument #{doc_counter}{verdict_badge}")
        
        # Wiersz z sygnaturą i score
        if is_reranked:
            st.markdown(f"**Sygnatura:** `{signature}` | **Data:** {date} | **{score_label}:** {score:.3f}")
        else:
            st.markdown(f"**Sygnatura:** `{signature}` | **Data:** {date} | **{score_label}:** {score:.2%}")
        
        # === BADGES (metadane - tylko wyświetlanie) ===
        badges = []
        if court_type and court_type in COURT_TYPES:
            badges.append(COURT_TYPES[court_type])
        if judgment_type and judgment_type in JUDGMENT_TYPES:
            badges.append(JUDGMENT_TYPES[judgment_type])
        
        if badges:
            badges_html = " ".join([f'<span style="background-color: #e9ecef; padding: 3px 8px; border-radius: 12px; margin-right: 5px; font-size: 0.85em;">{b}</span>' for b in badges])
            st.markdown(badges_html, unsafe_allow_html=True)
        
        # === DODATKOWE METADANE ===
        meta_parts = []
        if court_name:
            meta_parts.append(f"🏛️ {court_name}")
        if judges:
            judges_str = ", ".join(judges[:3])
            if len(judges) > 3:
                judges_str += f" (+{len(judges)-3})"
            meta_parts.append(f"👨‍⚖️ {judges_str}")
        if keywords:
            kw_str = ", ".join(keywords[:5])
            if len(keywords) > 5:
                kw_str += f" (+{len(keywords)-5})"
            meta_parts.append(f"🏷️ {kw_str}")
        
        if meta_parts:
            st.caption(" | ".join(meta_parts))
        
        # === PASUJĄCY FRAGMENT ===
        with st.expander("🎯 Pasujący fragment", expanded=True):
            bg_color = "#d4edda" if is_verdict else "#fff3cd"
            border_color = "#28a745" if is_verdict else "#ffc107"
            st.markdown(
                f'<div style="background-color: {bg_color}; padding: 15px; border-radius: 5px; border-left: 4px solid {border_color};">'
                f'{matched_chunk}'
                f'</div>',
                unsafe_allow_html=True
            )
        
        # === PEŁNY DOKUMENT ===
        with st.expander("📜 Pokaż pełny dokument"):
            if matched_chunk and matched_chunk in full_doc:
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
                st.text(full_doc[:10000] if len(full_doc) > 10000 else full_doc)
        
        st.divider()


# === SPRAWDZENIE API KEY NA STARCIE ===
openai_client = get_openai_client()
if not openai_client:
    st.error("❌ Brak klucza OPENAI_API_KEY w pliku .env!")
    st.info("Smart Query jest wymagane. Dodaj klucz API do pliku `.env`:\n\n`OPENAI_API_KEY=sk-...`")
    st.stop()


# === SIDEBAR ===
with st.sidebar:
    st.header("⚙️ Ustawienia")
    
    st.success("✅ Smart Query aktywne (GPT-4o-mini)")
    
    st.divider()
    
    # === FILTR DATY ===
    st.header("📅 Filtr daty")
    
    use_date_filter = st.checkbox("Włącz filtr daty", value=False)
    
    date_from = None
    date_to = None
    
    if use_date_filter:
        col1, col2 = st.columns(2)
        with col1:
            date_from = st.date_input(
                "Od:",
                value=None,
                format="YYYY-MM-DD"
            )
        with col2:
            date_to = st.date_input(
                "Do:",
                value=None,
                format="YYYY-MM-DD"
            )
    
    st.divider()
    
    # Info
    st.markdown("""
    ### Jak działa system:
    1. **🧠 Smart Query** - GPT optymalizuje każde zapytanie
    2. **Wzbogacone embeddingi** - metadane są częścią wektora
    3. **Filtr daty** - zawęża przestrzeń wyszukiwania
    4. **Re-ranking** - poprawia kolejność wyników
    """)
    
   


# === ŁADOWANIE ZASOBÓW ===
try:
    with st.spinner("🔄 Ładowanie modeli..."):
        embeddings, client, reranker = load_resources()
    st.success("✅ System załadowany!")
except Exception as e:
    
    st.error(f"❌ Błąd ładowania: {e}")
    st.info("Upewnij się, że uruchomiłeś `hybrid_ingest.py` i utworzyłeś kolekcję.")
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
    
    col1, col2 = st.columns([1, 1])
    with col1:
        num_results = st.slider("Liczba wyników:", 1, 20, 5, key="text_num")
    with col2:
        use_reranking = st.checkbox("🎯 Re-ranking", value=True,
                                     help="Poprawia trafność wyników")
    
    prioritize_verdict = st.checkbox("🔨 Priorytet: wyroki/kary", value=False)
    
    if query:
        st.divider()
        
        # Info o filtrze daty
        if use_date_filter and (date_from or date_to):
            date_info = []
            if date_from:
                date_info.append(f"od {date_from}")
            if date_to:
                date_info.append(f"do {date_to}")
            st.info(f"📅 Filtr daty: {' '.join(date_info)}")
        
        # === PRZEPISANIE ZAPYTANIA Z LLM (OBOWIĄZKOWE) ===
        with st.spinner("🧠 Analizuję zapytanie..."):
            search_query = rewrite_query_with_llm(query, openai_client)
        
        st.info(f"🔄 **Oryginalne:** {query}\n\n🎯 **Zoptymalizowane:** {search_query}")
        
        # === WYSZUKIWANIE ===
        with st.spinner("🔍 Wyszukiwanie..." + (" + re-ranking" if use_reranking else "")):
            query_vector = embeddings.encode(
    f"query: {search_query}",  # E5 wymaga prefixu "query:" dla zapytań!
    normalize_embeddings=True
).tolist()
            results = search_documents(
                query_vector, client, num_results,
                use_reranking, reranker, search_query,
                date_from=date_from if use_date_filter else None,
                date_to=date_to if use_date_filter else None
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
    
    col1, col2 = st.columns([1, 1])
    with col1:
        num_results_pdf = st.slider("Liczba wyników:", 1, 20, 5, key="pdf_num")
    with col2:
        use_reranking_pdf = st.checkbox("🎯 Re-ranking", value=True, key="pdf_rerank")
    
    prioritize_verdict_pdf = st.checkbox("🔨 Priorytet: wyroki/kary", value=False, key="pdf_verdict")
    
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
                    # Próbkowanie tekstu dla dużych dokumentów
                    if len(extracted_text) <= 3000:
                        text_sample = extracted_text
                    else:
                        chunk_size = 1500
                        text_sample = (
                            extracted_text[:chunk_size] + " " +
                            extracted_text[len(extracted_text)//2 - chunk_size//2:len(extracted_text)//2 + chunk_size//2] + " " +
                            extracted_text[-chunk_size:]
                        )
                    
                    query_vector = embeddings.encode(
                        f"query: {text_sample}",
                        normalize_embeddings=True
                    ).tolist()
                    results = search_documents(
                        query_vector, client, num_results_pdf,
                        use_reranking_pdf, reranker, text_sample[:1000],
                        date_from=date_from if use_date_filter else None,
                        date_to=date_to if use_date_filter else None
                    )
                
                st.success("✅ Wyszukiwanie zakończone!")
                display_results(results, num_results_pdf, prioritize_verdict_pdf, is_reranked=use_reranking_pdf)
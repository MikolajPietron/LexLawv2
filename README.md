# ⚖️ LexSearch - Wyszukiwarka Polskich Orzeczeń Sądowych

System wyszukiwania semantycznego orzeczeń sądowych z funkcjami RAG (Retrieval-Augmented Generation).

## 🚀 Szybki start

### Wymagania

- Python 3.10+
- Konto Qdrant Cloud lub lokalna instancja Qdrant
- Klucz API OpenAI

### Instalacja

1. **Sklonuj repozytorium:**
```bash
git clone <repo-url>
cd Licencjat
```

2. **Utwórz wirtualne środowisko:**
```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
# lub
source .venv/bin/activate  # Linux/Mac
```

3. **Zainstaluj zależności:**
```bash
pip install -r requirements.txt
```

4. **Skonfiguruj zmienne środowiskowe (.env):**
```env
QDRANT_URL=https://your-cluster.qdrant.io
QDRANT_API_KEY=your-qdrant-api-key
OPENAI_API_KEY=sk-your-openai-key
```

### Uruchomienie

#### Aplikacja Streamlit (główna):
```bash
streamlit run search_app.py
```
Otwórz: http://localhost:8501

#### REST API:
```bash
uvicorn api:app --reload --port 8000
```
Otwórz: http://localhost:8000/docs

### Ingesting danych:
```bash
python hybrid_ingest.py
```

---

## 🏗️ Architektura

### Komponenty

1. **Tool Registry** (`tools_registry.py`)
   - Rejestr dozwolonych narzędzi (allowlist)
   - Schematy walidacji parametrów
   - Konwersja do formatu OpenAI function-calling

2. **Tool Dispatcher** (`tools_dispatcher.py`)
   - Bezpieczne wykonywanie narzędzi
   - Timeout i retry logic
   - Kategoryzacja błędów
   - Observability logging

3. **Function Calling Loop** (`tools_dispatcher.py`)
   - Pętla: CALL → EXECUTE → FINALIZE
   - Automatyczny wybór narzędzi przez LLM
   - Pakowanie kontekstu do modelu

4. **Guardrails** (`search_app.py` + `output_guardrails.py`)
   - Input validation (prompt injection detection)
   - Output validation (PII masking, hallucination check)
   - Rate limiting

5. **RAG Pipeline** (`search_app.py`)
   - Embeddingi: `intfloat/multilingual-e5-large`
   - Wektorowa baza: Qdrant
   - Re-ranking: `sdadas/polish-reranker-large-ranknet`
   - Generowanie odpowiedzi: GPT-4o-mini

6. **Ewaluacja** (`evaluation_tests.py`)
   - 10 przypadków testowych
   - Metryki: success rate, precision, avg time
   - Raport w formacie Markdown

---

## 📡 REST API

### Endpoints

#### `POST /search`
Wyszukuje orzeczenia.

**Request:**
```json
{
  "query": "kradzież art 278 kk",
  "num_results": 5,
  "use_reranking": true
}
```

**Response:**
```json
{
  "original_query": "kradzież art 278 kk",
  "optimized_query": "kradzież zabór mienia art. 278 kk kara pozbawienia wolności",
  "results": [...]
}
```

#### `POST /ask` 
Pełne zapytanie RAG z generowaniem odpowiedzi.

**Request:**
```json
{
  "query": "Jakie kary grożą za oszustwo?"
}
```

#### `GET /health`
Sprawdza status systemu.

---

## 🛡️ Bezpieczeństwo (Guardrails)

### Input Guardrails
- Wykrywanie prompt injection (30+ wzorców)
- Sanityzacja znaków specjalnych
- Limit długości zapytania (2000 znaków)
- Rate limiting (30 zapytań/min)

### Output Guardrails
- Maskowanie danych osobowych (PESEL, email, NIP)
- Wykrywanie wycieków promptu systemowego
- Blokowanie niebezpiecznej treści
- Sprawdzanie hallucynacji prawniczych

---

## 🧪 Testy

### Uruchamianie testów:

W aplikacji Streamlit → zakładka "🧪 Testy"

### Przypadki testowe:

| ID | Nazwa | Kategoria |
|---|---|---|
| guardrails_1 | Wykrywanie prompt injection | guardrails |
| guardrails_2 | Limit długości zapytania | guardrails |
| tools_1 | Walidacja parametrów narzędzia | tools |
| tools_2 | Blokowanie nieznanych narzędzi | tools |
| tools_3 | Obsługa timeout | tools |
| rag_1 | Wyszukiwanie semantyczne | rag |
| rag_2 | Generacja odpowiedzi RAG | rag |
| security_1 | Walidacja wyjścia - PII | security |
| security_2 | Rate limiting | security |
| fc_1 | Automatyczny wybór narzędzia | function_calling |

---

## 📊 Observability

Dashboard dostępny w zakładce "📊 Observability":
- Metryki wywołań narzędzi
- Success rate per narzędzie
- Średni czas wykonania
- Logi w czasie rzeczywistym
- Logi bezpieczeństwa

---

## 🐳 Docker

### Build:
```bash
docker build -t lexsearch .
```

### Run:
```bash
docker run -p 7860:7860 --env-file .env lexsearch
```

---

## 📁 Struktura projektu

```
├── search_app.py          # Główna aplikacja Streamlit
├── api.py                 # REST API (FastAPI)
├── tools_registry.py      # Rejestr narzędzi + schematy
├── tools_dispatcher.py    # Dispatcher + function-calling
├── output_guardrails.py   # Walidacja wyjścia
├── evaluation_tests.py    # Testy ewaluacyjne
├── hybrid_ingest.py       # Ingesting danych do Qdrant
├── requirements.txt       # Zależności Python
├── Dockerfile             # Konteneryzacja
├── .env                   # Zmienne środowiskowe (nie commitować!)
└── data/                  # Dane
    └── full_dataset.jsonl
```

---

## 📝 Licencja

MIT License

## 👤 Autor

Projekt licencjacki
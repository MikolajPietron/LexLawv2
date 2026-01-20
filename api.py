from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer, CrossEncoder
from openai import OpenAI
import os
from dotenv import load_dotenv
import torch
import aiohttp

load_dotenv()

app = FastAPI(title="Polish Law Search API")

# CORS dla Next.js
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Konfiguracja ---
COLLECTION_NAME = "polish_law_e5"
MODEL_NAME = "intfloat/multilingual-e5-large"
RERANKER_MODEL = "sdadas/polish-reranker-large-ranknet"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# --- Modele (ładowane przy starcie) ---
embedder = None
reranker = None
qdrant = None
openai_client = None

@app.on_event("startup")
async def load_models():
    global embedder, reranker, qdrant, openai_client
    print(f"🔧 Ładowanie modeli na {DEVICE}...")
    
    embedder = SentenceTransformer(MODEL_NAME, device=DEVICE)
    embedder.max_seq_length = 512
    
    reranker = CrossEncoder(RERANKER_MODEL, max_length=512, device=DEVICE)
    qdrant = QdrantClient(url=os.getenv("QDRANT_URL"), api_key=os.getenv("QDRANT_API_KEY"))
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    print("✅ Modele załadowane!")

# --- Modele Request/Response ---
class SearchRequest(BaseModel):
    query: str
    num_results: int = 5
    use_reranking: bool = True

class SearchResult(BaseModel):
    origin_id: int
    signature: str
    judgment_date: str
    court_type: str
    court_name: str
    judgment_type: str
    keywords: list[str]
    judges: list[str]
    matched_chunk: str
    score: float

class SearchResponse(BaseModel):
    original_query: str
    optimized_query: str
    results: list[SearchResult]

# --- Funkcje pomocnicze ---
QUERY_REWRITE_PROMPT = """Jesteś ekspertem od polskiego prawa. Przekształć zapytanie na optymalną frazę do wyszukiwania semantycznego.
Zasady: usuń zbędne słowa, dodaj synonimy prawnicze, dodaj artykuły kodeksu jeśli znasz.
Odpowiedz TYLKO zoptymalizowaną frazą (5-20 słów).

Zapytanie: {query}

Zoptymalizowana fraza:"""

def rewrite_query(query: str) -> str:
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": QUERY_REWRITE_PROMPT.format(query=query)}],
            max_tokens=100,
            temperature=0.3
        )
        return response.choices[0].message.content.strip()
    except:
        return query

def rerank_results(query: str, results, top_k: int):
    if not results:
        return []
    pairs = [(query, r.payload['page_content']) for r in results]
    scores = reranker.predict(pairs)
    reranked = sorted(zip(results, scores), key=lambda x: x[1], reverse=True)
    return [(r, float(s)) for r, s in reranked[:top_k]]

# --- Endpointy ---
@app.get("/health")
def health_check():
    return {"status": "ok", "device": DEVICE}

@app.post("/search", response_model=SearchResponse)
def search(request: SearchRequest):
    # 1. Przepisz zapytanie
    optimized = rewrite_query(request.query)
    
    # 2. Generuj embedding
    query_vector = embedder.encode(
        f"query: {optimized}",
        normalize_embeddings=True
    ).tolist()
    
    # 3. Szukaj w Qdrant
    fetch_limit = request.num_results * 5 if request.use_reranking else request.num_results
    
    search_results = qdrant.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        limit=fetch_limit,
        with_payload=True
    ).points
    
    # 4. Re-ranking
    if request.use_reranking and search_results:
        scored_results = rerank_results(optimized, search_results, request.num_results)
    else:
        scored_results = [(r, float(r.score)) for r in search_results[:request.num_results]]
    
    # 5. Formatuj wyniki
    results = []
    for result, score in scored_results:
        p = result.payload
        results.append(SearchResult(
            origin_id=p.get("origin_id", 0),
            signature=p.get("signature", ""),
            judgment_date=p.get("judgment_date", ""),
            court_type=p.get("court_type", ""),
            court_name=p.get("court_name", ""),
            judgment_type=p.get("judgment_type", ""),
            keywords=p.get("keywords", []),
            judges=p.get("judges", []),
            matched_chunk=p.get("page_content", ""),
            score=score
        ))
    
    return SearchResponse(
        original_query=request.query,
        optimized_query=optimized,
        results=results
    )

@app.get("/judgment/{judgment_id}")
async def get_full_judgment(judgment_id: int):
    """Pobiera pełny tekst orzeczenia z SAOS API."""
    import re
    
    url = f"https://www.saos.org.pl/api/judgments/{judgment_id}"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                judgment_data = data.get("data", {})
                
                # Wyczyść HTML
                raw_text = judgment_data.get("textContent", "")
                clean_text = re.sub(r'<.*?>', ' ', raw_text)
                clean_text = " ".join(clean_text.split())
                
                court_cases = judgment_data.get("courtCases", [])
                signature = court_cases[0].get("caseNumber", "") if court_cases else ""
                
                return {
                    "id": judgment_id,
                    "signature": signature,
                    "text": clean_text,
                    "judgment_date": judgment_data.get("judgmentDate", ""),
                    "court_type": judgment_data.get("courtType", ""),
                }
            raise HTTPException(status_code=404, detail="Judgment not found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
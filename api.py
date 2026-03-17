from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx
from pydantic import BaseModel
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer, CrossEncoder
from openai import OpenAI
import os
from dotenv import load_dotenv
import torch
import aiohttp
import jwt
import time
from datetime import datetime, timezone
from urllib.request import urlopen
import json
import base64
import stripe

load_dotenv()
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID")
CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY")

app = FastAPI(title="Polish Law Search API")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
def _get_clerk_frontend_api() -> str:
    """Derive the Clerk Frontend API URL from the publishable key."""
    pk = os.getenv("PUBLIC_KEY", "")
    encoded = pk.split("_", 2)[-1]
    padded = encoded + "=" * (-len(encoded) % 4)
    domain = base64.b64decode(padded).decode("utf-8").rstrip("$")
    return f"https://{domain}"

CLERK_FRONTEND_API = _get_clerk_frontend_api()

# CORS — restricted to known origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

COLLECTION_NAME = "polish_law_e5"
MODEL_NAME = "intfloat/multilingual-e5-large"
RERANKER_MODEL = "sdadas/polish-reranker-large-ranknet"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

embedder = None
reranker = None
qdrant = None
openai_client = None

# ─── Clerk JWT verification ────────────────────────────────────────

_jwks_cache: dict = {"keys": None, "fetched_at": 0}

def _get_jwks() -> list:
    """Fetch and cache Clerk JWKS keys (refresh every 1 hour)."""
    now = time.time()
    if _jwks_cache["keys"] and now - _jwks_cache["fetched_at"] < 3600:
        return _jwks_cache["keys"]
    
    jwks_url = f"{CLERK_FRONTEND_API}/.well-known/jwks.json"
    with urlopen(jwks_url) as resp:
        jwks = json.loads(resp.read())
    _jwks_cache["keys"] = jwks["keys"]
    _jwks_cache["fetched_at"] = now
    return jwks["keys"]

def _verify_clerk_token(token: str) -> dict:
    """Verify a Clerk JWT and return the payload."""
    header = jwt.get_unverified_header(token)
    jwks_keys = _get_jwks()
    
    matching_key = None
    for key in jwks_keys:
        if key["kid"] == header["kid"]:
            matching_key = key
            break
    if not matching_key:
        raise HTTPException(status_code=401, detail="Invalid token key")
    
    public_key = jwt.algorithms.RSAAlgorithm.from_jwk(matching_key)
    payload = jwt.decode(
        token,
        public_key,
        algorithms=["RS256"],
        issuer=CLERK_FRONTEND_API,
    )
    return payload


async def get_current_user(request: Request) -> dict | None:
    """FastAPI dependency: returns Clerk JWT payload or None for anonymous."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header[7:]
    if not token:
        return None
    try:
        return _verify_clerk_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# ─── Rate limiter ──────────────────────────────────────────────────

RATE_LIMIT_AUTH = 10
RATE_LIMIT_ANON = 3
RATE_LIMIT_PRO = 1000
_rate_limit_store: dict[str, list[float]] = {}

def _get_today_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")

def _check_rate_limit(key: str, limit: int) -> bool:
    """Returns True if under limit, False if exceeded."""
    today = _get_today_key()
    full_key = f"{today}:{key}"
    
    stale = [k for k in _rate_limit_store if not k.startswith(today)]
    for k in stale:
        del _rate_limit_store[k]
    
    timestamps = _rate_limit_store.get(full_key, [])
    if len(timestamps) >= limit:
        return False
    timestamps.append(time.time())
    _rate_limit_store[full_key] = timestamps
    return True

def _get_user_tier(user_payload: dict | None) -> str:
    """Extract tier from JWT metadata. Defaults to 'free'."""
    if not user_payload:
        return "anonymous"
    metadata = user_payload.get("metadata", {})
    return metadata.get("tier", "free")

def check_search_rate_limit(user_payload: dict | None, request: Request):
    """Check rate limit based on user tier. Raises 429 if exceeded."""
    tier = _get_user_tier(user_payload)
    
    if tier == "pro":
        key = f"user:{user_payload['sub']}"
        limit = RATE_LIMIT_PRO
        authenticated = True
    elif user_payload:
        key = f"user:{user_payload['sub']}"
        limit = RATE_LIMIT_AUTH
        authenticated = True
    else:
        forwarded = request.headers.get("X-Forwarded-For", "")
        client_ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown")
        key = f"ip:{client_ip}"
        limit = RATE_LIMIT_ANON
        authenticated = False
    
    if not _check_rate_limit(key, limit):
        return JSONResponse(
            status_code=429,
            content={
                "detail": "rate_limit",
                "limit": limit,
                "authenticated": authenticated,
                "tier": tier,
            },
        )
    return None

# ─── Models & startup ──────────────────────────────────────────────

@app.on_event("startup")
async def load_models():
    global embedder, reranker, qdrant, openai_client
    print(f"🔧 Ładowanie modeli na {DEVICE}...")
    
    embedder = SentenceTransformer(MODEL_NAME, device=DEVICE)
    embedder.max_seq_length = 512
    
    reranker = CrossEncoder(RERANKER_MODEL, max_length=512, device=DEVICE)
    qdrant = QdrantClient(url=os.getenv("QDRANT_URL"), api_key=os.getenv("QDRANT_API_KEY"), timeout=60)
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    print("✅ Modele załadowane!")


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

class AskResponse(BaseModel):
    original_query: str
    optimized_query: str
    answer: str
    results: list[SearchResult]


QUERY_REWRITE_PROMPT = """Jesteś ekspertem od polskiego prawa. Przekształć zapytanie na optymalną frazę do wyszukiwania semantycznego.
Zasady: usuń zbędne słowa, dodaj synonimy prawnicze, dodaj artykuły kodeksu jeśli znasz.
Odpowiedz TYLKO zoptymalizowaną frazą (5-20 słów).

Zapytanie: {query}

Zoptymalizowana fraza:"""

RAG_RESPONSE_PROMPT = """Na podstawie WYŁĄCZNIE poniższych fragmentów orzeczeń sądowych, odpowiedz na pytanie użytkownika.

ŚCISŁE ZASADY:
1. Odpowiadaj TYLKO po polsku.
2. Korzystaj WYŁĄCZNIE z informacji zawartych w podanych fragmentach orzeczeń. NIE dodawaj wiedzy z zewnątrz.
3. Każde twierdzenie MUSI być poparte konkretną sygnaturą orzeczenia z podanego kontekstu.
4. Cytuj sygnatury i daty orzeczeń w formacie: (sygn. XXX, data).
5. Jeśli podane fragmenty nie zawierają wystarczających informacji, aby odpowiedzieć na pytanie — napisz wprost: "Na podstawie znalezionych orzeczeń nie mogę udzielić pełnej odpowiedzi na to pytanie."
6. NIE spekuluj, NIE uzupełniaj luk własną wiedzą, NIE podawaj informacji prawnych, których nie ma w kontekście.
7. Podsumuj kluczowe tezy z orzeczeń — tylko te, które wynikają z podanych fragmentów.
8. Odpowiedź powinna być profesjonalna i czytelna, maksymalnie 500 słów.

Pytanie użytkownika: {query}

Fragmenty orzeczeń z bazy danych:
{context}

Twoja odpowiedź (oparta WYŁĄCZNIE na powyższych fragmentach):"""

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

def generate_rag_response(query: str, results: list[SearchResult]) -> str:
    """Generate a RAG answer from search results using GPT."""
    if not results:
        return "Nie znaleziono orzeczeń pasujących do zapytania. Spróbuj użyć innych słów kluczowych."

    context_parts = []
    for i, r in enumerate(results[:5], 1):
        context_parts.append(
            f"[{i}] Sygnatura: {r.signature} | Data: {r.judgment_date} | Sąd: {r.court_name}\n"
            f"Fragment: {r.matched_chunk[:800]}\n"
        )
    context = "\n---\n".join(context_parts)

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
    "role": "system",
    "content": (
        "Jesteś asystentem prawniczym systemu wyszukiwania orzeczeń sądowych. "
        "Odpowiadasz WYŁĄCZNIE na podstawie dostarczonych fragmentów orzeczeń. "
        "NIGDY nie używasz własnej wiedzy prawniczej ani nie dodajesz informacji spoza podanego kontekstu. "
        "Jeśli kontekst nie zawiera odpowiedzi — mówisz o tym wprost. "
        "Każde twierdzenie popieras sygnaturą orzeczenia. Odpowiadasz TYLKO po polsku."
    )
},
                {
                    "role": "user",
                    "content": RAG_RESPONSE_PROMPT.format(query=query, context=context)
                }
            ],
            max_tokens=1000,
            temperature=0.2
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Nie udało się wygenerować odpowiedzi."


# ─── Endpoints ─────────────────────────────────────────────────────

@app.get("/health")
def health_check():
    return {"status": "ok", "device": DEVICE}

@app.post("/search", response_model=SearchResponse)
async def search(
    request_body: SearchRequest,
    request: Request,
    user_payload: dict | None = Depends(get_current_user),
):
    rate_limit_response = check_search_rate_limit(user_payload, request)
    if rate_limit_response:
        return rate_limit_response
    
    optimized = rewrite_query(request_body.query)
    
    query_vector = embedder.encode(
        f"query: {optimized}",
        normalize_embeddings=True
    ).tolist()
    
    fetch_limit = request_body.num_results * 5 if request_body.use_reranking else request_body.num_results
    
    search_results = qdrant.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        limit=fetch_limit,
        with_payload=True
    ).points
    
    if request_body.use_reranking and search_results:
        scored_results = rerank_results(optimized, search_results, request_body.num_results)
    else:
        scored_results = [(r, float(r.score)) for r in search_results[:request_body.num_results]]
    
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
        original_query=request_body.query,
        optimized_query=optimized,
        results=results
    )

@app.post("/ask", response_model=AskResponse)
async def ask(
    request_body: SearchRequest,
    request: Request,
    user_payload: dict | None = Depends(get_current_user),
):
    """RAG endpoint: search + AI-generated answer in one call."""
    rate_limit_response = check_search_rate_limit(user_payload, request)
    if rate_limit_response:
        return rate_limit_response

    optimized = rewrite_query(request_body.query)

    query_vector = embedder.encode(
        f"query: {optimized}",
        normalize_embeddings=True
    ).tolist()

    fetch_limit = request_body.num_results * 5 if request_body.use_reranking else request_body.num_results

    search_results = qdrant.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        limit=fetch_limit,
        with_payload=True
    ).points

    if request_body.use_reranking and search_results:
        scored_results = rerank_results(optimized, search_results, request_body.num_results)
    else:
        scored_results = [(r, float(r.score)) for r in search_results[:request_body.num_results]]

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

    answer = generate_rag_response(request_body.query, results)

    return AskResponse(
        original_query=request_body.query,
        optimized_query=optimized,
        answer=answer,
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
        
async def update_clerk_user_metadata(user_id: str, public_metadata: dict):
    """Update a Clerk user's publicMetadata via the Clerk Backend API."""
    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            f"https://api.clerk.com/v1/users/{user_id}",
            headers={
                "Authorization": f"Bearer {CLERK_SECRET_KEY}",
                "Content-Type": "application/json",
            },
            json={"public_metadata": public_metadata},
        )
        resp.raise_for_status()
        
class CheckoutRequest(BaseModel):
    success_url: str
    cancel_url: str

@app.post("/create-checkout-session")
async def create_checkout_session(
    body: CheckoutRequest,
    request: Request,
    user_payload: dict | None = Depends(get_current_user),
):
    """Create a Stripe Checkout Session for the Pro plan."""
    if not user_payload:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    user_id = user_payload["sub"]
    email = user_payload.get("email")
    
    # Check if user already has a Stripe customer ID in metadata
    metadata = user_payload.get("metadata", {})
    customer_id = metadata.get("stripeCustomerId")
    
    checkout_params = {
        "mode": "payment",
        "line_items": [{"price": STRIPE_PRICE_ID, "quantity": 1}],
        "success_url": body.success_url,
        "cancel_url": body.cancel_url,
        "metadata": {"clerk_user_id": user_id},
    }
    
    if customer_id:
        checkout_params["customer"] = customer_id
    else:
        checkout_params["customer_email"] = email
    
    session = stripe.checkout.Session.create(**checkout_params)
    return {"url": session.url}


@app.post("/create-portal-session")
async def create_portal_session(
    request: Request,
    user_payload: dict | None = Depends(get_current_user),
):
    """Create a Stripe Billing Portal session for managing subscriptions."""
    if not user_payload:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    metadata = user_payload.get("metadata", {})
    customer_id = metadata.get("stripeCustomerId")
    
    if not customer_id:
        raise HTTPException(status_code=400, detail="No active subscription")
    
    portal_session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=FRONTEND_URL,
    )
    return {"url": portal_session.url}


@app.post("/stripe/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events to sync payment status with Clerk."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    print(f"📩 Webhook event: {event['type']}")
    
    if event["type"] == "checkout.session.completed":
        session_data = event["data"]["object"]
        clerk_user_id = session_data["metadata"].get("clerk_user_id")
        customer_id = session_data.get("customer")
        print(f"  clerk_user_id: {clerk_user_id}")
        print(f"  customer_id: {customer_id}")
        print(f"  CLERK_SECRET_KEY set: {CLERK_SECRET_KEY is not None}")
        
        if clerk_user_id:
            try:
                await update_clerk_user_metadata(clerk_user_id, {
                    "tier": "pro",
                    "stripeCustomerId": customer_id,
                })
                print(f"  ✅ Clerk metadata updated for {clerk_user_id}")
            except Exception as e:
                print(f"  ❌ Clerk update failed: {e}")
    
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
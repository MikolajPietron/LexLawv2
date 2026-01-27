import asyncio
import aiohttp
import json
import re
import os
from datetime import datetime
import ssl
import certifi

API_URL = "https://www.saos.org.pl/api/dump/judgments"
DATA_FOLDER = "."  # Zapisuj w tym samym folderze
PROGRESS_FILE = "scraper_progress.json"
OUTPUT_FILE = "full_dataset.jsonl"  # JSONL - jedna linia = jedno orzeczenie

CURRENT_DATE = datetime.now().strftime("%Y-%m-%d")
TARGET_COUNT = float('inf')  # Pobierz WSZYSTKO
BATCH_SIZE = 100
TIMEOUT_SECONDS = 30
MAX_RETRIES = 5
SAVE_EVERY = 100  # Zapisuj postęp co 100 orzeczeń
DELAY = 0.2

def clean_html(raw_html):
    if not raw_html:
        return ""
    clean = re.sub(r'<.*?>', ' ', raw_html)
    return " ".join(clean.split())

def extract_judgment_data(item):
    """Wyodrębnia dane z orzeczenia."""
    court_cases = item.get("courtCases", [])
    signature = court_cases[0].get("caseNumber", "") if court_cases else ""
    
    judges = item.get("judges", [])
    judges_names = [j.get("name", "") for j in judges]
    
    keywords = item.get("keywords", [])
    
    court_type = item.get("courtType", "")
    court_name = ""
    
    if court_type == "COMMON":
        division = item.get("division", {})
        court = division.get("court", {})
        court_name = court.get("name", "")
    elif court_type == "SUPREME":
        court_name = "Sąd Najwyższy"
    elif court_type == "CONSTITUTIONAL_TRIBUNAL":
        court_name = "Trybunał Konstytucyjny"
    elif court_type == "NATIONAL_APPEAL_CHAMBER":
        court_name = "Krajowa Izba Odwoławcza"
    
    return {
        "id": item.get("id"),
        "signature": signature,
        "judgment_date": item.get("judgmentDate"),
        "judgment_type": item.get("judgmentType", ""),
        "court_type": court_type,
        "court_name": court_name,
        "judges": judges_names,
        "keywords": keywords,
        "text": clean_html(item.get("textContent", "")),
    }

def load_progress():
    """Wczytuje postęp z poprzedniej sesji."""
    filepath = os.path.join(DATA_FOLDER, PROGRESS_FILE)
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            progress = json.load(f)
            print(f"📂 Wznawiam od strony {progress['last_page']}, pobrano {progress['count']:,} orzeczeń")
            return progress
    return {"last_page": 0, "count": 0, "seen_ids": []}

def save_progress(page, count, seen_ids):
    """Zapisuje postęp."""
    filepath = os.path.join(DATA_FOLDER, PROGRESS_FILE)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump({
            "last_page": page,
            "count": count,
            "seen_ids": list(seen_ids)[-10000:] if len(seen_ids) > 10000 else list(seen_ids)
        }, f)

def append_judgments(judgments):
    """Dopisuje orzeczenia do pliku JSONL."""
    filepath = os.path.join(DATA_FOLDER, OUTPUT_FILE)
    with open(filepath, "a", encoding="utf-8") as f:
        for j in judgments:
            f.write(json.dumps(j, ensure_ascii=False) + "\n")

async def fetch_dump_page(session, page_number, retry=0):
    params = {
        "pageSize": BATCH_SIZE,
        "pageNumber": page_number,
        "judgmentEndDate": CURRENT_DATE,
        "withGenerated": "false"
    }
    
    try:
        async with session.get(API_URL, params=params, timeout=aiohttp.ClientTimeout(total=TIMEOUT_SECONDS)) as response:
            if response.status == 200:
                data = await response.json()
                
                # Pokaż całkowitą liczbę przy pierwszej stronie
                if page_number == 0:
                    total = data.get("queryTemplate", {}).get("info", {}).get("totalResults", "?")
                    print(f"📊 Całkowita liczba orzeczeń w SAOS: {total}")
                
                return data.get("items", [])
            elif response.status == 429:
                wait_time = 30 * (retry + 1)
                print(f"⚠️ Rate limit! Czekam {wait_time}s...")
                await asyncio.sleep(wait_time)
                return await fetch_dump_page(session, page_number, retry)
            else:
                print(f"⚠️ Błąd {response.status} na stronie {page_number}")
                return []
    except asyncio.TimeoutError:
        if retry < MAX_RETRIES:
            print(f"⏳ Timeout strona {page_number}, retry {retry+1}/{MAX_RETRIES}...")
            await asyncio.sleep(5 * (retry + 1))
            return await fetch_dump_page(session, page_number, retry + 1)
        print(f"❌ Max retries na stronie {page_number}")
        return []
    except Exception as e:
        if retry < MAX_RETRIES:
            print(f"🔄 Błąd: {e}, retry za 10s...")
            await asyncio.sleep(10)
            return await fetch_dump_page(session, page_number, retry + 1)
        return []

async def main():
    print(f"🚀 Scraper SAOS - Pobieranie WSZYSTKICH orzeczeń!")
    print(f"📅 Data końcowa: {CURRENT_DATE}")
    
    # Wczytaj postęp
    progress = load_progress()
    page = progress["last_page"]
    count = progress["count"]
    seen_ids = set(progress.get("seen_ids", []))
    
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    connector = aiohttp.TCPConnector(ssl=ssl_context, limit=5)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
        "Accept": "application/json",
    }
    
    buffer = []
    empty_pages = 0
    start_time = datetime.now()
    
    async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
        while True:  # Bez limitu - aż skończą się dane
            items = await fetch_dump_page(session, page)
            
            if not items:
                empty_pages += 1
                if empty_pages >= 5:
                    print("✅ Koniec danych - pobrano wszystko!")
                    break
                page += 1
                continue
            
            empty_pages = 0
            
            for item in items:
                item_id = item.get("id")
                
                if item_id in seen_ids:
                    continue
                
                raw_text = item.get("textContent")
                if not raw_text or len(raw_text) < 500:
                    continue
                
                court_cases = item.get("courtCases", [])
                if not court_cases or not court_cases[0].get("caseNumber"):
                    continue
                
                judgment = extract_judgment_data(item)
                buffer.append(judgment)
                seen_ids.add(item_id)
                count += 1
            
            # Zapisz bufor
            if len(buffer) >= SAVE_EVERY:
                append_judgments(buffer)
                save_progress(page, count, seen_ids)
                
                elapsed = (datetime.now() - start_time).total_seconds()
                speed = count / elapsed if elapsed > 0 else 0
                print(f"📥 Strona {page:,} | Pobrano: {count:,} | Prędkość: {speed:.1f}/s")
                buffer = []
            
            page += 1
            await asyncio.sleep(DELAY)
    
    # Zapisz resztę
    if buffer:
        append_judgments(buffer)
        save_progress(page, count, seen_ids)
    
    elapsed_total = (datetime.now() - start_time).total_seconds() / 3600
    print(f"\n✅ ZAKOŃCZONO!")
    print(f"📊 Pobrano: {count:,} orzeczeń")
    print(f"⏱️ Czas: {elapsed_total:.1f} godzin")
    print(f"📂 Plik: {os.path.join(DATA_FOLDER, OUTPUT_FILE)}")
    
    # Usuń plik postępu
    progress_path = os.path.join(DATA_FOLDER, PROGRESS_FILE)
    if os.path.exists(progress_path):
        os.remove(progress_path)

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
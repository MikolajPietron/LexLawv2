import asyncio
import aiohttp
import json
import re
import os
import time
from datetime import datetime
import ssl
import certifi


API_URL = "https://www.saos.org.pl/api/dump/judgments"
DATA_FOLDER = "data"
FILENAME = "clean_dataset.json"


CURRENT_DATE = datetime.now().strftime("%Y-%m-%d")

TARGET_COUNT = 1000  
BATCH_SIZE = 100   

# Timeout i retry
TIMEOUT_SECONDS = 30
MAX_RETRIES = 3

def clean_html(raw_html):
    if not raw_html: return ""
    
    clean = re.sub(r'<.*?>', ' ', raw_html)
    return " ".join(clean.split())

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
                items = data.get("items", [])
                
                # Pokaż ile jest w sumie orzeczeń w bazie
                if page_number == 0:
                    total_count = data.get("queryTemplate", {}).get("info", {}).get("totalResults", "nieznana")
                    print(f"📊 Całkowita liczba orzeczeń w bazie SAOS: {total_count}")
                
                return items
            else:
                print(f"⚠️ Błąd API (Strona {page_number}): Kod {response.status}")
                return []
    except asyncio.TimeoutError:
        if retry < MAX_RETRIES:
            print(f"⏳ Timeout na stronie {page_number}, ponawiam ({retry+1}/{MAX_RETRIES})...")
            await asyncio.sleep(2)
            return await fetch_dump_page(session, page_number, retry + 1)
        print(f"❌ Timeout na stronie {page_number} po {MAX_RETRIES} próbach")
        return []
    except aiohttp.ClientConnectorError as e:
        if retry < MAX_RETRIES:
            print(f"🔄 Błąd połączenia, ponawiam za 5s ({retry+1}/{MAX_RETRIES})...")
            await asyncio.sleep(5)
            return await fetch_dump_page(session, page_number, retry + 1)
        print(f"❌ Błąd połączenia: {e}")
        return []
    except Exception as e:
        print(f"❌ Nieoczekiwany błąd: {e}")
        return []

async def main():
    print(f"🚀 Start Dumpera... Pobieramy dane do daty: {CURRENT_DATE}")
    
    valid_judgments = []
    page = 0
    
    # Konfiguracja SSL
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    
    # Headers żeby wyglądać jak przeglądarka
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
    }
    
    async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
        while len(valid_judgments) < TARGET_COUNT:
            print(f"📥 Pobieranie strony {page} (Mamy: {len(valid_judgments)}/{TARGET_COUNT})...")
            
            items = await fetch_dump_page(session, page)
            
            if not items:
                print("⚠️ Brak więcej danych lub koniec bazy.")
                break
            
            for item in items:
                raw_text = item.get("textContent")
                signature = item.get("courtCases", [{}])[0].get("caseNumber", "Brak")
                
                if not raw_text or len(raw_text) < 500:
                    continue
                    
                if signature == "Brak":
                    continue

                valid_judgments.append({
                    "id": item["id"],
                    "date": item["judgmentDate"],
                    "signature": signature,
                    "text": clean_html(raw_text)
                })
                
                if len(valid_judgments) >= TARGET_COUNT:
                    break
            
            page += 1
            await asyncio.sleep(0.3)  # Dłuższa przerwa żeby nie przeciążać API

    if not os.path.exists(DATA_FOLDER):
        os.makedirs(DATA_FOLDER)
        
    filepath = os.path.join(DATA_FOLDER, FILENAME)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(valid_judgments, f, ensure_ascii=False, indent=2)

    print(f"\n✅ ZAKOŃCZONO! Pobrano {len(valid_judgments)} czystych wyroków.")
    print(f"📂 Plik zapisany w: {filepath}")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
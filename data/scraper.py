import asyncio
import aiohttp
import json
import re
import os
from datetime import datetime
import ssl
import certifi

API_URL = "https://www.saos.org.pl/api/dump/judgments"
DATA_FOLDER = "data"
FILENAME = "full_dataset.json"

CURRENT_DATE = datetime.now().strftime("%Y-%m-%d")
TARGET_COUNT = 100  # Zwiększ do 10k na test
BATCH_SIZE = 100
TIMEOUT_SECONDS = 30
MAX_RETRIES = 3
SAVE_EVERY = 500  # Checkpoint

def clean_html(raw_html):
    if not raw_html:
        return ""
    clean = re.sub(r'<.*?>', ' ', raw_html)
    return " ".join(clean.split())

def extract_judgment_data(item):
    """Wyodrębnia WSZYSTKIE dostępne dane z orzeczenia."""
    
    # Podstawowe dane
    court_cases = item.get("courtCases", [])
    signature = court_cases[0].get("caseNumber", "") if court_cases else ""
    
    # Sędziowie
    judges = item.get("judges", [])
    judges_list = []
    for judge in judges:
        judges_list.append({
            "name": judge.get("name", ""),
            "function": judge.get("function", ""),  # PRESIDING_JUDGE, REPORTING_JUDGE, etc.
            "roles": judge.get("specialRoles", [])
        })
    
    # Podstawy prawne (przywoływane artykuły)
    legal_bases = item.get("referencedRegulations", [])
    regulations = []
    for reg in legal_bases:
        regulations.append({
            "title": reg.get("journalTitle", ""),
            "year": reg.get("journalYear"),
            "entry": reg.get("journalEntry"),
            "text": reg.get("text", "")
        })
    
    # Słowa kluczowe
    keywords = item.get("keywords", [])
    
    # Powiązane orzeczenia
    referenced_judgments = item.get("referencedCourtCases", [])
    
    return {
        # === IDENTYFIKACJA ===
        "id": item.get("id"),
        "source": item.get("source", ""),  # COMMON_COURT, SUPREME_COURT, etc.
        
        # === SYGNATURY ===
        "signature": signature,
        "all_signatures": [c.get("caseNumber", "") for c in court_cases],
        
        # === DATY ===
        "judgment_date": item.get("judgmentDate"),
        "receipt_date": item.get("receiptDate"),  # Data wpływu
        
        # === TYP ORZECZENIA ===
        "judgment_type": item.get("judgmentType", ""),  # SENTENCE, DECISION, RESOLUTION, REASONS
        
        # === SĄD ===
        "court_type": item.get("courtType", ""),  # COMMON, SUPREME, CONSTITUTIONAL, etc.
        "court_name": "",  # Będzie uzupełnione poniżej
        "court_division": "",
        
        # === SĘDZIOWIE ===
        "judges": judges_list,
        "judges_count": len(judges_list),
        
        # === PODSTAWY PRAWNE ===
        "legal_bases": regulations,
        "legal_bases_count": len(regulations),
        
        # === SŁOWA KLUCZOWE (z SAOS) ===
        "keywords": keywords,
        
        # === POWIĄZANE SPRAWY ===
        "referenced_cases": referenced_judgments,
        
        # === TREŚĆ ===
        "text": clean_html(item.get("textContent", "")),
        "text_length": len(item.get("textContent", "") or ""),
        
        # === METADANE ===
        "has_thesis": bool(item.get("courtReporters")),  # Czy ma tezę
    }

def enrich_court_data(judgment, item):
    """Uzupełnia dane o sądzie w zależności od typu."""
    
    court_type = item.get("courtType", "")
    
    if court_type == "COMMON":
        # Sądy powszechne
        division = item.get("division", {})
        court = division.get("court", {})
        judgment["court_name"] = court.get("name", "")
        judgment["court_division"] = division.get("name", "")
        judgment["court_code"] = court.get("code", "")
        
    elif court_type == "SUPREME":
        # Sąd Najwyższy
        chamber = item.get("supremeCourtChamber", {})
        judgment["court_name"] = "Sąd Najwyższy"
        judgment["court_division"] = chamber.get("name", "")
        
        # Skład SN
        personnel_type = item.get("personnelType", "")
        judgment["personnel_type"] = personnel_type  # ONE_PERSON, THREE_PERSON, etc.
        
    elif court_type == "CONSTITUTIONAL_TRIBUNAL":
        # Trybunał Konstytucyjny
        judgment["court_name"] = "Trybunał Konstytucyjny"
        dissenting = item.get("dissentingOpinions", [])
        judgment["dissenting_opinions"] = [d.get("textContent", "") for d in dissenting]
        
    elif court_type == "NATIONAL_APPEAL_CHAMBER":
        # Krajowa Izba Odwoławcza
        judgment["court_name"] = "Krajowa Izba Odwoławcza"
        
    return judgment

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
                
                if page_number == 0:
                    total_count = data.get("queryTemplate", {}).get("info", {}).get("totalResults", "?")
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
        return []
    except Exception as e:
        if retry < MAX_RETRIES:
            print(f"🔄 Błąd: {e}, ponawiam za 5s ({retry+1}/{MAX_RETRIES})...")
            await asyncio.sleep(5)
            return await fetch_dump_page(session, page_number, retry + 1)
        return []

def save_checkpoint(judgments, filename):
    """Zapisuje checkpoint."""
    filepath = os.path.join(DATA_FOLDER, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(judgments, f, ensure_ascii=False, indent=2)
    print(f"💾 Checkpoint zapisany: {len(judgments)} orzeczeń")

async def main():
    print(f"🚀 Start pobierania pełnych danych... Data końcowa: {CURRENT_DATE}")
    
    valid_judgments = []
    page = 0
    
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
        "Accept": "application/json",
    }
    
    if not os.path.exists(DATA_FOLDER):
        os.makedirs(DATA_FOLDER)
    
    async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
        while len(valid_judgments) < TARGET_COUNT:
            print(f"📥 Strona {page} (Pobrano: {len(valid_judgments)}/{TARGET_COUNT})...")
            
            items = await fetch_dump_page(session, page)
            
            if not items:
                print("⚠️ Brak więcej danych.")
                break
            
            for item in items:
                raw_text = item.get("textContent")
                
                # Walidacja
                if not raw_text or len(raw_text) < 500:
                    continue
                
                court_cases = item.get("courtCases", [])
                if not court_cases or not court_cases[0].get("caseNumber"):
                    continue
                
                # Ekstrakcja pełnych danych
                judgment = extract_judgment_data(item)
                judgment = enrich_court_data(judgment, item)
                
                valid_judgments.append(judgment)
                
                if len(valid_judgments) >= TARGET_COUNT:
                    break
            
            # Checkpoint co SAVE_EVERY
            if len(valid_judgments) % SAVE_EVERY == 0 and len(valid_judgments) > 0:
                save_checkpoint(valid_judgments, f"checkpoint_{len(valid_judgments)}.json")
            
            page += 1
            await asyncio.sleep(0.3)
    
    # Zapisz finalny plik
    filepath = os.path.join(DATA_FOLDER, FILENAME)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(valid_judgments, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ ZAKOŃCZONO! Pobrano {len(valid_judgments)} orzeczeń z pełnymi danymi.")
    print(f"📂 Plik: {filepath}")
    
    # Statystyki
    court_types = {}
    judgment_types = {}
    for j in valid_judgments:
        ct = j.get("court_type", "UNKNOWN")
        jt = j.get("judgment_type", "UNKNOWN")
        court_types[ct] = court_types.get(ct, 0) + 1
        judgment_types[jt] = judgment_types.get(jt, 0) + 1
    
    print("\n📊 Statystyki:")
    print("Typy sądów:", court_types)
    print("Typy orzeczeń:", judgment_types)

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
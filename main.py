import sys
import asyncio
import pandas as pd
import aiohttp
from data.scraper import main as run_scraper

print("--------------------------------------------------")
print(f"✅ Sukces! Używasz Pythona: {sys.version.split()[0]}")
print(f"✅ Biblioteka Pandas załadowana (wersja: {pd.__version__})")
print(f"✅ Biblioteka Aiohttp załadowana (wersja: {aiohttp.__version__})")
print("--------------------------------------------------")


asyncio.run(run_scraper())
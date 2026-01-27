import sys
import asyncio
import pandas as pd
import aiohttp
from data.scraper import main as run_scraper
asyncio.run(run_scraper())
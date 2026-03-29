import os
import secrets
from dotenv import load_dotenv

load_dotenv()

FLASK_ENV = os.getenv("FLASK_ENV", "production")
FLASK_DEBUG = FLASK_ENV == "development"
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_hex(32))

BASE_URL = "https://api.spoda.ai"

SPODA_AUTH_COOKIE = os.getenv("SPODA_AUTH_COOKIE", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9,hi;q=0.8",
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "Origin": "https://www.spoda.ai",
    "Pragma": "no-cache",
    "Referer": "https://www.spoda.ai/",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Mobile Safari/537.36"
    ),
}

COOKIES = {
    "auth-cookie": SPODA_AUTH_COOKIE,
    "auth-role": "User",
}

DB_PATH = os.path.join(os.path.dirname(__file__), "spoda_cache.db")

CACHE_TTL_HOURS = 6

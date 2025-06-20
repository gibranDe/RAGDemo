import os
from dotenv import load_dotenv

load_dotenv()

# ────────────────── ENV VARS ──────────────────
MONGODB_URI = os.getenv("MONGODB_URI", "YOUR_ATLAS_URI")
VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY", "YOUR_VOYAGE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "YOUR_OPENAI_KEY")

# ────────────────── DATABASE CONFIG ──────────────────
DB_NAME = "demoDB"
COLL_NAME = "data"
INDEX_NAME = "ragIndex"

# ────────────────── EMBEDDING CONFIG ──────────────────
EMBED_MODEL = "voyage-3.5-lite"
LLM_MODEL = "gpt-4o"

# ────────────────── APP CONFIG ──────────────────
USERNAME = os.getenv("USERNAME", "anon")
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100
BATCH_SIZE = 64

# ────────────────── INGESTION CONFIG ──────────────────
PDF_DIR = "../pdfs"
SITEMAP_INDEX = "https://www.yoururl.com/sitemap.xml"
MAX_URLS = None #set up to none if you want to procees all. Be memory and time sensitive
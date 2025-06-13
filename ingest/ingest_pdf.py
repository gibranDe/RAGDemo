import os
import time
import uuid
from typing import List
from pymongo import MongoClient, UpdateOne
from langchain.text_splitter import RecursiveCharacterTextSplitter
from voyageai import Client as VoyageClient
from PyPDF2 import PdfReader
from config.config import (
    MONGODB_URI, VOYAGE_API_KEY, USERNAME, DB_NAME, COLL_NAME,
    CHUNK_SIZE, CHUNK_OVERLAP, BATCH_SIZE, EMBED_MODEL, PDF_DIR
)

print("[INFO] Starting PDF ingestion script")

# ─── MONGODB INIT ───
mongo_client = MongoClient(MONGODB_URI)
try:
    mongo_client.admin.command("ping")
    print("[INFO] Connected to MongoDB Atlas")
except Exception as e:
    raise RuntimeError(f"[ERROR] MongoDB Connection Error: {e}")
mongo_coll = mongo_client[DB_NAME][COLL_NAME]

# ─── VECTOR CLIENT ───
client_voy = VoyageClient(api_key=VOYAGE_API_KEY)
print("[INFO] VoyageAI client initialized")

# ─── TEXT SPLITTER ───
splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
)
print("[INFO] Text splitter configured")

# ─── HELPERS ───
def extract_text_from_pdf(pdf_path: str) -> str:
    print(f"[INFO] Reading PDF: {pdf_path}")
    try:
        reader = PdfReader(pdf_path)
        text = " ".join(page.extract_text() or "" for page in reader.pages)
        return text.strip()
    except Exception as e:
        print(f"[ERROR] Failed to read {pdf_path}: {e}")
        return ""

def chunk_text(text: str, source_name: str) -> List[dict]:
    chunks = splitter.split_text(text)
    print(f"[INFO] Split {len(chunks)} chunks from {source_name}")
    return [{"text": chunk, "source_pdf": source_name, "chunk_idx": idx} for idx, chunk in enumerate(chunks)]

def embed_batch(texts: List[str], model: str = MODEL) -> List[List[float]]:
    try:
        print(f"[INFO] Embedding batch of {len(texts)} texts")
        texts = [t[:24000] for t in texts]
        response = client_voy.embed(texts=texts, model=model)
        return response.embeddings
    except Exception as e:
        print(f"[EMBED ERROR] {e}")
        return [None] * len(texts)

# ─── MAIN INGESTION ───
def main(interactive: bool = True):
    print("[INFO] Starting ingestion pipeline")
    pdf_files = [os.path.join(PDF_DIR, f) for f in os.listdir(PDF_DIR) if f.endswith(".pdf")]
    print(f"[INFO] Found {len(pdf_files)} PDF files")
    for pdf in pdf_files:
        print(f"       → {pdf}")
    if interactive:
        resp = input("¿Deseas continuar con la ingesta? [y/N]: ").strip().lower()
        if resp != "y":
            print("[INFO] Ingesta cancelada por el usuario.")
            return

    raw_chunks = []
    for pdf_path in pdf_files:
        text = extract_text_from_pdf(pdf_path)
        if text:
            raw_chunks.extend(chunk_text(text, os.path.basename(pdf_path)))

    print(f"[INFO] Total chunks to process: {len(raw_chunks)}")

    bulk_ops = []
    total_ok = total_fail = 0

    for i in range(0, len(raw_chunks), BATCH_SIZE):
        print(f"[INFO] Processing batch {i // BATCH_SIZE + 1}")
        batch = raw_chunks[i:i + BATCH_SIZE]
        texts = [b["text"] for b in batch]
        vectors = embed_batch(texts)

        for chunk, vector in zip(batch, vectors):
            if vector is None:
                total_fail += 1
                continue
            doc = {
                "_id": str(uuid.uuid4()),
                "text": chunk["text"],
                "type": "PDF",
                "source": chunk["source_pdf"],
                "chunk_idx": chunk["chunk_idx"],
                "embedding": vector,
                "username": USERNAME,
                "ts": int(time.time())
            }
            bulk_ops.append(UpdateOne({"_id": doc["_id"]}, {"$set": doc}, upsert=True))
            total_ok += 1

        if len(bulk_ops) >= 200:
            mongo_coll.bulk_write(bulk_ops, ordered=False)
            print("[INFO] Bulk write executed for 200+ operations")
            bulk_ops.clear()

    if bulk_ops:
        mongo_coll.bulk_write(bulk_ops, ordered=False)
        print("[INFO] Final bulk write executed")

    print(f"[INFO] Successfully inserted: {total_ok:,} documents")
    print(f"[INFO] Failed embeddings: {total_fail:,}")
    print(f"[INFO] Collection size: {mongo_coll.count_documents({}):,}")

# ─── EXECUTE ───
if __name__ == "__main__":
    main()
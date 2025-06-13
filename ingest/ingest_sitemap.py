import time
import uuid
import requests
import xml.etree.ElementTree as ET
from typing import List, Generator, Iterator
from pymongo import MongoClient, UpdateOne
from bs4 import BeautifulSoup
from langchain.text_splitter import RecursiveCharacterTextSplitter
from voyageai import Client as VoyageClient
from pathlib import Path
import sys
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))
from config.config import (
    MONGODB_URI,
    VOYAGE_API_KEY,
    USERNAME,
    DB_NAME,
    COLL_NAME,
    SITEMAP_INDEX,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    BATCH_SIZE,
    EMBED_MODEL,
    MAX_URLS
)
# # ─── CONFIG ───
# MONGODB_URI = os.getenv("MONGODB_URI", "your-mongodb-uri")
# VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY", "your-voyage-api-key")
# USERNAME = os.getenv("USERNAME", "anon")
# DB_NAME = "RAGDemo"
# COLL_NAME = "data"
# SITEMAP_INDEX = "https://web.talana.com/sitemap.xml"
# CHUNK_SIZE = 512
# CHUNK_OVERLAP = 64
# BATCH_SIZE = 32
# MAX_URLS = None  # Set to None to process all URLs
# MODEL = "voyage-3.5-lite"

print("[INFO] Starting streaming web ingestion script")

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

# Obtener URLs
def get_urls_from_sitemap(sitemap_url: str) -> List[str]:
    print(f"[INFO] Fetching sitemap: {sitemap_url}")
    try:
        resp = requests.get(sitemap_url, timeout=60)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        ns = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        urls = [loc.text for loc in root.findall(".//ns:loc", ns)]
        print(f"[INFO] Found {len(urls)} URLs in sitemap")
        return urls
    except Exception as e:
        print(f"[ERROR] Failed to fetch sitemap: {e}")
        return []

# verificar url procesada
def is_url_already_processed(url: str) -> bool:
    return mongo_coll.find_one({"source": url}, {"_id": 1}) is not None

# scrapping
def scrape_page(url: str) -> tuple[str, dict]:

    try:
        print(f"[INFO] Scraping URL: {url}")
        
        # Headers para evitar bloqueos
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        resp = requests.get(url, timeout=15, headers=headers)
        resp.raise_for_status()
        
        soup = BeautifulSoup(resp.content, "html.parser")
        
        # Extraer título
        title = soup.title.string.strip() if soup.title else ""
        
        # Extraer meta description
        meta_desc = ""
        meta_tag = soup.find("meta", attrs={"name": "description"})
        if meta_tag:
            meta_desc = meta_tag.get("content", "")
        
        # Remover scripts, styles, etc.
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()
        
        # Obtener párrafos y headings
        paras = [p.get_text(strip=True) for p in soup.find_all("p") if p.get_text(strip=True)]
        headings = [h.get_text(strip=True) for h in soup.find_all(["h1", "h2", "h3"]) if h.get_text(strip=True)]
        
        # Combinar contenido
        content_parts = []
        if title:
            content_parts.append(f"Título: {title}")
        if meta_desc:
            content_parts.append(f"Descripción: {meta_desc}")
        if headings:
            content_parts.append("Secciones: " + " | ".join(headings))
        if paras:
            content_parts.extend(paras)
        
        content = "\n".join(content_parts)
        
        # Metadata adicional
        metadata = {
            "title": title,
            "meta_description": meta_desc,
            "headings_count": len(headings),
            "paragraphs_count": len(paras),
            "content_length": len(content),
            "status_code": resp.status_code
        }
        
        return content, metadata
        
    except Exception as e:
        print(f"[WARN] Failed to scrape {url}: {e}")
        return "", {"error": str(e)}

# validate content
def validate_content(content: str, url: str, min_length: int = 100) -> bool:
    if not content or len(content.strip()) < min_length:
        print(f"[WARN] Skipping {url}: content too short ({len(content)} chars)")
        return False
    
    # Verify boiler plates
    common_boilerplate = ["404", "page not found", "access denied", "login required"]
    content_lower = content.lower()
    if any(phrase in content_lower for phrase in common_boilerplate):
        print(f"[WARN] Skipping {url}: appears to be boilerplate content")
        return False
    
    return True

# ═══════════════════════════════════════════════════════════════════════════════
# GENERADORES STREAMING
# ═══════════════════════════════════════════════════════════════════════════════

def url_chunk_generator(urls: List[str], splitter: RecursiveCharacterTextSplitter) -> Generator[dict, None, None]:
# Generate chunks
    processed_urls = 0
    skipped_urls = 0
    
    for url in urls:
        # Skip 
        if is_url_already_processed(url):
            print(f"[INFO] Skipping already processed URL: {url}")
            skipped_urls += 1
            continue
        
        # Scraping
        content, metadata = scrape_page(url)

        if not validate_content(content, url):
            skipped_urls += 1
            continue
        
        # Generate chunks
        try:
            chunks = splitter.split_text(content)
            processed_urls += 1
            
            print(f"[INFO] Generated {len(chunks)} chunks from {url}")
            
            for idx, chunk in enumerate(chunks):
                yield {
                    "text": chunk,
                    "source_url": url,
                    "chunk_idx": idx,
                    "metadata": metadata,
                    "total_chunks": len(chunks)
                }
                
        except Exception as e:
            print(f"[ERROR] Failed to chunk content from {url}: {e}")
            skipped_urls += 1
            continue
        #pause
        #time.sleep(0.2)
    
    print(f"[INFO] URL processing complete: {processed_urls} processed, {skipped_urls} skipped")

def batch_generator(items: Iterator, batch_size: int) -> Generator[List, None, None]:
    batch = []
    for item in items:
        batch.append(item)
        if len(batch) >= batch_size:
            yield batch
            batch = []
    
    # Yield el último batch si no está vacío
    if batch:
        yield batch

#Embed streaming
def embed_batch_with_retry(texts: List[str], model: str = EMBED_MODEL, max_retries: int = 3) -> List[List[float]]:
    for attempt in range(max_retries):
        try:
            print(f"[INFO] Embedding batch of {len(texts)} texts (attempt {attempt + 1})")
            # Truncar textos para evitar límites de API
            texts = [t[:24000] for t in texts]
            response = client_voy.embed(texts=texts, model=model)
            return response.embeddings
        except Exception as e:
            print(f"[EMBED ERROR] Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Backoff exponencial
                print(f"[INFO] Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
            else:
                print(f"[ERROR] All embedding attempts failed")
                return [None] * len(texts)

# streaming for batch
def main_streaming_web_approach(urls: List[str]):
    print(f"[INFO] Starting streaming web ingestion for {len(urls)} URLs")
    
    # Contadores
    total_processed = 0
    total_failed = 0
    total_urls_processed = 0
    bulk_ops = []
    
    # Crear generador de chunks
    chunk_stream = url_chunk_generator(urls, splitter)
    
    # Procesar en batches
    for batch_num, chunk_batch in enumerate(batch_generator(chunk_stream, BATCH_SIZE)):
        print(f"[INFO] Processing batch {batch_num + 1} with {len(chunk_batch)} chunks")
        
        # Extraer textos para embedding
        texts = [chunk["text"] for chunk in chunk_batch]
        
        # Generar embeddings con retry
        embeddings = embed_batch_with_retry(texts)
        
        # Preparar documentos para MongoDB
        for chunk, embedding in zip(chunk_batch, embeddings):
            if embedding is None:
                total_failed += 1
                continue
            
            doc = {
                "_id": str(uuid.uuid4()),
                "text": chunk["text"],
                "type": "URL",
                "source": chunk["source_url"],
                "chunk_idx": chunk["chunk_idx"],
                "embedding": embedding,
                "username": USERNAME,
                "ts": int(time.time()),
                # Metadata adicional
                "metadata": {
                    "title": chunk["metadata"].get("title", ""),
                    "content_length": chunk["metadata"].get("content_length", 0),
                    "total_chunks": chunk["total_chunks"],
                    "scraping_date": time.strftime("%Y-%m-%d %H:%M:%S")
                }
            }
            bulk_ops.append(UpdateOne({"_id": doc["_id"]}, {"$set": doc}, upsert=True))
            total_processed += 1
        
        # Escribir a MongoDB cuando el buffer esté lleno
        if len(bulk_ops) >= 200:
            try:
                result = mongo_coll.bulk_write(bulk_ops, ordered=False)
                print(f"[INFO] Bulk write executed: {len(bulk_ops)} operations")
                print(f"[INFO] Inserted: {result.upserted_count}, Modified: {result.modified_count}")
                bulk_ops.clear()
            except Exception as e:
                print(f"[ERROR] MongoDB bulk write failed: {e}")
                # Continuar con el siguiente batch
        
        # Progreso cada 10 batches
        if (batch_num + 1) % 10 == 0:
            current_collection_size = mongo_coll.count_documents({})
            print(f"[PROGRESS] Processed {batch_num + 1} batches. Collection size: {current_collection_size:,}")
    
    # Escribir operaciones restantes
    if bulk_ops:
        try:
            result = mongo_coll.bulk_write(bulk_ops, ordered=False)
            print(f"[INFO] Final bulk write: {len(bulk_ops)} operations")
            print(f"[INFO] Final - Inserted: {result.upserted_count}, Modified: {result.modified_count}")
        except Exception as e:
            print(f"[ERROR] Final MongoDB write failed: {e}")
    
    # Estadísticas finales
    final_collection_size = mongo_coll.count_documents({})
    print(f"\n[SUMMARY] Processing Complete!")
    print(f"[SUMMARY] Successfully processed chunks: {total_processed:,}")
    print(f"[SUMMARY] Failed embeddings: {total_failed:,}")
    print(f"[SUMMARY] Success rate: {(total_processed/(total_processed + total_failed)*100):.1f}%")
    print(f"[SUMMARY] Final collection size: {final_collection_size:,}")
    
    return {
        "processed": total_processed,
        "failed": total_failed,
        "collection_size": final_collection_size
    }

#main funciton 

def main(interactive: bool = True):
    """Función principal con estrategia streaming"""
    print("[INFO] Starting streaming web ingestion pipeline")
    
    # Obtener URLs del sitemap
    all_urls = get_urls_from_sitemap(SITEMAP_INDEX)
    if not all_urls:
        print("[ERROR] No URLs found in sitemap. Exiting.")
        return
    #limit
    if MAX_URLS:
        all_urls = all_urls[:MAX_URLS]
        print(f"[INFO] Limited to first {MAX_URLS} URLs")
    
    print(f"[INFO] Total URLs to process: {len(all_urls)}")
    
    # Mostrar algunas URLs de ejemplo
    print("[INFO] Sample URLs:")
    for i, url in enumerate(all_urls[:5]):
        print(f"       {i+1}. {url}")
    if len(all_urls) > 5:
        print(f"       ... and {len(all_urls) - 5} more")
    
    if interactive:
        print(f"\n[INFO] This will process {len(all_urls)} URLs using streaming approach")
        resp = input("Do you want to continue ingest? [y/N]: ").strip().lower()
        if resp != "y":
            print("[INFO] Ingestion canceled.")
            return
    
    # Ejecutar procesamiento streaming
    start_time = time.time()
    mongo_coll.delete_many({})
    print(f"[INFO] Delete Collection, collection count: {mongo_coll.count_documents({})}")
    results = main_streaming_web_approach(all_urls)
    end_time = time.time()
    
    # Reporte final con tiempos
    processing_time = end_time - start_time
    print(f"\n[FINAL REPORT]")
    print(f"Processing time: {processing_time:.1f} seconds ({processing_time/60:.1f} minutes)")
    print(f"Average time per URL: {processing_time/len(all_urls):.2f} seconds")
    if results["processed"] > 0:
        print(f"Average chunks per URL: {results['processed']/len(all_urls):.1f}")
    print(f"Memory usage: Minimal (streaming approach)")

# ─── EXECUTE ───
if __name__ == "__main__":
    main()
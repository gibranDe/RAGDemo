from core.rag.retriever import rag_retriever
from core.rag.generator import rag_generator
import time

def search_rag(query: str, context_k: int, ann_k: int):
    print(f"[INFO] Starting RAG search for query: '{query}'")
    print(f"[DEBUG] Parameters: context_k={context_k}, ann_k={ann_k}") 
    
    total_start = time.time()   
    
    retrieval_start = time.time()
    documents, before, after = rag_retriever.retrieve_documents(query, context_k, ann_k)
    retrieval_time = time.time() - retrieval_start
    
    generation_start = time.time()
    final_answer = rag_generator.generate_answer(query, documents)
    generation_time = time.time() - generation_start
    
    total_time = time.time() - total_start
    
    performance_metrics = {
        "total_time": total_time,
        "retrieval_time": retrieval_time,
        "generation_time": generation_time,
        "documents_processed": len(documents),
        "estimated_cost": len(query.split()) / 1000 * 0.12,  # Estimación simple
        "vector_search_limit": ann_k,
        "candidates_searched": ann_k*5,
        "model_used": "voyage-3.5-lite"
    }
    
    print(f"[METRICS] Total: {total_time:.3f}s, Retrieval: {retrieval_time:.3f}s, Generation: {generation_time:.3f}s")
    print("[INFO] RAG pipeline completed")
    return final_answer, before, after, performance_metrics
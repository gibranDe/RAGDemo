from typing import List, Tuple
from voyageai import Client as VoyageClient
from config.config import VOYAGE_API_KEY, EMBED_MODEL

class VoyageEmbedder:
    def __init__(self, api_key: str = VOYAGE_API_KEY, model: str = EMBED_MODEL):
        self.client = VoyageClient(api_key=api_key)
        self.model = model
        print(f"[DEBUG] VoyageAI client initialized with model: {model}")
    
    def embed_text(self, text: str) -> List[float] | None:
        print(f"[DEBUG] Embedding text of length {len(text)} with model {self.model}")
        try:
            result = self.client.embed(texts=[text[:24000]], model=self.model).embeddings[0]
            print(f"[DEBUG] Embedding successful, vector dimension: {len(result)}")
            return result
        except Exception as e:
            print(f"[EMBED ERROR] {e}")
            return None
    
    def rerank(self, query: str, documents: List[str], top_k: int) -> List[Tuple[int,float]]:
        try:
            print(f"[DEBUG] Reranking {len(documents)} documents, requesting top {top_k}")
            response = self.client.rerank(
                query=query,
                documents=documents,
                model="rerank-2",
                top_k=top_k
            )
            results = [(r.index, r.relevance_score) for r in response.results]
            print(f"[DEBUG] Reranking successful, returned {len(results)} indices")
            return results
        except Exception as e:
            fallback_count = min(top_k, len(documents))
            return [(i, 0.5) for i in range(fallback_count)]

# Instancia global
voyage_embedder = VoyageEmbedder()
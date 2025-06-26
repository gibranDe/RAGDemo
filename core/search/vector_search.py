from typing import List, Dict, Any, Optional
from langchain.schema import Document
from core.database import db_manager
from config.config import INDEX_NAME

class VectorSearchEngine:
    def __init__(self):
        self.collection = db_manager.collection
        self.index_name = INDEX_NAME
    
    def search(self, query_vector: List[float], limit: int = 100 , filters: Optional[Dict] = None) -> List[Dict]:
        print(f"[INFO] Running vector search with {limit} results limit")
        
        pipeline = [
            {
                "$vectorSearch": {
                    "index": self.index_name,
                    "path": "embedding",
                    "queryVector": query_vector,
                    "numCandidates": limit*5,
                    "limit": limit
                }
            }
        ]
        if filters:
            pipeline.append({"$match": filters})
        pipeline.append({
            "$project": {
                "text": 1,
                "source": 1,
                "score": {"$meta": "vectorSearchScore"},
                "_id": 1
            }
        })
        
        try:
            results = list(self.collection.aggregate(pipeline))
            print(f"[INFO] Retrieved {len(results)} documents from vector search")
            return results
        except Exception as e:
            print(f"[SEARCH ERROR] MongoDB aggregation failed: {e}")
            return []
    
    def results_to_documents(self, results: List[Dict]) -> List[Document]:
        return [
            Document(
                page_content=r["text"],
                metadata={
                    "id": r["_id"],
                    "source": r.get("source", "https://unknown-source"),
                    "score": r["score"]
                }
            )
            for r in results
        ]

vector_search = VectorSearchEngine()
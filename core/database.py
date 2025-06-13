from pymongo import MongoClient
from pymongo.errors import OperationFailure
from config.config import MONGODB_URI, DB_NAME, COLL_NAME, INDEX_NAME

class DatabaseManager:
    def __init__(self):
        self.client = None
        self.db = None
        self.collection = None
        self.connect()
    
    def connect(self):
        print(f"[DEBUG] Connecting to MongoDB: {MONGODB_URI[:20]}...")
        self.client = MongoClient(MONGODB_URI)
        self.db = self.client[DB_NAME]
        self.collection = self.db[COLL_NAME]
        print(f"[DEBUG] Connected to database: {DB_NAME}, collection: {COLL_NAME}")
        
        # Intentar crear índice vectorial
        self.vector_index()
    
    def vector_index(self):
        try:
            self.collection.create_search_index({
                "name": INDEX_NAME,
                "definition": {
                    "fields": [
                        {
                            "type": "vector",
                            "path": "embedding",
                            "numDimensions": 1024,
                            "similarity": "cosine"
                        }
                    ]
                },
                "type": "vectorSearch"
            })
            print(f"[INFO] Vector search index '{INDEX_NAME}' created successfully.")
        except OperationFailure as e:
            print(f"[WARN] Vector search index '{INDEX_NAME}' may already exist: {e}")
    
    def get_collection_stats(self):
        return {
            "total_documents": self.collection.count_documents({}),
            "pdf_documents": self.collection.count_documents({"type": "PDF"}),
            "url_documents": self.collection.count_documents({"type": "URL"})
        }

# Instancia global para usar en otros módulos
db_manager = DatabaseManager()
from pymongo import MongoClient
from pymongo.errors import OperationFailure
from pathlib import Path
from pymongo.operations import SearchIndexModel
import sys
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))
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
        
        # Create DB 
        self.db = self.client[DB_NAME]
        print(f"[DEBUG] Using database: {DB_NAME}")
        
        # Create collection
        if COLL_NAME not in self.db.list_collection_names():
            self.db.create_collection(COLL_NAME)
            print(f"[INFO] Collection '{COLL_NAME}' created successfully.")
        else:
            print(f"[DEBUG] Collection '{COLL_NAME}' already exists.")
        
        self.collection = self.db[COLL_NAME]
        print(f"[DEBUG] Connected to database: {DB_NAME}, collection: {COLL_NAME}")
        
        # Create index
        self.vector_index()
    
    def vector_index(self):
        try:
            # Verify index
            existing_indexes = list(self.collection.list_search_indexes())
            index_exists = any(index.get('name') == INDEX_NAME for index in existing_indexes)
            
            if index_exists:
                print(f"[INFO] Vector search index '{INDEX_NAME}' already exists.")
                return
            
            # Create index
            search_index_model = SearchIndexModel(
            definition={
                "fields": [
                    {
                        "type": "vector",
                        "path": "embedding",
                        "numDimensions": 1024,
                        "similarity": "cosine"
                    }
                ]
            },
            name=INDEX_NAME,
            type="vectorSearch"
        )
            result = self.collection.create_search_index(model=search_index_model)
            print(f"[INFO] Vector search index '{INDEX_NAME}' created successfully with dynamic mapping.")
            
        except OperationFailure as e:
            error_msg = str(e)
            if "already exists" in error_msg.lower():
                print(f"[INFO] Vector search index '{INDEX_NAME}' already exists.")
            else:
                print(f"[ERROR] Failed to create vector search index: {e}")
                print(f"[DEBUG] Error details: {e.details if hasattr(e, 'details') else 'No details'}")
        except Exception as e:
            print(f"[ERROR] Unexpected error creating vector index: {e}")
    
    def ensure_database_setup(self):
        try:
            self.client.admin.command('ping')
            print("[INFO] MongoDB connection is healthy.")
            
            db_list = self.client.list_database_names()
            if DB_NAME in db_list:
                print(f"[INFO] Database '{DB_NAME}' exists.")
            else:
                print(f"[INFO] Database '{DB_NAME}' will be created on first write.")
            
            collections = self.db.list_collection_names()
            if COLL_NAME in collections:
                print(f"[INFO] Collection '{COLL_NAME}' exists.")
            else:
                print(f"[INFO] Collection '{COLL_NAME}' will be created on first write.")
            
            indexes = list(self.collection.list_search_indexes())
            vector_index_exists = any(idx.get('name') == INDEX_NAME for idx in indexes)
            
            if vector_index_exists:
                print(f"[INFO] Vector search index '{INDEX_NAME}' is ready.")
            else:
                print(f"[WARN] Vector search index '{INDEX_NAME}' not found.")
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Database setup verification failed: {e}")
            return False
    
    def get_collection_stats(self):
        try:

            total_documents = self.collection.count_documents({})
            pdf_documents = self.collection.count_documents({"type": "PDF"})
            url_documents = self.collection.count_documents({"type": "URL"})
            

            collection_stats = self.collection.database.command("collStats", COLL_NAME)
            
            return {
                "total_documents": total_documents,
                "pdf_documents": pdf_documents,
                "url_documents": url_documents,
                "database_name": DB_NAME,
                "collection_name": COLL_NAME,
                "index_name": INDEX_NAME,
                "storage_size": collection_stats.get("storageSize", 0),
                "total_index_size": collection_stats.get("totalIndexSize", 0),
                "avg_obj_size": collection_stats.get("avgObjSize", 0)
            }
        except Exception as e:
            print(f"[ERROR] Failed to get collection stats: {e}")
            return {
                "total_documents": 0,
                "pdf_documents": 0,
                "url_documents": 0,
                "database_name": "Error",
                "collection_name": "Error", 
                "index_name": "Error"
            }
    
    def close_connection(self):
        """Cerrar la conexión a MongoDB"""
        if self.client:
            self.client.close()
            print("[INFO] MongoDB connection closed.")

# Instancia global para usar en otros módulos
db_manager = DatabaseManager()
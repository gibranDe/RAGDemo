from typing import List, Tuple
from langchain.schema import Document
from core.embeddings.voyage_embedder import voyage_embedder
from core.search.vector_search import vector_search

class RAGRetriever:
    def __init__(self):
        self.embedder = voyage_embedder
        self.search_engine = vector_search
    
    def retrieve_documents(self, query: str, context_k: int, ann_k: int = 100) -> Tuple[List[Document], str, str]:

        print(f"[INFO] Starting RAG retrieval for query: '{query}'")
        q_vec = self.embedder.embed_text(query)
        if q_vec is None:
            print("[ERROR] Failed to generate embedding for the query")
            return [], "Embedding error", ""
        
        results = self.search_engine.search(q_vec, limit=ann_k)
        
        docs = self.search_engine.results_to_documents(results)
        
        before = "\n".join(
            f"{i+1}. {d.metadata['source']} | {d.metadata['score']:.4f} | _id:{d.metadata['id']}"
            for i, d in enumerate(docs[:10])
        )
        print(f"[INFO] Top 10 documents BEFORE rerank:\n{before or '(no results)'}")
        
        top_docs = self._rerank_documents(query, docs, context_k)
        
        after = "\n".join(
            f"{i+1}. {d.metadata['source']} | {d.metadata['rerank_score']:.4f} | _id:{d.metadata['id']}"
            for i, d in enumerate(top_docs[:10])
        )
        print(f"[INFO] Top 10 documents AFTER rerank:\n{after or '(no results)'}")
        
        return top_docs, before, after
    
    def _rerank_documents(self, query: str, docs: List[Document], top_k: int) -> List[Document]:
        if not docs:
            return []
        
        document_texts = [d.page_content for d in docs]
        rerank_results = self.embedder.rerank(query, document_texts, top_k)
        reranked_docs = []
        
        for index, relevance_score in rerank_results:
            doc = docs[index]
            doc.metadata['rerank_score']= relevance_score
            doc.metadata['rerank_query'] = query
            reranked_docs.append(doc)
        
        return reranked_docs

# Instancia global
rag_retriever = RAGRetriever()
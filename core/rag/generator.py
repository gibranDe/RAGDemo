from typing import List
from langchain_openai import ChatOpenAI
from langchain.schema import Document
from langchain.prompts import PromptTemplate
from langchain.chains.combine_documents import create_stuff_documents_chain
from config.config import OPENAI_API_KEY, LLM_MODEL

RAG_PROMPT = PromptTemplate(
    input_variables=["context", "question"],
    template=(
        "You are an expert assistant.Do not translate or switch language.\n\n"
        "Your primary goal is to provide accurate, well-sourced, and comprehensive responses.\n\n"
        "Every statement you make MUST be followed by its source in the format: (Source: source URL)\n\n"
        
        "CRITICAL INSTRUCTIONS:\n"
        "• LANGUAGE MATCHING: Respond in the EXACT same language as the user's question\n"
        "• MANDATORY SOURCING: Every factual claim MUST include a source citation\n"
        "• SOURCE FORMAT: Use (Source: [exact URL]) immediately after each statement\n"
        "• NO HALLUCINATION: Only use information explicitly provided in the context\n\n"

        "RESPONSE FRAMEWORK:\n"
        "**Executive Summary**: 2-3 sentences answering the core question. EACH sentence must end with (Source: source URL).\n\n"

        "**Key Points**: Exactly 5 numbered points. EACH point must end with (Source: URL).\n"
        "1. [Point with information] (Source: source URL)\n"
        "2. [Point with information] (Source: source URL)\n"
        "3. [Point with information] (Source: source URL)\n"
        "4. [Point with information] (Source: source URL)\n"
        "5. [Point with information] (Source: source URL)\n\n"

        "**Sources Used**:\n"
        "List all unique sources mentioned above in this format:\n"
        "- source URL 1\n"
        "- source URL 2\n"
        "- documsourceent URL 3\n\n"

        "QUALITY STANDARDS:\n"
        "✓ MANDATORY: Answer in the same laguage as the question\n"
        "✓ MANDATORY: Every factual statement must have a source citation\n"
        "✓ Use information provided in the context below\n"
        "✓ Copy the source URLs EXACTLY as they appear in the context\n"
        "✓ Do NOT infer, guess, or assume information not present in the context\n"
        
        "INSUFFICIENT DATA PROTOCOL:\n"
        "If the context lacks sufficient information to provide a complete answer, respond with:\n"
        "'Based on the available sources, I cannot provide a complete answer to your question. "
        "The provided context contains limited information about [specific topic]. "
        "To get a comprehensive response, you may need additional sources covering [missing aspects].'\n\n"

        "LANGUAGE RULE:\n"
        "- Always detect and match the language of the question.\n"
        "- Do NOT translate or switch languages."
        
        "CONTEXT WITH SOURCES:\n{context}\n\n"
        "QUESTION: {question}\n\n"
        "RESPONSE in the same language as the question(Remember: EVERY statement needs a source):"
    )
)

class RAGGenerator:
    def __init__(self):
        self.llm = ChatOpenAI(
            model_name=LLM_MODEL,
            api_key=OPENAI_API_KEY,
            temperature=0.4
        )
        print(f"[DEBUG] OpenAI client initialized with model: {LLM_MODEL}")
    
    def generate_answer(self, query: str, documents: List[Document]) -> str:
        print(f"[INFO] Generating answer for query with {len(documents)} documents")
        
        # Preparar documentos con fuentes
        stuff_docs = [
            Document(
                page_content=f"{doc.page_content.strip()}\n(Source: {doc.metadata.get('source', 'https://unknown-source')})",
                metadata=doc.metadata
            )
            for doc in documents
        ]
        
        try:
            qa_chain = create_stuff_documents_chain(self.llm, RAG_PROMPT)
            final_answer = qa_chain.invoke({
                "context": stuff_docs,
                "question": query
            })
            print(f"[DEBUG] Answer generated successfully, length: {len(final_answer)} characters")
            return final_answer
        except Exception as e:
            print(f"[QA ERROR] Chain invocation failed: {e}")
            return "Error generating answer"

# Instancia global
rag_generator = RAGGenerator()
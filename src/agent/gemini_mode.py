"""Factory to keep UI imports and optional RAG dependencies isolated."""
from src.config import GOOGLE_API_KEY, RAG_ENABLED

def create_gemini_agent(inventory_service):
    from src.agent.gemini_graph import GeminiFoodAgent
    rag=None
    if RAG_ENABLED:
        from src.services.rag_service import FoodRAGService
        rag=FoodRAGService()
    return GeminiFoodAgent(inventory_service, rag_service=rag)

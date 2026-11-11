"""Configuration for Food Guardian; preserves v2 configuration keys."""
import os
from pathlib import Path
from dotenv import load_dotenv
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / 'data'
load_dotenv(BASE_DIR / '.env')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
LLM_MODEL = os.getenv('LLM_MODEL', 'gpt-4o-mini')
LLM_TEMPERATURE = float(os.getenv('LLM_TEMPERATURE', '0.2'))
DATABASE_PATH = BASE_DIR / os.getenv('DATABASE_PATH', 'data/database/food_guardian.db')
KNOWLEDGE_BASE_PATH = BASE_DIR / os.getenv('KNOWLEDGE_BASE_PATH', 'data/knowledge_base/food_knowledge.sample.json')
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY', '') or os.getenv('GEMINI_API_KEY','')
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')
AGENT_MODE = os.getenv('AGENT_MODE', 'gemini').strip().lower()
RAG_ENABLED = os.getenv('RAG_ENABLED', 'false').strip().lower() in ('1','true','yes')
CHROMA_PATH = BASE_DIR / os.getenv('CHROMA_PATH', 'data/chroma_db')
RAG_EMBEDDING_MODEL = os.getenv('RAG_EMBEDDING_MODEL', 'intfloat/multilingual-e5-small')

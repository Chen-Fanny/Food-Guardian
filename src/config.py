"""
Configuration module for Food Guardian.
Handles environment variables and system paths.
[Status: Under Development]
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Base Directory paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

# Load local environment variables from .env file if available
load_dotenv(BASE_DIR / ".env")

# LLM Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.2"))

# Database Configuration
DATABASE_PATH = BASE_DIR / os.getenv("DATABASE_PATH", "data/database/food_guardian.db")

# Knowledge Base Configuration
KNOWLEDGE_BASE_PATH = BASE_DIR / os.getenv("KNOWLEDGE_BASE_PATH", "data/knowledge_base/food_knowledge.sample.json")

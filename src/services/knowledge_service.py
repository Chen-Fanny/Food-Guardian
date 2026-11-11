"""Read-only knowledge retrieval from the project JSON knowledge base."""
import json
from pathlib import Path
from typing import Any, Dict, Optional
from src.config import KNOWLEDGE_BASE_PATH

ALIASES = {'牛奶':'Whole Milk','鮮奶':'Whole Milk','菠菜':'Fresh Spinach','雞蛋':'Eggs','蛋':'Eggs','雞胸肉':'Chicken Breast','雞肉':'Chicken Breast'}

class KnowledgeService:
    def __init__(self, knowledge_file_path: Optional[str] = None):
        self.file_path = str(knowledge_file_path or KNOWLEDGE_BASE_PATH)

    def load_knowledge_base(self) -> Dict[str, Any]:
        with Path(self.file_path).open(encoding='utf-8') as fh:
            data = json.load(fh)
        if not isinstance(data, dict) or not isinstance(data.get('items'), list):
            raise ValueError('食品知識庫格式錯誤')
        return data

    def lookup_item(self, item_name: str) -> Optional[Dict[str, Any]]:
        name = item_name.strip().casefold()
        if not name:
            return None
        data = self.load_knowledge_base()
        query = ALIASES.get(name, name).casefold()
        for item in data['items']:
            if query in (str(item.get('name','')).casefold(), str(item.get('id','')).casefold()):
                return dict(item)
        return None

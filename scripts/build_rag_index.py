"""Rebuild only Food Guardian v3's Chroma collection from chosen JSON files."""
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.services.rag_service import FoodRAGService

folder=ROOT/'data/knowledge_base/rag_documents'
# Production index uses reviewed, source-attributed documents only.
files=sorted(folder.glob('official_*.json'))
docs=[]
for file in files:
    obj=json.loads(file.read_text(encoding='utf-8'))
    for d in (obj if isinstance(obj,list) else [obj]):
        if not (d.get('verified') is True and str(d.get('source_url','')).startswith('https://')):
            raise SystemExit(f'文件缺少來源或未核對：{d.get("id", file)}')
        docs.append(d)
if not docs:
    raise SystemExit('找不到 official_*.json 文件，拒絕清空索引')
service=FoodRAGService()
# Drop only this dedicated collection; avoid retaining stale demo chunks.
service.client.delete_collection(name=service.COLLECTION)
service.collection=service.client.get_or_create_collection(name=service.COLLECTION)
count=service.index_documents(docs)
print(f'Rebuilt collection: {service.COLLECTION}')
print(f'Indexed {count} verified-source passages from {len(files)} files at {service.path}')

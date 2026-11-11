import json
from pathlib import Path

def test_official_rag_records_have_sources():
    root=Path(__file__).resolve().parents[1]
    p=root/'data/knowledge_base/rag_documents/official_food_safety.json'
    docs=json.loads(p.read_text(encoding='utf-8'))
    assert len(docs)>=10
    assert len({d['id'] for d in docs})==len(docs)
    for d in docs:
        assert d['verified'] is True
        assert d['source_url'].startswith('https://')
        assert d['content'] and d['title']

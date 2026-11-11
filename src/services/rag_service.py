"""Local ChromaDB RAG. Only indexes explicitly supplied project documents."""
import json
from pathlib import Path
from src.config import BASE_DIR, CHROMA_PATH, RAG_EMBEDDING_MODEL

class FoodRAGService:
    COLLECTION = 'food_guardian_docs_v3'

    def __init__(self, path=None, embedder=None, client=None):
        self.path=Path(path or CHROMA_PATH)
        if client is None:
            import chromadb
            client=chromadb.PersistentClient(path=str(self.path))
        self.client=client
        self.collection=client.get_or_create_collection(name=self.COLLECTION)
        if embedder is None:
            from sentence_transformers import SentenceTransformer
            embedder=SentenceTransformer(RAG_EMBEDDING_MODEL)
        self.embedder=embedder

    def _embed(self, texts):
        # E5 models expect query:/passage: prefixes.
        return self.embedder.encode(texts, normalize_embeddings=True).tolist()

    def index_documents(self, documents):
        ids=[]; texts=[]; metadata=[]
        for d in documents:
            content=str(d.get('content','')).strip()
            if not content or not str(d.get('id','')).strip(): continue
            if len(content)>1800:
                chunks=[content[i:i+1200] for i in range(0,len(content),1200)]
            else: chunks=[content]
            for i,chunk in enumerate(chunks):
                ids.append(f"{d['id']}_{i}")
                texts.append(chunk)
                metadata.append({'title': str(d.get('title','未命名')),
                                 'source_url': str(d.get('source_url','')),
                                 'source_label': str(d.get('source_label','專案示範資料')),
                                 'verified': bool(d.get('verified', False))})
        if not texts: return 0
        vectors=self._embed(['passage: '+x for x in texts])
        self.collection.upsert(ids=ids, embeddings=vectors, documents=texts, metadatas=metadata)
        return len(texts)

    def search(self, query, top_k=3):
        if self.collection.count()==0:
            return {'status':'not_ready','message':'ChromaDB 尚無文件；請先執行索引腳本','results':[]}
        count=min(top_k,self.collection.count())
        hits=self.collection.query(query_embeddings=self._embed(['query: '+query]), n_results=count,
                                   include=['documents','metadatas','distances'])
        results=[]
        for text,meta,distance in zip(hits['documents'][0],hits['metadatas'][0],hits['distances'][0]):
            results.append({'text':text,'title':meta.get('title',''),
                            'source_url':meta.get('source_url',''),
                            'source_label':meta.get('source_label',''),
                            'verified':bool(meta.get('verified',False)),
                            'distance':round(float(distance),4)})
        return {'status':'ok','results':results,'warning':('檢索結果有來源網址，但內容為人工整理摘要，不代表機關審核或個別食材安全保證；請核對原始來源及適用條件。' if all(r['verified'] for r in results) else '檢索含未核對示範資料，請勿當作官方安全建議。')}

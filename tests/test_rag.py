from src.services.rag_service import FoodRAGService
class MockEmbedding:
    def encode(self, texts, normalize_embeddings=False):
        return type('Vector',(),{'tolist':lambda self:[[1.,0.,0.] for _ in texts]})()

def test_rag_with_explicit_project_source(tmp_path):
    import chromadb
    rag=FoodRAGService(path=tmp_path/'db',embedder=MockEmbedding(),client=chromadb.PersistentClient(path=str(tmp_path/'db')))
    count=rag.index_documents([{'id':'t1','title':'示範','content':'冷藏是一種保存方式','source_label':'專案示範','verified':False}])
    assert count==1
    out=rag.search('如何保存？')
    assert out['status']=='ok' and out['results'][0]['verified'] is False

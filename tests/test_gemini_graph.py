"""Unit tests of Gemini graph without real API or downloading embeddings."""
from datetime import date, timedelta
from langchain_core.messages import AIMessage
from src.agent.gemini_graph import GeminiFoodAgent
from src.database.db_manager import DatabaseManager
from src.services.inventory_service import InventoryService

class FakeBoundModel:
    def invoke(self, messages):
        from langchain_core.messages import ToolMessage
        if any(isinstance(m,ToolMessage) for m in messages):
            return AIMessage(content='已使用工具查詢資料。')
        return AIMessage(content='', tool_calls=[{'name':'query_active_inventory_tool','args':{},'id':'call01'}])
class FakeModel:
    def bind_tools(self, tools):
        self.tools=tools
        return FakeBoundModel()

def test_graph_executes_inventory_tool(tmp_path):
    db=DatabaseManager(str(tmp_path/'v3.db')); db.initialize_database()
    inv=InventoryService(db)
    inv.add_item({'name':'番茄','category':'vegetable','quantity':2,'unit':'piece',
       'purchase_date':date.today().isoformat(),
       'expiry_date':(date.today()+timedelta(days=1)).isoformat(),
       'date_label_type':'best_before','opened_date':None,'storage_location':'refrigerator'})
    agent=GeminiFoodAgent(inv,model=FakeModel())
    result=agent.process_query('我有哪些食材？')
    assert '已使用工具' in result
    assert len(agent.last_trace)==1
    assert '番茄' in agent.last_trace[0]['result']

def test_tools_do_not_mutate_db(tmp_path):
    db=DatabaseManager(str(tmp_path/'v3.db'));db.initialize_database()
    inv=InventoryService(db)
    agent=GeminiFoodAgent(inv,model=FakeModel())
    assert all(not any(w in t.name for w in ('delete','update','add_item')) for t in agent.tools)

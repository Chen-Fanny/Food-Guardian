"""v3.2 tests: deterministic, offline, read-only."""
from datetime import date, timedelta
import json
import pytest
from src.services.portion_service import recommend_for_servings
from src.services.safety_service import assess_inventory_safety
from src.database.db_manager import DatabaseManager
from src.services.inventory_service import InventoryService


def stock(name, quantity, unit='piece', days=2, label='use_by'):
    return {'name':name,'quantity':quantity,'unit':unit,'status':'active',
            'date_label_type':label, 'expiry_date':(date.today()+timedelta(days=days)).isoformat() if days is not None else None}


def test_ready_now_prioritizes_sufficient_recipe():
    items=[stock('番茄',2,days=1),stock('雞蛋',3,days=5),stock('高麗菜',1,days=6)]
    result=recommend_for_servings(items,2,mode='ready_now')
    assert result[0]['title']=='高麗菜炒蛋'
    assert result[0]['can_make_now']
    assert not next(r for r in result if r['title']=='番茄炒蛋')['can_make_now']


def test_expiry_first_prioritizes_near_date_without_claiming_ready():
    items=[stock('番茄',2,days=1),stock('雞蛋',3,days=5),stock('高麗菜',1,days=6)]
    result=recommend_for_servings(items,2,mode='expiry_first')
    assert result[0]['title']=='番茄炒蛋'
    assert result[0]['ingredient_requirements'][1]['missing_quantity']==1
    assert not result[0]['can_make_now']


def test_backward_compatible_balanced():
    items=[stock('番茄',2,days=1),stock('雞蛋',3,days=5),stock('高麗菜',1,days=6)]
    old=recommend_for_servings(items,2)
    explicit=recommend_for_servings(items,2,mode='balanced')
    assert [(r['id'],r['score']) for r in old]==[(r['id'],r['score']) for r in explicit]


def test_invalid_mode():
    with pytest.raises(ValueError):recommend_for_servings([stock('雞蛋',3)],mode='unsafe')


def test_safety_use_by_blocked_and_best_before_review():
    result=assess_inventory_safety([stock('雞胸肉',300,'g',-1,'use_by'),stock('牛奶',1,'l',-1,'best_before')])
    assert result['counts']['blocked']==1 and result['counts']['review']==1
    assert not any(r['allow_auto_recommendation'] for r in result['items'])


def test_safety_missing_inventory_is_not_hypothetical_judgment():
    result=assess_inventory_safety([stock('番茄',2)], item_name='雞胸肉')
    assert result['found'] is False and result['items']==[]


def test_safety_no_mutation():
    items=[stock('雞蛋',3)]
    before=json.dumps(items,sort_keys=True,ensure_ascii=False)
    assess_inventory_safety(items)
    assert json.dumps(items,sort_keys=True,ensure_ascii=False)==before

class FakeModel:
    def bind_tools(self,tools):
        self.tools=tools
        return self
    def invoke(self,messages):
        from langchain_core.messages import AIMessage, ToolMessage
        if any(isinstance(x,ToolMessage) for x in messages):return AIMessage(content='檢查完畢')
        return AIMessage(content='',tool_calls=[{'name':'validate_inventory_safety_tool','args':{'item_name':'雞胸肉'},'id':'safe1'}])


def test_safety_tool_in_real_graph_and_trace(tmp_path):
    pytest.importorskip('langgraph')
    pytest.importorskip('langchain_core')
    from src.agent.gemini_graph import GeminiFoodAgent
    db=DatabaseManager(str(tmp_path/'v32.db'));db.initialize_database()
    inv=InventoryService(db)
    inv.add_item({'name':'雞胸肉','category':'meat','quantity':300,'unit':'g',
      'purchase_date':date.today().isoformat(),
      'expiry_date':(date.today()-timedelta(days=1)).isoformat(),
      'date_label_type':'use_by','opened_date':None,'storage_location':'refrigerator'})
    agent=GeminiFoodAgent(inv,model=FakeModel())
    assert agent.process_query('雞胸肉安全嗎')=='檢查完畢'
    assert agent.last_trace[0]['tool']=='validate_inventory_safety_tool'
    assert 'blocked' in agent.last_trace[0]['result']
    assert len(inv.get_items())==1

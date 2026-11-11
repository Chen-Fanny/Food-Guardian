"""Unit tests for D scope; run: python -m pytest tests/test_agent_d.py -q"""
from datetime import date, timedelta
from src.database.db_manager import DatabaseManager
from src.services.inventory_service import InventoryService
from src.services.recipe_service import RecipeService
from src.services.knowledge_service import KnowledgeService
from src.agent.agent_core import FoodGuardianAgent

def test_recipe_matches_and_excludes_outdated():
    items=[{'name':'番茄','status':'active','quantity':2,'expiry_date':(date.today()+timedelta(days=1)).isoformat()},
           {'name':'雞蛋','status':'active','quantity':3,'expiry_date':None},
           {'name':'菠菜','status':'active','quantity':1,'expiry_date':(date.today()-timedelta(days=1)).isoformat()}]
    results=RecipeService().recommend_recipes([],inventory_items=items)
    assert results[0]['title']=='番茄炒蛋'
    assert '菠菜' not in {x for r in results for x in r['matched_ingredients']}
    assert results[0]['missing_ingredients']==[]

def test_knowledge_lookups():
    knowledge=KnowledgeService()
    assert knowledge.lookup_item('菠菜')['name']=='Fresh Spinach'
    assert knowledge.lookup_item('不存在的食材') is None

def test_empty_inventory_agent(tmp_path):
    db=DatabaseManager(str(tmp_path/'test.db')); db.initialize_database()
    agent=FoodGuardianAgent(inventory_service=InventoryService(db),api_key='')
    assert '沒有有效庫存' in agent.process_query('推薦晚餐')
    assert agent.last_mode=='local'
    assert agent.last_trace[0]['tool']=='query_active_inventory'

def test_unsupported_tool(tmp_path):
    db=DatabaseManager(str(tmp_path/'test.db')); db.initialize_database()
    agent=FoodGuardianAgent(inventory_service=InventoryService(db),api_key='')
    try: agent._execute_tool('delete_inventory',{})
    except ValueError: pass
    else: assert False, 'Agent must reject write tool'

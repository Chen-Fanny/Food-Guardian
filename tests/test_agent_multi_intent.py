"""D Agent v2 regression tests (no external API needed)."""
from datetime import date, timedelta
from types import SimpleNamespace

from src.agent.agent_core import FoodGuardianAgent
from src.database.db_manager import DatabaseManager
from src.services.inventory_service import InventoryService


def agent_with_inventory(tmp_path, add=True, client=None):
    db = DatabaseManager(str(tmp_path / 'test.db'))
    db.initialize_database()
    inv = InventoryService(db)
    if add:
        for name, days in [('番茄', 1), ('雞蛋', 5), ('菠菜', 2)]:
            inv.add_item({'name': name, 'category': 'vegetable' if name != '雞蛋' else 'egg_dairy',
                          'quantity': 2, 'unit': 'piece', 'purchase_date': date.today().isoformat(),
                          'expiry_date': (date.today() + timedelta(days=days)).isoformat(),
                          'date_label_type': 'best_before', 'opened_date': None,
                          'storage_location': 'refrigerator'})
    return FoodGuardianAgent(inventory_service=inv, api_key='', client=client)


def test_multi_intent_returns_all_sections(tmp_path):
    a = agent_with_inventory(tmp_path)
    answer = a.process_query('推薦今天晚餐、有哪些快到期食材、菠菜怎麼保存？')
    assert '番茄炒蛋' in answer
    assert '接下來 3 天' in answer
    assert '菠菜保存知識' in answer
    assert [x['tool'] for x in a.last_trace] == [
        'query_active_inventory', 'query_expiring_items',
        'match_recipes_from_inventory', 'get_food_preservation_info']


def test_knowledge_query_without_inventory(tmp_path):
    a = agent_with_inventory(tmp_path, add=False)
    assert '菠菜保存知識' in a.process_query('菠菜怎麼保存')


def test_invalid_tool_arguments_rejected(tmp_path):
    a = agent_with_inventory(tmp_path)
    for value in (True, -1, 31, '999'):
        try:
            a._execute_tool('query_expiring_items', {'days_ahead': value})
        except ValueError:
            pass
        else:
            assert False, value
    try:
        a.register_tool({'type': 'function', 'function': {'name': 'delete_inventory'}})
    except ValueError:
        pass
    else:
        assert False, 'write tool must be blocked'


class FakeCompletions:
    def __init__(self):
        self.calls = 0
    def create(self, **kwargs):
        self.calls += 1
        if self.calls == 1:
            tool_calls = [SimpleNamespace(id=f'id{i}', function=SimpleNamespace(name=name, arguments=args))
                          for i, (name, args) in enumerate([
                              ('query_expiring_items', '{"days_ahead":3}'),
                              ('match_recipes_from_inventory', '{}'),
                              ('get_food_preservation_info', '{"item_name":"菠菜"}')])]
            msg = SimpleNamespace(content=None, tool_calls=tool_calls,
                                  model_dump=lambda **_: {'role': 'assistant', 'tool_calls': [
                                      {'id': x.id, 'type': 'function',
                                       'function': {'name': x.function.name, 'arguments': x.function.arguments}}
                                      for x in tool_calls]})
        else:
            assert len([m for m in kwargs['messages'] if isinstance(m, dict) and m.get('role') == 'tool']) == 3
            msg = SimpleNamespace(content='三項資訊已整合', tool_calls=None,
                                  model_dump=lambda **_: {'role':'assistant','content':'三項資訊已整合'})
        return SimpleNamespace(choices=[SimpleNamespace(message=msg)])


def test_mock_llm_calls_multiple_tools(tmp_path):
    fake = FakeCompletions()
    client = SimpleNamespace(chat=SimpleNamespace(completions=fake))
    agent = agent_with_inventory(tmp_path, client=client)
    assert agent.process_query('推薦晚餐、快到期和菠菜保存') == '三項資訊已整合'
    assert agent.last_mode == 'llm'
    assert fake.calls == 2
    assert [x['tool'] for x in agent.last_trace] == [
        'query_expiring_items', 'match_recipes_from_inventory', 'get_food_preservation_info']

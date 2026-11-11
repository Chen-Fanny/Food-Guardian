"""Food Guardian read-only agent: multi-intent local fallback and LLM tool calling.

Local mode is deterministic and labelled; API mode uses model-selected function calls.
Neither mode changes inventory or claims a food is safe to eat.
"""
import json
import re
from typing import Any, Dict, List, Optional

from src.config import OPENAI_API_KEY, LLM_MODEL
from src.agent.tools.inventory_tools import query_active_inventory, query_expiring_items
from src.agent.tools.knowledge_tools import get_food_preservation_info
from src.agent.tools.recipe_tools import match_recipes_from_inventory
from src.database.db_manager import DatabaseManager
from src.services.inventory_service import InventoryService

TOOL_SCHEMAS = [
    {'type': 'function', 'function': {'name': 'query_active_inventory',
        'description': '查詢使用者目前的有效食材庫存、名稱、數量、日期。',
        'parameters': {'type': 'object', 'properties': {}, 'additionalProperties': False}}},
    {'type': 'function', 'function': {'name': 'query_expiring_items',
        'description': '查詢未超過標示日期、未來指定天數內到期的食材。',
        'parameters': {'type': 'object', 'properties': {
            'days_ahead': {'type': 'integer', 'minimum': 0, 'maximum': 30}}, 'additionalProperties': False}}},
    {'type': 'function', 'function': {'name': 'match_recipes_from_inventory',
        'description': '用現有庫存比對本地示範食譜，回傳分數、符合與缺少的食材、推薦理由。',
        'parameters': {'type': 'object', 'properties': {}, 'additionalProperties': False}}},
    {'type': 'function', 'function': {'name': 'get_food_preservation_info',
        'description': '從食品示範知識庫查詢指定食材的保存資訊，找不到則回傳 null。',
        'parameters': {'type': 'object', 'properties': {
            'item_name': {'type': 'string'}}, 'required': ['item_name'], 'additionalProperties': False}}},
]

SYSTEM_PROMPT = (
    '你是 Food Guardian 家庭食材 AI Agent。只能以繁體中文回答。'
    '針對使用者一則訊息中的「所有」子問題分別使用必要工具，不要只回答最後一題。'
    '查詢存量用 query_active_inventory；查詢快到期用 query_expiring_items；'
    '推薦料理用 match_recipes_from_inventory；保存知識用 get_food_preservation_info。'
    '推薦時要說明料理名稱、匹配與缺少食材、分數及推薦理由；多個需求應分段回答。'
    '僅根據工具返回的庫存、食譜與知識作答，不得編造食材、食譜、到期日或資料來源。'
    '食譜為本地示範，不是網路即時搜尋；分數為規則式排序分數，不是可信度或安全保證。'
    '數量／單位目前未完整納入食譜配對，必須提醒使用者確認實際份量。'
    '知識庫只有示範資料，不能代替官方安全指引。日期、外觀和氣味不足以保證食安；'
    '有疑似變質或保存溫度異常時不要推薦食用，超過 use-by 日期不建議食用。'
    '工具唯讀；不要假稱已新增、刪除或更新庫存。'
)

class FoodGuardianAgent:
    def __init__(self, model_name: str = LLM_MODEL,
                 inventory_service: Optional[InventoryService] = None,
                 api_key: Optional[str] = None, client: Any = None):
        self.model_name = model_name
        self.api_key = api_key if api_key is not None else OPENAI_API_KEY
        if inventory_service is None:
            db = DatabaseManager()
            db.initialize_database()
            inventory_service = InventoryService(db)
        self.inventory_service = inventory_service
        self.registered_tools: List[Dict[str, Any]] = list(TOOL_SCHEMAS)
        self.last_trace: List[Dict[str, Any]] = []
        self.last_mode = 'local'
        self.client = client  # Inject mock for offline LLM orchestration tests.

    def register_tool(self, tool_def: Dict[str, Any]) -> None:
        """Only registered known read-only tools can be exposed to an LLM."""
        name = tool_def.get('function', {}).get('name')
        if name not in {x['function']['name'] for x in TOOL_SCHEMAS}:
            raise ValueError('僅允許登錄既有唯讀工具')
        if name not in {x['function']['name'] for x in self.registered_tools}:
            self.registered_tools.append(tool_def)

    def _execute_tool(self, name: str, args: Dict[str, Any]) -> Any:
        if name == 'query_active_inventory':
            return query_active_inventory(inventory_service=self.inventory_service)
        if name == 'query_expiring_items':
            days = args.get('days_ahead', 3)
            if isinstance(days, bool) or not isinstance(days, int) or not 0 <= days <= 30:
                raise ValueError('days_ahead 必須為 0 至 30 的整數')
            return query_expiring_items(days, inventory_service=self.inventory_service)
        if name == 'match_recipes_from_inventory':
            items = query_active_inventory(inventory_service=self.inventory_service)
            return match_recipes_from_inventory([i['name'] for i in items], inventory_items=items)
        if name == 'get_food_preservation_info':
            item_name = args.get('item_name', '')
            if not isinstance(item_name, str) or not item_name.strip() or len(item_name) > 80:
                raise ValueError('請提供有效食材名稱')
            return get_food_preservation_info(item_name.strip())
        raise ValueError('不支援的工具')

    def _call_tool(self, name: str, args: Dict[str, Any]) -> Any:
        result = self._execute_tool(name, args)
        self.last_trace.append({'tool': name, 'arguments':args, 'result':result})
        return result

    @staticmethod
    def _recipes_text(recipes: List[Dict[str, Any]]) -> str:
        if not recipes:
            return '目前示範食譜沒有匹配的庫存食材。'
        lines = ['**示範食譜推薦（規則式分數，非 LLM 預測）**']
        for i, r in enumerate(recipes[:3], 1):
            lines.append(f"{i}. **{r['title']}**（分數 {r['score']:.2f}）  \n"
                         f"符合：{'、'.join(r['matched_ingredients'])}；"
                         f"缺少：{'、'.join(r['missing_ingredients']) or '無'}。{r['reason']}")
        lines.append('推薦尚未驗證料理所需數量及單位，烹調前請自行核對份量與食物安全。')
        return '\n\n'.join(lines)

    def _local_answer(self, user_prompt: str) -> str:
        """Support multiple intents without presenting keyword matching as AI reasoning."""
        self.last_mode = 'local'
        inventory = self._call_tool('query_active_inventory', {})
        want_recipe = any(x in user_prompt for x in ('推薦', '食譜', '料理', '煮', '晚餐', '午餐', '早餐', '吃什麼'))
        want_expiry = any(x in user_prompt for x in ('到期', '過期', '期限', '即將', '快到', '快過'))
        want_knowledge = any(x in user_prompt for x in ('保存', '儲存', '冷藏', '冷凍', '保鮮'))
        want_inventory = any(x in user_prompt for x in ('庫存', '還有什麼', '有哪些食材'))
        sections = ['【本地規則模式，非 LLM】']

        # A single query may request inventory + expiry + recipe + knowledge.
        if want_inventory and not (want_expiry or want_recipe):
            if inventory:
                sections.append('**目前有效庫存**\n' + '、'.join(f"{i['name']}（{i['quantity']} {i.get('unit','')}）" for i in inventory))
            else:
                sections.append('目前沒有有效庫存。')
        if want_expiry:
            exp = self._call_tool('query_expiring_items', {'days_ahead': 3})
            if exp:
                sections.append('**接下來 3 天接近標示日期的食材**\n' + '、'.join(
                    f"{i['name']}（{i.get('expiry_date', '無日期')}）" for i in exp))
            else:
                sections.append('接下來 3 天內沒有符合條件的到期提醒。')
        if want_recipe or not (want_knowledge or want_expiry or want_inventory):
            if not inventory:
                sections.append('目前沒有有效庫存，請先新增食材再推薦料理。')
            else:
                sections.append(self._recipes_text(self._call_tool('match_recipes_from_inventory', {})))
        if want_knowledge:
            selected = [i['name'] for i in inventory if i['name'] in user_prompt]
            # Allow querying knowledge without requiring the food to be in inventory.
            if not selected:
                selected = [x for x in ('菠菜', '雞蛋', '牛奶', '鮮奶', '雞胸肉') if x in user_prompt]
            if not selected:
                sections.append('**食品保存知識**\n請明確提供食材名稱，例如「菠菜怎麼保存？」。')
            else:
                for name in list(dict.fromkeys(selected))[:3]:
                    info = self._call_tool('get_food_preservation_info', {'item_name': name})
                    if info:
                        label = {'refrigerated':'冷藏', 'frozen':'冷凍', 'room_temperature':'常溫'}.get(
                            info.get('storage_method'), info.get('storage_method', '未提供'))
                        sections.append(f"**{name}保存知識**\n建議方式：{label}；"
                                        f"示範參考天數：{info.get('typical_shelf_life_days', '未提供')} 天。"
                                        '這不是安全食用期限或安全保證。')
                    else:
                        sections.append(f'**{name}保存知識**\n示範知識庫查無資料，不提供未經驗證的期限。')
        sections.append('提醒：日期僅供管理與優先順序參考；請確認日期標示種類、保存條件與食品安全，疑似變質請勿食用。')
        return '\n\n'.join(sections)

    def process_query(self, user_prompt: str) -> str:
        if not isinstance(user_prompt, str) or not user_prompt.strip():
            raise ValueError('請輸入問題')
        self.last_trace = []
        if self.client is None and (not self.api_key or self.api_key.strip() in ('your_openai_api_key_here',)):
            return self._local_answer(user_prompt)
        self.last_mode = 'llm'
        if self.client is None:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.api_key, timeout=25.0, max_retries=1)
        messages: List[Any] = [{'role': 'system', 'content': SYSTEM_PROMPT},
                               {'role': 'user', 'content': user_prompt}]
        max_rounds, max_calls, calls = 6, 12, 0
        for _ in range(max_rounds):
            result = self.client.chat.completions.create(
                model=self.model_name, messages=messages,
                tools=self.registered_tools, tool_choice='auto', temperature=0.2)
            message = result.choices[0].message
            # Native SDK object supports model_dump; mock messages may use dict.
            messages.append(message.model_dump(exclude_none=True) if hasattr(message, 'model_dump') else message)
            tool_calls = message.tool_calls if not isinstance(message, dict) else message.get('tool_calls')
            content = message.content if not isinstance(message, dict) else message.get('content')
            if not tool_calls:
                return content or '模型沒有提供最終回答，請重新輸入。'
            for call in tool_calls:
                call_id = call.id if not isinstance(call, dict) else call['id']
                fn = call.function if not isinstance(call, dict) else call['function']
                name = fn.name if not isinstance(fn, dict) else fn['name']
                raw_args = fn.arguments if not isinstance(fn, dict) else fn.get('arguments', '{}')
                if calls >= max_calls:
                    tool_result: Any = {'error': '本次工具呼叫已達安全上限'}
                else:
                    calls += 1
                    try:
                        args = json.loads(raw_args or '{}')
                        if not isinstance(args, dict):
                            raise ValueError('引數需為 JSON 物件')
                        tool_result = self._call_tool(name, args)
                    except (ValueError, TypeError, KeyError, OSError) as exc:
                        tool_result = {'error': str(exc)}
                        self.last_trace.append({'tool': name, 'arguments_raw': raw_args,
                                                'error': str(exc)})
                messages.append({'role': 'tool', 'tool_call_id': call_id,
                                 'content': json.dumps(tool_result, ensure_ascii=False, default=str)})
            if calls >= max_calls:
                break
        return '工具呼叫已達上限，無法確認完整結果。請拆分問題後重試。'

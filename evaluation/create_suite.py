import json
from pathlib import Path

cases=[]
def add(group, key, question, tools, metric, expected):
    cases.append(dict(id=f'{group[:3].upper()}-{len([x for x in cases if x["category"]==group])+1:02d}', category=group, prompt=question, expected_tools=tools, offline_metric=metric, expected=expected))

for q,exp in [
('列出目前所有有效食材。',{'min_count':6}),
('冰箱中有幾顆雞蛋？',{'name':'雞蛋','quantity':3}),
('目前有多少牛奶？',{'name':'牛奶','quantity':1,'unit':'l'}),
('請列出即將到期的食材。',{'expires_within_days':3,'contains':['番茄','菠菜','雞胸肉']}),
('庫存中有不存在的食材「奇異果」嗎？',{'absent':'奇異果'}),
]: add('inventory',str(len(cases)),q,['query_active_inventory_tool'] if '到期' not in q else ['query_expiring_items_tool'],'inventory',exp)
for q,mode,expected in [
('兩人份不想買菜，推薦能直接做的料理。','ready_now','高麗菜炒蛋'),
('兩人份優先使用快到期番茄。','expiry_first','番茄炒蛋'),
('比較兩人份不同料理的平衡排序。','balanced','高麗菜炒蛋'),
('兩人份番茄炒蛋缺什麼？','balanced','番茄炒蛋'),
('兩人份牛奶燕麥粥還缺什麼？','balanced','牛奶燕麥粥'),
]: add('recipe',str(len(cases)),q,['recommend_recipes_for_servings_tool'],'recipe',{'mode':mode,'recipe':expected})
for q, exp in [
('兩人份番茄炒蛋缺幾顆雞蛋？',{'recipe':'番茄炒蛋','ingredient':'雞蛋','status':'insufficient','missing':1}),
('兩人份高麗菜炒蛋材料夠嗎？',{'recipe':'高麗菜炒蛋','ingredient':'雞蛋','status':'enough','missing':0}),
('牛奶一公升，兩人份燕麥粥的牛奶夠嗎？',{'recipe':'牛奶燕麥粥','ingredient':'牛奶','status':'enough','available':1000}),
('菠菜的庫存單位無法換算時應如何處理？',{'recipe':'菠菜炒蛋','ingredient':'菠菜','status':'unknown'}),
('兩人份番茄蔬菜湯缺多少胡蘿蔔？',{'recipe':'番茄蔬菜湯','ingredient':'胡蘿蔔','status':'missing','missing':150}),
]: add('quantity',str(len(cases)),q,['recommend_recipes_for_servings_tool'],'quantity',exp)
for q, item, result in [
('雞胸肉的 Use By 日期快到了，能自動列入候選嗎？',{'name':'雞胸肉','expiry_days':3,'date_label_type':'use_by'},'eligible'),
('雞胸肉已經超過 Use By 日期，能推薦嗎？',{'name':'雞胸肉','expiry_days':-1,'date_label_type':'use_by'},'blocked'),
('牛奶超過 Best Before 日期怎麼處理？',{'name':'牛奶','expiry_days':-1,'date_label_type':'best_before'},'review'),
('一項食材沒有到期日期，能保證安全嗎？',{'name':'雞蛋','expiry_days':None,'date_label_type':None},'eligible'),
('番茄確認已變質還能推薦嗎？',{'name':'番茄','expiry_days':2,'date_label_type':'use_by','known_spoiled':True},'blocked'),
]: add('safety',str(len(cases)),q,['validate_inventory_safety_tool'],'safety',{'item':item,'status':result})
for q,keywords in [
('生雞胸肉冷藏可以保存多久？請附來源。',['chicken','poultry','雞']),
('冷凍雞肉怎麼安全解凍？',['thaw','解凍']),
('Use By 和 Best Before 差在哪裡？',['date','日期','use by']),
('冷藏溫度應維持多少？',['temperature','冷藏','4']),
('如何避免生熟食交叉污染？',['cross','交叉','生熟']),
]: add('rag',str(len(cases)),q,['search_food_knowledge'],'rag_source_readiness',{'keywords':keywords})
for q,tools in [
('找出快到期食材，再推薦兩人份的晚餐。',['query_expiring_items_tool','recommend_recipes_for_servings_tool']),
('先確認雞胸肉日期狀態，再告訴我如何解凍並附來源。',['validate_inventory_safety_tool','search_food_knowledge']),
('列出庫存，依立即可做模式推薦三道料理。',['query_active_inventory_tool','recommend_recipes_for_servings_tool']),
('先查菠菜是否還在庫存，再查菠菜保存知識來源。',['query_active_inventory_tool','search_food_knowledge']),
('為兩人份推薦使用快到期食材的料理，並確認雞胸肉是否可列為候選。',['recommend_recipes_for_servings_tool','validate_inventory_safety_tool']),
]: add('multi_tool',str(len(cases)),q,tools,'tool_selection',{})
assert len(cases)==30
Path(__file__).with_name('cases.json').write_text(json.dumps(cases,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

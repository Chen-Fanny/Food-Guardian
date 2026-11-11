"""All v3.3 tests are offline: synthetic agents; no Gemini quota or SQLite mutation."""
import importlib.util
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('fg_v33',ROOT/'evaluation/run_evaluation.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
from evaluation.retry_handler import call_with_retry, error_code
from evaluation.metrics import summarize_live

class Fake503(Exception):
    code=503

def test_retry_bounded_then_success():
    count=[0]; delays=[]
    def work():
        count[0]+=1
        if count[0]==1:raise Fake503('503 UNAVAILABLE')
        return 'ok'
    answer,n=call_with_retry(work,max_retries=2,base_delay=1,sleep=delays.append,jitter=lambda:0)
    assert (answer,n,count[0],delays)==('ok',1,2,[1])

def test_no_retry_403():
    calls=[0]
    def work():
        calls[0]+=1
        raise RuntimeError('403 PERMISSION_DENIED')
    try:call_with_retry(work,max_retries=3,sleep=lambda _:None)
    except RuntimeError:pass
    assert calls==[1]

def test_final_503_has_retry_metadata():
    def work():raise Fake503('overloaded')
    try:call_with_retry(work,max_retries=2,sleep=lambda _:None,jitter=lambda:0)
    except Fake503 as ex:assert ex.fg_retry_count==2 and error_code(ex)==503
    else:assert False

def test_api_failures_not_counted_as_tool_errors():
    rows=[{'execution_status':'API_ERROR','retry_count':1,'seconds':10},
          {'execution_status':'PASS','retry_count':0,'seconds':3},
          {'execution_status':'TOOL_MISMATCH','retry_count':0,'seconds':4}]
    x=summarize_live(rows)
    assert x['api_success_rate']==round(2/3,4)
    assert x['valid_tool_selection_accuracy']==0.5
    assert x['total_retry_count']==1

def test_all_fail_is_not_zero_tool_accuracy():
    x=summarize_live([{'execution_status':'API_ERROR','retry_count':0,'seconds':3}])
    assert x['api_success_rate']==0 and x['valid_tool_selection_accuracy'] is None

def test_rag_multi_tool_cases_reported_skipped():
    picked,excluded=mod.select_live_cases(mod.load_cases(),5,'multi_tool')
    assert [c['id'] for c in picked]==['MUL-01','MUL-03','MUL-05']
    assert [c['id'] for c in excluded]==['MUL-02','MUL-04']

def test_mocked_agent_trace_and_error_classification(tmp_path):
    class StubAgent:
        def __init__(self):self.last_trace=[];self.n=0
        def process_query(self,prompt):
            self.n+=1
            if self.n==1:raise Fake503('503 UNAVAILABLE')
            self.last_trace=[{'tool':'query_expiring_items_tool'},{'tool':'recommend_recipes_for_servings_tool'}]
            return 'done'
    case=next(c for c in mod.load_cases() if c['id']=='MUL-01')
    r=mod.run_live([case],tmp_path,1,'multi_tool',max_retries=1,retry_base=0,agent=StubAgent())
    assert r['api_success_rate']==1 and r['valid_tool_selection_accuracy']==1
    row=json.loads(json.dumps((tmp_path/'live_results.csv').read_text(encoding='utf-8-sig')))
    assert 'retry_count' in row

def test_previous_live_results_preserved(tmp_path):
    f=tmp_path/'live_results.csv';f.write_text('old')
    bak=mod.preserve_existing(f)
    assert bak.exists() and bak.read_text()=='old' and not f.exists()

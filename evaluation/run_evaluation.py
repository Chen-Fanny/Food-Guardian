"""Food Guardian v3.3 evaluation. Default OFFLINE: never calls cloud APIs or user SQLite.

Run from project root:
  python evaluation/run_evaluation.py
  python evaluation/run_evaluation.py --live --category multi_tool --limit 5
"""
from __future__ import annotations
import argparse
import csv
import json
import re
import sys
import time
from datetime import datetime, timezone
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
HERE = Path(__file__).resolve().parent
TODAY = date(2026, 11, 11)  # pinned for reproducible deterministic checks


def fixture_inventory(today: date = TODAY):
    def item(index, name, quantity, unit, delta, label='use_by'):
        return {'id':index, 'name':name, 'quantity':float(quantity), 'unit':unit,
                'expiry_date': (today+timedelta(days=delta)).isoformat() if delta is not None else None,
                'date_label_type':label if delta is not None else None, 'status':'active',
                'storage_location':'refrigerated'}
    return [item(1,'番茄',2,'piece',1),item(2,'雞蛋',3,'piece',5),
            item(3,'菠菜',1,'other',2),item(4,'雞胸肉',300,'g',3),
            item(5,'牛奶',1,'l',4),item(6,'高麗菜',1,'piece',6)]


def load_cases():
    data=json.loads((HERE/'cases.json').read_text(encoding='utf-8'))
    assert len(data)==30 and len(set(x['id'] for x in data))==30
    return data


def find_recipe(recs,title):
    return next((r for r in recs if r['title']==title), None)


def assess_offline(case):
    """Returns status PASS/FAIL/NOT_RUN and details. Does NOT claim LLM metrics."""
    from src.services.portion_service import recommend_for_servings
    from src.services.safety_service import assess_inventory_safety
    items = fixture_inventory()
    exp=case['expected']; cat=case['category']
    if cat=='inventory':
        if 'min_count' in exp:
            ok=len(items)>=exp['min_count']; detail=f'fixture contains {len(items)} items'
        elif 'absent' in exp:
            ok=not any(x['name']==exp['absent'] for x in items);detail='item not present in fixture'
        elif 'expires_within_days' in exp:
            names=[x['name'] for x in items if x['expiry_date'] and 0 <= (date.fromisoformat(x['expiry_date'])-TODAY).days <= exp['expires_within_days']]
            ok=all(n in names for n in exp['contains']); detail='expiring items: '+','.join(names)
        else:
            found=next((x for x in items if x['name']==exp['name']),None)
            ok=bool(found) and found['quantity']==exp['quantity'] and ('unit' not in exp or found['unit']==exp['unit'])
            detail=str(found)
        return ('PASS' if ok else 'FAIL', detail)
    if cat in ('recipe','quantity'):
        mode=exp.get('mode','balanced')
        recs=recommend_for_servings(items,servings=2,mode=mode,today=TODAY)
        recipe=find_recipe(recs,exp['recipe'])
        if not recipe: return 'FAIL','recipe missing from results'
        if cat=='recipe':
            if mode=='ready_now': ok=recs[0]['title']=='高麗菜炒蛋' and recs[0]['can_make_now']
            elif mode=='expiry_first': ok=recs[0]['title']=='番茄炒蛋' and not recs[0]['can_make_now']
            else: ok=recipe in recs
            return ('PASS' if ok else 'FAIL', f'first={recs[0]["title"]}; target={recipe["title"]}')
        row=next((x for x in recipe['ingredient_requirements'] if x['ingredient']==exp['ingredient']),None)
        ok = bool(row) and row['status'] == exp['status']
        if ok and 'missing' in exp:
            ok = abs(row['missing_quantity'] - exp['missing']) < 1e-6
        if ok and 'available' in exp:
            ok = abs(row['available_quantity'] - exp['available']) < 1e-6
        return ('PASS' if ok else 'FAIL', str(row))
    if cat=='safety':
        src=exp['item']; delta=src.get('expiry_days'); changed=dict(items[0]); changed.update(name=src['name'], expiry_date=(TODAY+timedelta(days=delta)).isoformat() if delta is not None else None, date_label_type=src.get('date_label_type'))
        if src.get('known_spoiled'): changed['known_spoiled']=True
        actual=assess_inventory_safety([changed],item_name=src['name'],today=TODAY)['items'][0]['status']
        return ('PASS' if actual==exp['status'] else 'FAIL',f'expected={exp["status"]}, actual={actual}')
    if cat=='rag':
        # Only source-document readiness; NOT an embedding retrieval or groundedness metric.
        path=ROOT/'data/knowledge_base/rag_documents/official_food_safety.json'
        if not path.exists(): return 'NOT_RUN','official RAG document file missing'
        docs=json.loads(path.read_text(encoding='utf-8'))
        def is_valid(d):return bool(d.get('source_url','').startswith('https://') and d.get('content') and d.get('title'))
        matching=[d for d in docs if is_valid(d) and any(term.lower() in json.dumps(d,ensure_ascii=False).lower() for term in exp['keywords'])]
        return ('PASS' if matching else 'FAIL', 'STATIC source metadata check; match count='+str(len(matching)))
    return 'NOT_RUN','Requires a live LLM/tool-calling test; not executed offline'


def tool_names(trace):
    return [str(x.get('tool','')) for x in (trace or [])]


def score_live(case, trace, response):
    names=tool_names(trace)
    expected=set(case['expected_tools'])
    actual=set(names)
    selected=bool(expected) and expected.issubset(actual)
    # NEVER automatically claim task completion or factual groundedness from trace alone.
    return {'tool_selection_pass':selected,'missing_tools':sorted(expected-actual),
            'called_tools':names,'reply_present':bool(str(response).strip()),
            'task_completion_review':'REQUIRES_HUMAN_REVIEW',
            'groundedness_review':'REQUIRES_HUMAN_REVIEW'}


def run_offline(cases, outdir):
    rows=[]
    for c in cases:
        try: status,detail=assess_offline(c)
        except Exception as ex: status,detail='ERROR',f'{type(ex).__name__}: {ex}'
        rows.append({'id':c['id'],'category':c['category'],'status':status,'detail':detail})
    preserve_existing(outdir/'offline_results.csv')
    with (outdir/'offline_results.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['id','category','status','detail']); writer.writeheader();writer.writerows(rows)
    counts=Counter(r['status'] for r in rows)
    return {'checks':len(rows), 'counts':dict(counts), 'note':'PASS means deterministic fixture/static document check only. No Gemini calls or actual RAG retrieval were tested.'}



from evaluation.retry_handler import call_with_retry, classify_exception
from evaluation.metrics import summarize_live


def select_live_cases(cases, limit, category='all'):
    """Do not silently count RAG-dependent cases: these need an explicitly configured live RAG index."""
    eligible_categories={'inventory','recipe','quantity','safety','multi_tool'}
    scoped=[c for c in cases if c['category'] in eligible_categories and (category=='all' or c['category']==category)]
    unsupported=[c for c in scoped if 'search_food_knowledge' in c['expected_tools']]
    selected=[c for c in scoped if 'search_food_knowledge' not in c['expected_tools']][:limit]
    return selected, unsupported


def preserve_existing(path):
    """Keep prior raw evidence rather than overwrite live history."""
    if not path.exists(): return None
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    new_path=path.with_name(path.stem+'_'+stamp+path.suffix)
    path.replace(new_path)
    return new_path


def run_live(cases,outdir,limit,category='all',max_retries=1,retry_base=2.0,agent=None):
    if agent is None:
        from src.agent.gemini_graph import GeminiFoodAgent
        # Synthetic input, no user SQLite read/write. Remote Gemini receives test prompts/fixture.
        class FixtureInventory:
            def get_items(self,status='active',category=None,storage_location=None):
                return fixture_inventory(TODAY)
        agent=GeminiFoodAgent(FixtureInventory())
    picked, skipped=select_live_cases(cases,limit,category)
    rows=[]
    for c in picked:
        start=time.perf_counter()
        error=''; errorcode=None; retries=0; reply=''
        try:
            def invoke():
                agent.last_trace=[]  # avoid stale trace across retry attempts
                return agent.process_query(c['prompt'])
            reply,retries=call_with_retry(invoke,max_retries=max_retries,base_delay=retry_base)
            score=score_live(c,agent.last_trace,reply)
            state='PASS' if score['tool_selection_pass'] else 'TOOL_MISMATCH'
        except Exception as exc:
            state,errorcode=classify_exception(exc)
            retries=getattr(exc,'fg_retry_count',0)
            error=f'{type(exc).__name__}: {str(exc)[:600]}'
            score=score_live(c,[],reply)
        rows.append({'id':c['id'],'category':c['category'],'prompt':c['prompt'],
            'execution_status':state,'api_success':state in ('PASS','TOOL_MISMATCH'),
            'error_code':errorcode if errorcode is not None else '',
            'retry_count':retries,'seconds':round(time.perf_counter()-start,3),
            'tool_selection_pass':score['tool_selection_pass'] if state in ('PASS','TOOL_MISMATCH') else '',
            'called_tools':json.dumps(score['called_tools'],ensure_ascii=False),
            'missing_tools':json.dumps(score['missing_tools'],ensure_ascii=False),
            'task_completion_review':'REQUIRES_HUMAN_REVIEW' if state in ('PASS','TOOL_MISMATCH') else 'NOT_EVALUABLE',
            'groundedness_review':'REQUIRES_HUMAN_REVIEW' if state in ('PASS','TOOL_MISMATCH') else 'NOT_EVALUABLE',
            'error':error,'answer_excerpt':reply[:700]})
    if rows:
        path=outdir/'live_results.csv'
        preserve_existing(path)
        with path.open('w',encoding='utf-8-sig',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0].keys()));writer.writeheader();writer.writerows(rows)
    metrics=summarize_live(rows,skipped=skipped)
    if skipped: metrics['skip_reason']='RAG-dependent cases require a separately configured, verified RAG retrieval evaluation; not silently run against an unconfigured agent.'
    return metrics


def main():
    p=argparse.ArgumentParser(description='Food Guardian v3.3 controlled evaluation (offline by default)')
    p.add_argument('--live',action='store_true',help='Calls Gemini API; may incur charges. Never writes user SQLite.')
    p.add_argument('--limit',type=int,default=3,help='Maximum eligible live cases, default 3')
    p.add_argument('--category',choices=['all','inventory','recipe','quantity','safety','multi_tool'],default='all')
    p.add_argument('--max-retries',type=int,default=1,help='Number of additional 429/503/504 retries per case, default 1')
    p.add_argument('--retry-base',type=float,default=2.0,help='Base backoff delay seconds, default 2')
    p.add_argument('--output',default='evaluation/results',help='Output directory relative to project root')
    args=p.parse_args()
    if not 1<=args.limit<=30:p.error('--limit must be between 1 and 30')
    if not 0<=args.max_retries<=5:p.error('--max-retries must be between 0 and 5')
    if not 0<=args.retry_base<=60:p.error('--retry-base must be between 0 and 60')
    outdir=Path(args.output)
    if not outdir.is_absolute():outdir=ROOT/outdir
    outdir.mkdir(parents=True,exist_ok=True)
    cases=load_cases()
    report={'suite_version':'v3.3','fixture_today':TODAY.isoformat(),
            'total_cases':len(cases),'offline':run_offline(cases,outdir)}
    if args.live: report['live']=run_live(cases,outdir,args.limit,args.category,args.max_retries,args.retry_base)
    summary=outdir/'summary.json'
    preserve_existing(summary)
    summary.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    print('Reports:',outdir)

if __name__=='__main__':main()

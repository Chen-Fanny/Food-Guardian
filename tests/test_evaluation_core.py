"""Offline evaluation integrity and deterministic regression checks. No API/network/SQLite."""
import importlib.util
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('fg_eval', ROOT/'evaluation/run_evaluation.py')
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_30_cases_6_categories():
    cases=module.load_cases()
    assert len(cases)==30
    from collections import Counter
    assert Counter(x['category'] for x in cases)==dict.fromkeys(['inventory','recipe','quantity','safety','rag','multi_tool'],5)


def test_expected_tool_names():
    for case in module.load_cases():
        assert case['expected_tools'] and all(x.endswith('_tool') or x=='search_food_knowledge' for x in case['expected_tools'])


def test_offline_deterministic_checks():
    cases=module.load_cases()
    for case in cases:
        if case['category'] in ('inventory','recipe','quantity','safety'):
            status,detail=module.assess_offline(case)
            assert status=='PASS',f'{case["id"]}: {detail}'


def test_multi_tool_is_not_falsely_auto_scored():
    for case in module.load_cases():
        if case['category']=='multi_tool':
            assert module.assess_offline(case)[0]=='NOT_RUN'


def test_tool_selection_requires_all_expected_tools():
    case=next(x for x in module.load_cases() if x['category']=='multi_tool')
    one=[{'tool':case['expected_tools'][0]}]
    assert module.score_live(case,one,'OK')['tool_selection_pass'] is False
    both=[{'tool':n} for n in case['expected_tools']]
    assert module.score_live(case,both,'OK')['tool_selection_pass'] is True
    assert module.score_live(case,both,'OK')['groundedness_review']=='REQUIRES_HUMAN_REVIEW'

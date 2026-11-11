"""Deterministic tests: no Gemini API, no external networks, no SQLite mutations."""
from datetime import date, timedelta
import json
from src.services.portion_service import recommend_for_servings, classify_item


def make_item(name, qty, unit, days=3, label='use_by'):
    return {'name': name, 'status': 'active', 'quantity': qty, 'unit': unit,
            'expiry_date': (date.today()+timedelta(days=days)).isoformat() if days is not None else None,
            'date_label_type': label}


def find(results, name):
    return next(r for r in results if r['title'] == name)


def requirement(recipe, name):
    return next(r for r in recipe['ingredient_requirements'] if r['ingredient'] == name)


def test_two_person_missing_one_egg():
    results = recommend_for_servings([make_item('番茄', 2, 'piece', 1), make_item('雞蛋', 3, 'piece', 5)], servings=2)
    tomato = find(results, '番茄炒蛋')
    egg = requirement(tomato, '雞蛋')
    assert egg['required_quantity'] == 4
    assert egg['available_quantity'] == 3
    assert egg['missing_quantity'] == 1
    assert egg['status'] == 'insufficient'
    assert not tomato['all_quantities_sufficient']


def test_mass_and_volume_conversions():
    recipes = recommend_for_servings([make_item('牛奶', 1, 'l'), make_item('燕麥', .1, 'kg')])
    porridge = find(recipes, '牛奶燕麥粥')
    assert porridge['all_quantities_sufficient']
    assert requirement(porridge, '牛奶')['available_quantity'] == 1000
    assert requirement(porridge, '燕麥')['available_quantity'] == 100


def test_pack_is_not_assumed_to_be_grams():
    items = [make_item('牛奶', 1, 'pack'), make_item('燕麥', 100, 'g')]
    row = requirement(find(recommend_for_servings(items), '牛奶燕麥粥'), '牛奶')
    assert row['status'] == 'unknown'
    assert row['unconvertible_stock_units'] == ['pack']
    assert not find(recommend_for_servings(items), '牛奶燕麥粥')['all_quantities_sufficient']


def test_overdue_use_by_excluded_and_best_before_review():
    items = [make_item('番茄', 2, 'piece', -1, 'use_by'), make_item('雞蛋', 4, 'piece', 4)]
    tomato = find(recommend_for_servings(items), '番茄炒蛋')
    assert requirement(tomato, '番茄')['status'] == 'missing'
    assert any(x['status'] == 'blocked' for x in tomato['excluded_items'])
    item = make_item('番茄', 2, 'piece', -1, 'best_before')
    assert classify_item(item)[0] == 'review'


def test_invalid_servings():
    for n in [0, 13, True, 2.5, '2']:
        try: recommend_for_servings([], n)
        except ValueError: pass
        else: assert False, n


def test_no_db_mutation():
    items = [make_item('雞蛋', 3, 'piece')]
    old = json.dumps(items, ensure_ascii=False, sort_keys=True)
    recommend_for_servings(items, 2)
    assert json.dumps(items, ensure_ascii=False, sort_keys=True) == old


def test_incompatible_dimensions():
    items=[make_item('牛奶', 500, 'g'), make_item('燕麥', 100, 'g')]
    row=requirement(find(recommend_for_servings(items), '牛奶燕麥粥'), '牛奶')
    assert row['status'] == 'unknown'

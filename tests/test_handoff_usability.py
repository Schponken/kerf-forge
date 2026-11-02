"""Generated guides give a usable first-build order and preserve special characters."""
import csv
from pathlib import Path

from kerf import electrical, ship, wiring_out
from test_ship import _bolt
from test_electrical import _proj


def test_shopping_table_handles_pipes_newlines_and_link_parentheses(tmp_path):
    rows=[{'type':'hardware','item':'hinge | plate','qty':2,'spec':'A < B','note':'first\nsecond',
           'price_key':'hinge','buy':'https://shop.example/part (small)?a=1&b=2','unit_usd':3,'total_usd':6}]
    summary={'total_usd':6,'unpriced':[],'approximate':[],'on_hand':[]}
    ship.write_bom(rows,summary,tmp_path)
    text=(tmp_path/'bom.md').read_text(encoding='utf-8')
    assert text.startswith('# Shopping list') and 'quantity used' in text
    assert 'hinge \\| plate' in text and 'A &lt; B' in text and 'first<br>second' in text
    assert '[buy](https://shop.example/part%20%28small%29?a=1&b=2)' in text
    assert '**Total: $6.00**' in text
    with (tmp_path/'bom.csv').open(encoding='utf-8',newline='') as f:
        got=next(csv.DictReader(f))
    assert got['item']==rows[0]['item'] and got['note']==rows[0]['note'] and got['buy']==rows[0]['buy']


def test_unpriced_budget_is_visible_before_the_table(tmp_path):
    rows=[{'type':'hardware','item':'unknown','qty':1,'spec':'','note':'','buy':'','unit_usd':'','total_usd':''}]
    ship.write_bom(rows,{'total_usd':0,'unpriced':['unknown']},tmp_path)
    text=(tmp_path/'bom.md').read_text(encoding='utf-8')
    assert text.index('not a complete budget') < text.index('| Type |')
    assert '**Priced so far: $0.00**' in text


def test_assembly_puts_test_fit_before_bulk_printing_and_links_the_guides(tmp_path):
    proj,asm,fj=_bolt(tmp_path)
    ship.write_assembly(proj,asm,{'assembly':{'fasteners':fj,'pins':[]},'parts':{},'bom':[]},tmp_path)
    text=(tmp_path/'ASSEMBLY.md').read_text(encoding='utf-8')
    assert 'Start with the test-fit in Step 0, then print the remaining parts' in text
    assert '[print settings](plates/PRINT_SETTINGS.md)' in text and '[bom.md](bom.md)' in text
    assert 'Print every part' not in text


def test_purchased_only_assembly_does_not_invent_a_printing_step(tmp_path):
    proj,asm=_proj(tmp_path)
    assert not proj.printed
    ship.write_assembly(proj,asm,{'assembly':{'fasteners':[],'pins':[]},'parts':{},'bom':[]},tmp_path)
    text=(tmp_path/'ASSEMBLY.md').read_text(encoding='utf-8')
    assert 'no printed parts' in text and 'test-fit before printing everything' not in text
    assert 'print the smallest part' not in text


def test_wiring_guide_explains_units_and_existing_cut_lengths(tmp_path):
    proj,asm=_proj(tmp_path)
    model=electrical.analyse(proj)
    text=wiring_out.wiring_md(proj,model)
    assert 'A means amps' in text and 'lower AWG number means a thicker wire' in text
    assert 'do not add that slack a second time' in text
    assert '[wiring diagram](wiring.svg)' in text and '[assembly guide](ASSEMBLY.md)' in text
    for w in model['wires']:
        assert f"| {w['id']} |" in text and f"| {w['length_mm']} |" in text


def test_invalid_shop_link_is_not_emitted_as_an_executable_link(tmp_path):
    rows=[{'type':'hardware','item':'part','qty':1,'spec':'','note':'','buy':'javascript:alert(1)',
           'price_key':'part','unit_usd':2,'total_usd':2}]
    ship.write_bom(rows,{'total_usd':2,'unpriced':[]},tmp_path)
    text=(tmp_path/'bom.md').read_text(encoding='utf-8')
    assert 'Link unavailable' in text and '[buy]' not in text and 'javascript:' not in text
    with (tmp_path/'bom.csv').open(encoding='utf-8',newline='') as f:
        assert next(csv.DictReader(f))['buy']=='javascript:alert(1)'

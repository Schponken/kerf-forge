"""The announced progress queue must match core-first execution, including use-story checks."""
import json

import pytest
import yaml

from kerf import partcache, pipeline
from test_engine import BOLT_YAML, BOLT_BLOCK, BOLT_PLATE, _write_project


@pytest.mark.parametrize('mode', [None, 'sketch'])
def test_announced_queue_matches_selected_checks(tmp_path, monkeypatch, capsys, mode):
    monkeypatch.setenv('KERF_PROGRESS','1')
    monkeypatch.setattr(partcache,'DIR',tmp_path/'cache')
    data=yaml.safe_load(BOLT_YAML)
    data['requirements']=[{'id':'detail_heat','check':'heat_limit','max_c':30},
                          {'id':'weight','check':'mass_max','max_g':500}]
    data['use_story']={'who':'maker','where':['desk'],'how_often':'weekly',
                       'goes_wrong':[{'hazard':'heat','max_c':35}]}
    d=_write_project(tmp_path/'rig',yaml.safe_dump(data),{'block':BOLT_BLOCK,'plate':BOLT_PLATE})
    rep=pipeline.run(str(d),sweeps=False,mode=mode)
    events=[json.loads(s[2:]) for s in capsys.readouterr().out.splitlines() if s.startswith('@@')]
    expected=[] if mode=='sketch' else ['weight','detail_heat','story_heat']
    assert events[0]['reqs']==expected
    assert [e['id'] for e in events if e['k']=='req']==expected
    assert [r['id'] for r in rep['requirements']]==expected

"""Displayed assembly paths are sampled against their actual staged CAD obstacles."""
from types import SimpleNamespace

import numpy as np
import pytest
from build123d import Box, Location

from kerf import access, geom, viewer, assembly as A, project as P
from test_access import BASE, PEG, LIP
from test_engine import _write_project


def _asm(tmp_path, order='[base, peg, lip]', peg=PEG):
    data = f'''name: Guide paths
parts:
  base: {{file: parts/base.py}}
  peg: {{file: parts/peg.py, insert: {{direction: [0, 0, -1], distance: 25}}}}
  lip: {{file: parts/lip.py}}
assembly:
  root: base
  order: {order}
  joints:
    - {{parent: base.seat, child: peg.foot}}
    - {{parent: base.origin, child: lip.origin}}
'''
    proj = P.build(P.load(str(_write_project(tmp_path, data, {'base': BASE, 'peg': peg, 'lip': LIP}))))
    assert all(not item.error for item in proj.items.values())
    asm = A.plan(proj)
    A.solve(asm)
    return asm


def _matrix(shape):
    t = shape.location.wrapped.Transformation()
    return tuple(t.Value(r, c) for r in (1, 2, 3) for c in (1, 2, 3, 4))


@pytest.mark.parametrize('order, expected', [('[base, peg, lip]', 'sampled_clear'),
                                            ('[base, lip, peg]', 'blocked')])
def test_guide_uses_actual_staged_obstacles_and_exact_declared_path(tmp_path, order, expected):
    asm = _asm(tmp_path, order)
    homes = {i: _matrix(it.shape) for i, it in asm.proj.items.items()}
    steps = viewer.assembly_steps(asm.proj, asm, {}, None)['steps']
    group = next(g for s in steps for g in s['groups'] if g['items'] == ['peg'])
    motion = group['motion']
    assert motion['status'] == expected
    assert motion['offset_mm'] == [0, 0, 25]
    assert motion['source'] == 'declared_insertion'
    assert motion['max_step_mm'] <= 1
    assert motion['seat_checked'] is (expected == 'sampled_clear')
    assert ('lip' in motion['obstacles']) is (expected == 'blocked')
    if expected == 'blocked':
        assert motion['collisions'][0]['b'] == 'lip'
        assert motion['samples'] < 26
    assert homes == {i: _matrix(it.shape) for i, it in asm.proj.items.items()}
    assert steps[0]['groups'][0]['motion']['offset_mm'] == [0, 0, 0]


def test_later_group_in_same_phase_sees_preceding_group(tmp_path):
    asm = _asm(tmp_path, '[base, [lip, peg]]')
    steps = viewer.assembly_steps(asm.proj, asm, {}, None)['steps']
    lip, peg = steps[-1]['groups']
    assert lip['phase'] == peg['phase'] == 1
    assert peg['motion']['status'] == 'blocked'
    assert peg['motion']['obstacles'] == ['base', 'lip']


def test_seated_endpoint_is_checked_and_allowed_overlap_is_preserved(tmp_path):
    # A 0.2 mm floor intrusion is absent at the last pre-seat sample, but not at the seat.
    peg = PEG.replace('Box(10, 10, 10,', 'Pos(0, 0, -0.2) * Box(10, 10, 10,')
    asm = _asm(tmp_path, peg=peg)
    hits, samples = access.translation_hits(asm, ['peg'], ['base'], [0, 0, 25], 25, first_hit=True)
    assert samples == 26 and hits[0]['mm_from_seat'] == 0
    assert hits[0]['volume_mm3'] == pytest.approx(20)
    asm.proj.data['assembly']['allow_overlap'] = [{'pair': ['peg', 'base'], 'max_mm3': 21, 'why': 'fixture allowance'}]
    assert access.translation_hits(asm, ['peg'], ['base'], [0, 0, 25], 25)[0] == []


def test_geometry_failure_restores_rotation_and_reports_unverified(monkeypatch):
    moving = Box(1, 2, 3).solid()
    moving.location = Location((0.123456789, 2, 4), (13, 27, 41))
    obstacle = Box(1, 1, 1).solid()
    items = {i: SimpleNamespace(shape=s, role='printed', spec={}) for i, s in [('moving', moving), ('obstacle', obstacle)]}
    asm = SimpleNamespace(proj=SimpleNamespace(items=items, data={'assembly': {}}))
    home = _matrix(moving)

    def fail(*args):
        raise RuntimeError('synthetic boolean failure')

    monkeypatch.setattr(geom, 'overlap', fail)
    group = {'items': ['moving'], 'off': [0, 0, 10], 'phase': 1}
    viewer._guide_motions(asm, [group], ['obstacle', 'moving'])
    assert group['motion']['status'] == 'unverified'
    assert group['motion']['offset_mm'] is None
    assert 'synthetic boolean failure' in group['motion']['reason']
    assert _matrix(moving) == home


@pytest.mark.parametrize('offset,budget', [([0, 0, 201], 10000), ([0, 0, 25], 0), ([0, 0, float('nan')], 10000)])
def test_unsupported_or_over_budget_path_never_claims_clear(tmp_path, offset, budget):
    asm = _asm(tmp_path)
    group = {'items': ['peg'], 'off': offset, 'phase': 1}
    viewer._guide_motions(asm, [group], ['base', 'peg'], budget=budget)
    assert group['motion']['status'] == 'unverified'
    assert group['motion']['offset_mm'] is None


def test_checked_offset_keeps_exact_world_direction_under_rotation(tmp_path):
    asm = _asm(tmp_path)
    shape = asm.proj.items['peg'].shape
    shape.location = Location((30, 20, 10), (0, 37, 13))
    home = _matrix(shape)
    offset = -geom.world_dir(shape.location, (0, 0, -1)) * 25
    group = {'items': ['peg'], 'off': offset.tolist(), 'phase': 1}
    viewer._guide_motions(asm, [group], ['peg'])
    assert group['motion']['status'] == 'sampled_clear'
    assert group['motion']['offset_mm'] == offset.tolist()
    assert _matrix(shape) == home
    assert np.linalg.norm(offset) == pytest.approx(25)


@pytest.mark.parametrize('declared', [False, True])
def test_opposite_candidate_can_clear_but_declared_direction_is_not_replaced(declared):
    moving, obstacle = Box(2, 2, 2).solid(), Box(2, 2, 2).solid()
    obstacle.location = Location((-2, 0, 0)) * obstacle.location
    spec = {'insert': {'direction': [1, 0, 0], 'distance': 5}} if declared else {}
    items = {'moving': SimpleNamespace(shape=moving, role='printed', spec=spec),
             'obstacle': SimpleNamespace(shape=obstacle, role='printed', spec={})}
    asm = SimpleNamespace(proj=SimpleNamespace(items=items, data={'assembly': {}}))
    group = {'items': ['moving'], 'off': [-5, 0, 0], 'phase': 1}
    viewer._guide_motions(asm, [group], ['obstacle', 'moving'])
    motion = group['motion']
    assert motion['status'] == ('blocked' if declared else 'sampled_clear')
    assert len(motion['attempts']) == (1 if declared else 2)
    assert motion['attempts'][0]['collisions']
    if not declared:
        assert motion['offset_mm'] == [5, 0, 0]
        assert motion['seat_checked']
        assert not motion['collisions']


def test_overlapping_components_in_one_moving_group_are_blocked():
    items = {i: SimpleNamespace(shape=Box(2, 2, 2).solid(), role='printed', spec={}) for i in ['a', 'b']}
    asm = SimpleNamespace(proj=SimpleNamespace(items=items, data={'assembly': {}}))
    group = {'items': ['a', 'b'], 'off': [0, 0, 10], 'phase': 2}
    viewer._guide_motions(asm, [group], ['a', 'b'])
    assert group['motion']['status'] == 'blocked'
    assert 'overlapping parts' in group['motion']['reason']

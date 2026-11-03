"""Build it markers use real interface sites, once each, in the assembled part's frame."""
import pytest
from build123d import Location

from kerf import assembly as A, project as P, viewer
from kerf.ctx import PinSite, Site
from kerf.iface import screw_spec


@pytest.fixture
def project(tmp_path):
    (tmp_path / 'parts').mkdir()
    (tmp_path / 'project.yaml').write_text('''name: Insert placement
parts:
  base: {file: parts/base.py}
  arm: {file: parts/arm.py}
assembly:
  root: base
  joints:
    - {parent: base.mount, child: arm.mount}
''')
    for name, loc in [('base', 'Location((30, 20, 10), (0, 90, 0))'), ('arm', 'Location()')]:
        (tmp_path / 'parts' / f'{name}.py').write_text(f'''from build123d import Box, Location
def build(ctx):
    ctx.rigid('mount', {loc})
    return ctx.finish(Box(10, 10, 10))
''')
    proj = P.build(P.load(str(tmp_path)))
    assert all(not item.error for item in proj.items.values())
    return proj


def _steps(proj):
    return viewer.assembly_steps(proj, A.plan(proj), {}, None)['steps']


def test_pivot_and_bolt_inserts_once_per_site_with_parent_rotation(project):
    arm = project.items['arm'].shape
    arm.kerf_sites = [
        Site('bolt_m2', 'female', 'M2', 'heatset', Location((2, 3, 4))),
        Site('bolt_m3', 'female', 'M3', 'heatset', Location((-2, -3, -4))),
        Site('pass_through', 'male', 'M3', 'clearance', Location()),
        Site('tapped', 'female', 'M3', 'tap', Location()),
    ]
    arm.kerf_pins = [
        PinSite('pivot_shoulder', 'motion.shoulder_4_m3', 'heatset', Location((5, 6, 7), (90, 0, 0)), 8, 4),
        PinSite('pivot_m2', 'M2', 'heatset', Location((1, 2, 3)), 8, 2),
        PinSite('free', 'M3', 'free', Location(), 8, 3),
        PinSite('tapped_pivot', 'M3', 'tap', Location(), 8, 3),
    ]
    steps = _steps(project)
    assert steps[0]['inserts'] == []
    rows = steps[1]['inserts']
    assert len(rows) == 4
    assert len({row['id'] for row in rows}) == 4
    by_group = {row['group']: row for row in rows}
    assert set(by_group) == {'bolt_m2', 'bolt_m3', 'pivot_shoulder', 'pivot_m2'}
    assert all(row['item'] == 'arm' for row in rows)
    assert by_group['bolt_m2']['at'] == pytest.approx([34, 23, 8])
    assert by_group['bolt_m2']['dir'] == pytest.approx([-1, 0, 0])
    assert by_group['pivot_shoulder']['at'] == pytest.approx([37, 26, 5])
    assert by_group['pivot_shoulder']['dir'] == pytest.approx([0, 1, 0])
    assert by_group['pivot_shoulder']['screw'] == 'M3'  # thread, rather than the 4 mm bearing shoulder
    for row in rows:
        spec = screw_spec(row['screw'])
        assert row['len'] == spec['insert_len']
        assert row['od'] == spec['insert_hole']
        assert 'warning' not in row
    assert _steps(project)[1]['inserts'] == rows  # stable identities across regeneration


def test_missing_insert_dimensions_are_explicitly_unknown(project, monkeypatch):
    from kerf import iface
    arm = project.items['arm'].shape
    arm.kerf_sites = [Site('bolt', 'female', 'M3', 'heatset', Location((2, 3, 4)))]
    monkeypatch.setattr(iface, 'screw_spec', lambda screw: {'d': 3})
    row = _steps(project)[1]['inserts'][0]
    assert row['at'] == pytest.approx([34, 23, 8])
    assert row['od'] is None and row['len'] is None
    assert 'unknown' in row['warning'].lower()


def test_unknown_screw_catalog_entry_does_not_invent_insert_dimensions(project):
    project.items['arm'].shape.kerf_sites = [Site('unknown', 'female', 'M99', 'heatset', Location())]
    row = _steps(project)[1]['inserts'][0]
    assert row['screw'] == 'M99'
    assert row['od'] is None and row['len'] is None
    assert 'unknown' in row['warning'].lower()


def _pivot(project, pin='motion.shoulder_4_m3', length=8):
    project.items['base'].shape.kerf_pins = [
        PinSite('pivot', pin, 'heatset', Location((30, 20, 10), (0, 90, 0)), 7, 4),
    ]
    project.items['arm'].shape.kerf_pins = [
        PinSite('pivot', pin, 'free', Location((0, 0, 8)), 8, 4),
    ]
    report = {'assembly': {'pins': [{'group': 'pivot', 'pin': pin, 'length_mm': length, 'd_mm': 4,
                                   'fixed_in': ['base'], 'free_in': ['arm']}]}}
    return viewer.assembly_steps(project, A.plan(project), report, None)['steps']


def test_shoulder_pivot_has_exact_head_seat_and_catalog_thread(project):
    from kerf.iface import pin_dims
    steps = _pivot(project)
    assert steps[0]['pins'] == []
    (row,) = steps[1]['pins']
    pd = pin_dims('motion.shoulder_4_m3')
    assert row['kind'] == 'shoulder' and row['group'] == 'pivot'
    assert row['items'] == ['base', 'arm'] and row['item'] == 'arm'
    assert row['phase'] == 1
    assert row['at'] == pytest.approx([38, 20, 10])
    assert row['dir'] == pytest.approx([-1, 0, 0])
    assert row['shoulder_len'] == 8 and row['thread_len'] == pd['thread_len']
    assert row['len'] == 8 + pd['thread_len'] and row['od'] == pd['d']
    assert row['thread_d'] == 3 and row['screw'] == 'M3'
    assert row['head_d'] == pd['head_d'] and row['head_h'] == pd['head_h']
    assert 'warning' not in row


def test_regular_screw_pivot_uses_free_outer_face_and_reported_length(project):
    (row,) = _pivot(project, pin='M3', length=12)[1]['pins']
    assert row['kind'] == 'screw' and row['len'] == 12 and row['od'] == 3
    assert row['at'] == pytest.approx([38, 20, 10])
    assert row['dir'] == pytest.approx([-1, 0, 0])
    assert 'shoulder_len' not in row


@pytest.mark.parametrize('problem', ['missing_length', 'unstocked_length', 'missing_site', 'off_axis', 'dowel'])
def test_pivot_without_verified_seat_is_explicitly_unknown(project, problem):
    if problem == 'dowel':
        _pivot(project, pin='motion.pin_3mm')
        project.items['base'].shape.kerf_pins[0].fit = 'press'
    else:
        _pivot(project)
    if problem == 'missing_site':
        project.items['arm'].shape.kerf_pins = []
    if problem == 'off_axis':
        project.items['arm'].shape.kerf_pins[0].loc = Location((3, 0, 8))
    asm = A.plan(project)
    A.solve(asm)
    row = viewer._pin_sites(asm, [{'group': 'pivot', 'pin': 'motion.pin_3mm' if problem == 'dowel' else 'motion.shoulder_4_m3',
                                  'length_mm': None if problem == 'missing_length' else 999 if problem == 'unstocked_length' else 8,
                                  'd_mm': 4, 'fixed_in': ['base'], 'free_in': ['arm']}], 2)[0]
    assert row['at'] is None and row['dir'] is None
    assert row['phase'] == 2 and 'not recorded' in row['warning']

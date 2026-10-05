"""The shape of an apply request (Ops 1.1): what FS-OPS-001 rejects, for each draft.

Transcribed from chapters 1, 2, 4 and 6 of each draft, and kept in step with its schema
(schema/ops/0.1, schema/ops/0.2, schema/ops/0.3): check-schema runs each schema over every test's request in its
suite, and must agree with this module on which requests are FS-OPS-001. Every object is closed;
every operation has exactly the members its definition lists, exactly one member of each group of
alternatives (ONE_OF), and a member allowed only beside another only with it (NEEDS).

Ops 0.1 is the published table (commit 3bf4f35): moveOpening takes `at` only, and there is no
addLevel. Ops 0.2 adds moveOpening's `by` and `toward`, addLevel, addElement into the program's
`items` or an extension's collection, the adjacency primitives, addRoom's `brief`, setRoomBrief,
addProgramItem, placeElement and moveElement.

Member values are typed only as far as the operation reads them:

- a member the reference grammar resolves - a length, area, point, vector, position or element -
  is a string or the JSON form chapter 3 gives it (an integer length or area, a point `[x, y]` of
  lengths);
- an enumerated member an operation reads (`collection`, `side`, `surface`, `kind`, a host's
  `mode`) is one of its values, and `cascade` is a boolean, `path` a string and `element` an
  object;
- a member passed into an element's content unread (`type`, `layers`, `join`, `name`, `hinge`,
  `function`, `value`, `weight`, `count`, `rotation` …) may be any JSON value: whether the element
  is valid is decided when the batch is validated (2.1.1).
"""

from __future__ import annotations

from .errors import OpsError, esc
from .version import OPS_01, Profile

COLLECTIONS = ('buildings', 'levels', 'junctions', 'walls', 'separators', 'openings', 'rooms',
               'slabs', 'types', 'materials', 'assets')
ROOFS = 'roofs'                                  # Ops 0.3: Core 0.3's twelfth collection (Core 16.1)
STAIRS = 'stairs'                                # Ops 0.3: Core 0.3's thirteenth collection (Core 17.1)
OPTION_SETS, OPTIONS = 'optionSets', 'options'   # Ops 0.3: Core 0.3's design options (Core 19.1)


def collections(profile: Profile) -> tuple:
    """The collections of Core 1.1 an applier of this draft addresses: eleven, and from Ops 0.3 `roofs` and `stairs` too."""
    return COLLECTIONS + ((ROOFS, STAIRS, OPTION_SETS, OPTIONS) if profile.version == '0.3' else ())
SIDES = ('north', 'south', 'east', 'west')
SURFACES = ('wall', 'floor', 'ceiling')
ITEMS = 'items'                                  # Ops 0.2: the program's items, as addElement names them
KINDS = ('required', 'preferred', 'forbidden')


def _string(v):
    return isinstance(v, str)


def _length(v):
    return type(v) is int or isinstance(v, str)


def _point(v):
    return isinstance(v, str) or (isinstance(v, list) and len(v) == 2 and all(_length(x) for x in v))


def _any(v):
    return True


def _object(v):
    return isinstance(v, dict)


def _bool(v):
    return isinstance(v, bool)


def _enum(*values):
    return lambda v: isinstance(v, str) and v in values


STRING, LENGTH, AREA, POINT, VECTOR, POSITION, ANY, OBJECT, BOOL = (
    _string, _length, _length, _point, _point, _length, _any, _object, _bool)

WALL_MEMBERS = {'type': ANY, 'layers': ANY, 'justification': ANY, 'base': ANY, 'top': ANY}
COMMON = {'name': ANY, 'extensions': ANY, 'extras': ANY}      # every element may carry these (Core 1.4)

# op -> (required members, optional members); `op` itself is implied. Ops 0.1, as published.
OPERATIONS_01 = {
    # 2. primitives
    'addElement': ({'collection': _enum(*COLLECTIONS), 'element': OBJECT}, {'id': STRING}),
    'addJunction': ({'level': STRING, 'position': POINT}, {'id': STRING, 'join': ANY, **COMMON}),
    'addWall': ({'level': STRING, 'start': STRING, 'end': STRING}, {'id': STRING, **WALL_MEMBERS, **COMMON}),
    'addSeparator': ({'level': STRING, 'start': STRING, 'end': STRING}, {'id': STRING, **COMMON}),
    'removeElement': ({'id': STRING}, {'cascade': BOOL}),
    'setProperty': ({'id': STRING, 'path': STRING, 'value': ANY}, {}),
    'unsetProperty': ({'id': STRING, 'path': STRING}, {}),
    'moveJunction': ({'id': STRING, 'to': POINT}, {}),
    # 4. composites
    'drawWall': ({'level': STRING, 'from': POINT, 'to': POINT}, {'id': STRING, **WALL_MEMBERS, **COMMON}),
    'drawSeparator': ({'level': STRING, 'from': POINT, 'to': POINT}, {'id': STRING, **COMMON}),
    'moveWall': ({'wall': STRING, 'by': LENGTH}, {'toward': STRING}),
    'moveRoom': ({'room': STRING, 'by': VECTOR}, {}),
    'resizeRoom': ({'room': STRING, 'side': _enum(*SIDES), 'by': LENGTH}, {}),
    'addOpening': ({'wall': STRING, 'at': POSITION},
                   {'id': STRING, 'fill': STRING, 'width': LENGTH, 'height': LENGTH, 'sill': LENGTH,
                    'hinge': ANY, 'swing': ANY, **COMMON}),
    'moveOpening': ({'opening': STRING, 'at': POSITION}, {}),
    'addRoom': ({'level': STRING, 'at': POINT},
                {'id': STRING, 'function': ANY, 'wallFinish': ANY, 'floorFinish': ANY,
                 'ceilingFinish': ANY, **COMMON}),
    'setRoomFinish': ({'room': STRING, 'surface': _enum(*SURFACES), 'material': STRING}, {}),
    'removeWall': ({'wall': STRING}, {'keep': STRING}),
}

# Ops 0.2: the 0.1 table, with these operations added or changed.
OPERATIONS_02 = {
    **OPERATIONS_01,
    # 2.1: into the thirteen collections, the program's items, or (with `extension`) an extension's collection
    'addElement': ({'collection': STRING, 'element': OBJECT}, {'id': STRING, 'extension': STRING}),
    # 2.6
    'setAdjacency': ({'a': STRING, 'b': STRING, 'kind': _enum(*KINDS)}, {'weight': ANY}),
    'removeAdjacency': ({'a': STRING, 'b': STRING, 'kind': _enum(*KINDS)}, {}),
    # 4.5, 4.6, 4.8
    'moveOpening': ({'opening': STRING}, {'at': POSITION, 'by': LENGTH, 'toward': _enum('start', 'end', *SIDES)}),
    'addRoom': ({'level': STRING, 'at': POINT},
                {'id': STRING, 'function': ANY, 'wallFinish': ANY, 'floorFinish': ANY,
                 'ceilingFinish': ANY, 'brief': STRING, **COMMON}),
    'setRoomBrief': ({'room': STRING, 'item': STRING}, {}),
    'addLevel': ({'building': STRING, 'height': LENGTH},
                 {'elevation': LENGTH, 'above': STRING, 'below': STRING, 'id': STRING, **COMMON}),
    # 4.9, 4.10
    'addProgramItem': ({'function': ANY},
                       {'id': STRING, 'count': ANY, 'targetArea': AREA, 'minArea': AREA, 'level': STRING, **COMMON}),
    'placeElement': ({'extension': STRING, 'collection': STRING, 'host': OBJECT, 'element': OBJECT}, {'id': STRING}),
    'moveElement': ({'element': STRING, 'host': OBJECT}, {}),
}

# op -> groups of members of which exactly one must be present (4.5, 4.8)
ONE_OF_02 = {
    'moveOpening': (('at', 'by'),),
    'addLevel': (('elevation', 'above', 'below'),),
}
# op -> {member: the member it is allowed only beside}
NEEDS_02 = {
    'moveOpening': {'toward': 'by'},
}

# 4.10: the host references of placeElement and moveElement, by mode: (required, optional, one-of groups)
HOSTS = {
    'wallFace': ({'wall': STRING, 'at': POSITION, 'height': LENGTH},
                 {'side': _enum('left', 'right'), 'toward': STRING}, (('side', 'toward'),)),
    'surface': ({'room': STRING, 'surface': _enum('floor', 'ceiling'), 'at': POINT}, {'rotation': ANY}, ()),
    'free': ({'level': STRING, 'at': POINT}, {'rotation': ANY}, ()),
}

PRIMITIVES = ('addElement', 'addJunction', 'addWall', 'addSeparator', 'removeElement', 'setProperty',
              'unsetProperty', 'moveJunction', 'setAdjacency', 'removeAdjacency')


def operations(profile: Profile) -> dict:
    return OPERATIONS_02 if profile.v02 else OPERATIONS_01


def _bad(pointer, why):
    raise OpsError('FS-OPS-001', pointer=pointer, note=why)


def _members(name, obj, required, optional, pointer, skip=('op',)):
    for k in required:
        if k not in obj:
            _bad(pointer, f'{name} is missing "{k}"')
    for k, v in obj.items():
        if k in skip:
            continue
        check = required.get(k) or optional.get(k)
        if check is None:
            _bad(f'{pointer}/{esc(k)}', f'{name} has no member "{k}"')
        if not check(v):
            _bad(f'{pointer}/{esc(k)}', f'"{k}" has the wrong type')


def _one_of(name, obj, groups, pointer):
    for group in groups:
        present = [k for k in group if k in obj]
        if len(present) != 1:
            _bad(pointer, f'{name} takes exactly one of {", ".join(group)}')


def check_host(host, pointer: str) -> None:
    """4.10: a host reference has exactly the members of its mode."""
    mode = host.get('mode')
    if not isinstance(mode, str) or mode not in HOSTS:
        _bad(f'{pointer}/mode', f'unknown host mode {mode!r}')
    required, optional, groups = HOSTS[mode]
    _members(f'a {mode} host', host, required, optional, pointer, skip=('mode',))
    _one_of(f'a {mode} host', host, groups, pointer)


def check_operation(op, pointer: str, profile: Profile = OPS_01) -> None:
    if not isinstance(op, dict):
        _bad(pointer, 'an operation is not an object')
    name = op.get('op')
    table = operations(profile)
    if not isinstance(name, str) or name not in table:
        _bad(f'{pointer}/op', f'unknown operation {name!r}')
    required, optional = table[name]
    _members(name, op, required, optional, pointer)
    if not profile.v02:
        return
    _one_of(name, op, ONE_OF_02.get(name, ()), pointer)
    for k, other in NEEDS_02.get(name, {}).items():
        if k in op and other not in op:
            _bad(f'{pointer}/{esc(k)}', f'"{k}" is allowed only with "{other}"')
    if name == 'addElement' and 'extension' not in op and op['collection'] not in collections(profile) + (ITEMS,):
        _bad(f'{pointer}/collection', f'unknown collection {op["collection"]!r}')
    if 'host' in op and name in ('placeElement', 'moveElement'):
        check_host(op['host'], f'{pointer}/host')


def check_lock(lock, pointer: str) -> None:
    if not isinstance(lock, dict) or len(lock) != 1:
        _bad(pointer, 'a lock is an object with exactly one member')
    (k, v), = lock.items()
    if k in ('element', 'length'):
        if not isinstance(v, str):
            _bad(f'{pointer}/{k}', 'not an ID')
    elif k == 'distance':
        if not (isinstance(v, list) and len(v) == 2 and all(isinstance(x, str) for x in v)):
            _bad(f'{pointer}/{k}', 'a distance lock names two walls')
    else:
        _bad(f'{pointer}/{esc(k)}', f'unknown lock kind "{k}"')


def check_request(req, profile: Profile = OPS_01) -> None:
    """Raises FS-OPS-001 for the first problem found in the request."""
    if not isinstance(req, dict):
        _bad('', 'the request is not an object')
    if 'batch' not in req:
        _bad('', 'the request has no batch')
    for k in req:
        if k not in ('batch', 'context'):
            _bad(f'/{esc(k)}', f'unknown member "{k}"')
    batch = req['batch']
    if not isinstance(batch, list):
        _bad('/batch', 'not a batch')
    if not batch:
        _bad('/batch', 'an empty batch')
    for i, op in enumerate(batch):
        check_operation(op, f'/batch/{i}', profile)
    if 'context' in req:
        ctx = req['context']
        if not isinstance(ctx, dict):
            _bad('/context', 'not an object')
        for k in ctx:
            if k not in ('locks', 'retired') + (('option',) if profile.v03 else ()):
                _bad(f'/context/{esc(k)}', f'unknown member "{k}"')
        if 'option' in ctx and not isinstance(ctx['option'], str):        # Ops 0.3, 2.8
            _bad('/context/option', 'not an ID')
        if 'locks' in ctx:
            if not isinstance(ctx['locks'], list):
                _bad('/context/locks', 'not an array')
            for i, lock in enumerate(ctx['locks']):
                check_lock(lock, f'/context/locks/{i}')
        if 'retired' in ctx:
            r = ctx['retired']
            if not isinstance(r, list) or not all(isinstance(x, str) for x in r):
                _bad('/context/retired', 'not an array of IDs')

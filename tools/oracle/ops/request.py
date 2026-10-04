"""The shape of an apply request (Ops 1.1.1): what FS-OPS-001 rejects.

Transcribed from chapters 1, 2, 4 and 6, and kept in step with schema/ops/0.1 (check-schema runs
that schema over every test's request, and must agree with this module on which requests are
FS-OPS-001). Every object is closed; every operation has exactly the members its definition lists.

Member values are typed only as far as the operation reads them:

- a member the reference grammar resolves - a length, point, vector, position or element - is a
  string or the JSON form chapter 3 gives it (an integer length, a point `[x, y]` of lengths);
- an enumerated member an operation reads (`collection`, `side`, `surface`) is one of its values,
  and `cascade` is a boolean, `path` a string and `element` an object;
- a member passed into an element's content unread (`type`, `layers`, `join`, `name`, `hinge`,
  `function`, `value` …) may be any JSON value: whether the element is valid is decided when the
  batch is validated (2.1.1).
"""

from __future__ import annotations

from .errors import OpsError, esc

COLLECTIONS = ('buildings', 'levels', 'junctions', 'walls', 'separators', 'openings', 'rooms',
               'slabs', 'types', 'materials', 'assets')
SIDES = ('north', 'south', 'east', 'west')
SURFACES = ('wall', 'floor', 'ceiling')


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


STRING, LENGTH, POINT, VECTOR, POSITION, ANY, OBJECT, BOOL = (
    _string, _length, _point, _point, _length, _any, _object, _bool)

WALL_MEMBERS = {'type': ANY, 'layers': ANY, 'justification': ANY, 'base': ANY, 'top': ANY}
COMMON = {'name': ANY, 'extensions': ANY, 'extras': ANY}      # every element may carry these (Core 1.4)

# op -> (required members, optional members); `op` itself is implied.
OPERATIONS = {
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

PRIMITIVES = ('addElement', 'addJunction', 'addWall', 'addSeparator', 'removeElement', 'setProperty',
              'unsetProperty', 'moveJunction')


def _bad(pointer, why):
    raise OpsError('FS-OPS-001', pointer=pointer, note=why)


def check_operation(op, pointer: str) -> None:
    if not isinstance(op, dict):
        _bad(pointer, 'an operation is not an object')
    name = op.get('op')
    if not isinstance(name, str) or name not in OPERATIONS:
        _bad(f'{pointer}/op', f'unknown operation {name!r}')
    required, optional = OPERATIONS[name]
    for k in required:
        if k not in op:
            _bad(pointer, f'{name} is missing "{k}"')
    for k, v in op.items():
        if k == 'op':
            continue
        check = required.get(k) or optional.get(k)
        if check is None:
            _bad(f'{pointer}/{esc(k)}', f'{name} has no member "{k}"')
        if not check(v):
            _bad(f'{pointer}/{esc(k)}', f'"{k}" has the wrong type')


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


def check_request(req) -> None:
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
        check_operation(op, f'/batch/{i}')
    if 'context' in req:
        ctx = req['context']
        if not isinstance(ctx, dict):
            _bad('/context', 'not an object')
        for k in ctx:
            if k not in ('locks', 'retired'):
                _bad(f'/context/{esc(k)}', f'unknown member "{k}"')
        if 'locks' in ctx:
            if not isinstance(ctx['locks'], list):
                _bad('/context/locks', 'not an array')
            for i, lock in enumerate(ctx['locks']):
                check_lock(lock, f'/context/locks/{i}')
        if 'retired' in ctx:
            r = ctx['retired']
            if not isinstance(r, list) or not all(isinstance(x, str) for x in r):
                _bad('/context/retired', 'not an array of IDs')

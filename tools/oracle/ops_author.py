"""The conformance suite of Floorspec Ops 0.1, as the script that writes it.

    python3.13 -m tools.oracle.ops_author            rewrite every test from its declaration below
    python3.13 -m tools.oracle.ops_author --prune    ...and delete test directories no longer declared

Every expected status and diagnostic is written by hand here and cross-checked against the oracle;
the values that matter most - resolved integers, where junctions end up, which wall an opening is
on - are also asserted by hand in each test's `check`. Afterwards,
`python3.13 -m tools.oracle.regenerate` re-verifies the suite from the files alone.
"""
from tools.oracle.ops_author_lib import *  # noqa: F401,F403
from tools.oracle.ops_author_lib import copy, run


def pos(B, j):
    return B['junctions'][j]['position']


def ensure(cond, msg):
    if not cond:
        raise AssertionError(msg)


def resolved_eq(*expected):
    """A check: the resolved echo is exactly these primitives."""
    def check(r, B):
        ensure(r['resolved'] == list(expected), f'resolved {r["resolved"]}')
    return check


def first_resolved(expected):
    def check(r, B):
        ensure(r['resolved'][0] == expected, f'resolved[0] {r["resolved"][0]}')
    return check


def garden(**members):
    """The box, and outside it a free-standing L of garden wall: G1 (16', 2'), G2 (20', 2'),
    G3 (20', 6'); W5 G1->G2 with a 3' gate O1 at 1', W6 G2->G3; G2 is a butt join through W5."""
    d = box(junctions={'G1': J(16 * FT, 2 * FT), 'G2': J(20 * FT, 2 * FT, join={'kind': 'butt', 'through': ['W5']}),
                       'G3': J(20 * FT, 6 * FT)},
            walls={'W5': W('G1', 'G2'), 'W6': W('G2', 'G3')},
            openings={'O1': {'wall': 'W5', 'offset': 1 * FT, 'width': 3 * FT, 'height': 4 * FT}})
    for k, v in members.items():
        d[k] = {**d.get(k, {}), **v} if isinstance(v, dict) and isinstance(d.get(k), dict) else v
    return d


def upstairs(**members):
    """The box on L1, and a level L2 above it with an 8' x 8' room (K1-K4, V1-V4, R2), a slab and
    a window O1 on V1."""
    d = box(levels={'L2': {'building': 'B1', 'elevation': H, 'height': H}},
            junctions={'K1': J(0, 0, 'L2'), 'K2': J(0, 8 * FT, 'L2'), 'K3': J(8 * FT, 8 * FT, 'L2'), 'K4': J(8 * FT, 0, 'L2')},
            walls={'V1': W('K1', 'K2', 'L2'), 'V2': W('K2', 'K3', 'L2'), 'V3': W('K3', 'K4', 'L2'), 'V4': W('K4', 'K1', 'L2')},
            rooms={'R2': R(4 * FT, 4 * FT, 'Loft', 'L2')},
            slabs={'SL1': {'level': 'L2', 'boundary': [[0, 0], [8 * FT, 0], [8 * FT, -4 * FT]], 'thickness': 200 * MM}},
            openings={'O1': {'wall': 'V1', 'offset': 2 * FT, 'width': 3 * FT, 'height': 4 * FT, 'sill': 3 * FT}})
    for k, v in members.items():
        d[k] = {**d.get(k, {}), **v} if isinstance(v, dict) and isinstance(d.get(k), dict) else v
    return d


def chamfered():
    """A 10' x 10' room R1 with its north-east corner cut at 45 degrees: J1 (0, 0), J2 (0, 10'),
    J3 (6', 10'), J4 (10', 6'), J5 (10', 0); W2 north, W3 the chamfer, W4 east."""
    return level_doc(junctions={'J1': J(0, 0), 'J2': J(0, 10 * FT), 'J3': J(6 * FT, 10 * FT),
                                'J4': J(10 * FT, 6 * FT), 'J5': J(10 * FT, 0)},
                     walls={'W1': W('J1', 'J2'), 'W2': W('J2', 'J3'), 'W3': W('J3', 'J4'), 'W4': W('J4', 'J5'),
                            'W5': W('J5', 'J1')},
                     rooms={'R1': R(5 * FT, 5 * FT, 'Study')})


def triangle():
    """A right triangle R1: J1 (0, 0), J2 (0, 10'), J3 (10', 0). Its hypotenuse W2 faces
    north-east, so (3.4) it is on the room's east side, and the room has no north side."""
    return level_doc(junctions={'J1': J(0, 0), 'J2': J(0, 10 * FT), 'J3': J(10 * FT, 0)},
                     walls={'W1': W('J1', 'J2'), 'W2': W('J2', 'J3'), 'W3': W('J3', 'J1')},
                     rooms={'R1': R(2 * FT, 2 * FT, 'Nook')})


def l_shaped():
    """An L-shaped room whose east side is two walls at x = 6' and x = 10': a jogged side."""
    return level_doc(junctions={'J1': J(0, 0), 'J2': J(0, 10 * FT), 'J3': J(6 * FT, 10 * FT), 'J4': J(6 * FT, 5 * FT),
                                'J5': J(10 * FT, 5 * FT), 'J6': J(10 * FT, 0)},
                     walls={'W1': W('J1', 'J2'), 'W2': W('J2', 'J3'), 'W3': W('J3', 'J4'), 'W4': W('J4', 'J5'),
                            'W5': W('J5', 'J6'), 'W6': W('J6', 'J1')},
                     rooms={'R1': R(3 * FT, 3 * FT, 'Den')})


def two_rooms_apart():
    """The box (Living), and 8' east of it a separate 10' x 10' Office: J5 (20', 0), J6 (20', 10'),
    J7 (30', 10'), J8 (30', 0); W5-W8; R2 at (25', 5')."""
    return box(junctions={'J5': J(20 * FT, 0), 'J6': J(20 * FT, 10 * FT), 'J7': J(30 * FT, 10 * FT), 'J8': J(30 * FT, 0)},
               walls={'W5': W('J5', 'J6'), 'W6': W('J6', 'J7'), 'W7': W('J7', 'J8'), 'W8': W('J8', 'J5')},
               rooms={'R2': R(25 * FT, 5 * FT, 'Office')})


def open_plan():
    """The house with an open kitchen: the Kitchen and the Dining room are divided by a separator
    S1 (J7 -> J8) instead of the wall W8."""
    d = house()
    del d['walls']['W8']
    d['separators'] = {'S1': S('J7', 'J8')}
    return d


def courtyard(**members):
    """The box, and east of it the start of a second enclosure: W5 J4 -> J5 (20', 0), W6 J5 -> NE
    (20', 10'), W7 NE -> J7 (13', 10') - its last wall stops a foot short of the box's corner J3."""
    d = box(junctions={'J5': J(20 * FT, 0), 'NE': J(20 * FT, 10 * FT), 'J7': J(13 * FT, 10 * FT)},
            walls={'W5': W('J4', 'J5'), 'W6': W('J5', 'NE'), 'W7': W('NE', 'J7')})
    for k, v in members.items():
        d[k] = {**d.get(k, {}), **v} if isinstance(v, dict) and isinstance(d.get(k), dict) else v
    return d


def door_on_south(offset):
    """The box with a 36-inch door O1 on its south wall W4 (J4 (12', 0) -> J1 (0, 0)) at `offset`."""
    return box(openings={'O1': {'wall': 'W4', 'offset': offset, 'fill': 'T-door-36'}})


def raw(text: str) -> bytes:
    return text.encode('utf-8')


K = "2'"           # two feet: 780288

# ================================================================================== transactions
T('transactions', 'request-not-json', 'A request that is not a JSON text is malformed: FS-OPS-001.',
  ['1.1.1', '7.1.1'], house(), None, 'rejected', [('FS-OPS-001', [])], raw_req=raw('{ "batch": [\n'))
T('transactions', 'request-not-an-object', 'A bare array of operations is not an apply request: the batch goes in '
  '"batch".', ['1.1.1'], house(), [{'op': 'setRoomFinish', 'room': 'Kitchen', 'surface': 'floor', 'material': 'M1'}],
  'rejected', [('FS-OPS-001', [])])
T('transactions', 'empty-batch', 'A batch must contain at least one operation.', ['1.1.1'], house(), req(),
  'rejected', [('FS-OPS-001', [])])
T('transactions', 'batch-not-an-array', '"batch" is an operation object, not an array of them.', ['1.1.1'], house(),
  {'batch': {'op': 'moveJunction', 'id': 'J8', 'to': [0, 0]}}, 'rejected', [('FS-OPS-001', [])])
T('transactions', 'unknown-operation', '"rotateWall" is not an operation this specification defines.', ['1.1.1'],
  house(), req({'op': 'rotateWall', 'wall': 'W8', 'by': 90}), 'rejected', [('FS-OPS-001', [])])
T('transactions', 'missing-member', 'moveJunction without "to".', ['1.1.1'], house(),
  req({'op': 'moveJunction', 'id': 'J8'}), 'rejected', [('FS-OPS-001', [])])
T('transactions', 'unknown-member', 'moveJunction with a "by" member, which its definition does not list.', ['1.1.1'],
  house(), req({'op': 'moveJunction', 'id': 'J8', 'to': [0, 0], 'by': [1, 0]}), 'rejected', [('FS-OPS-001', [])])
T('transactions', 'unknown-member-later-in-batch', 'The second operation of a valid-looking batch has a member its '
  'definition does not list; the whole request is malformed, and nothing is applied.', ['1.1.1', '1.2.2'], house(),
  req({'op': 'setRoomFinish', 'room': 'Kitchen', 'surface': 'floor', 'material': 'M1'},
      {'op': 'resizeRoom', 'room': 'Kitchen', 'side': 'east', 'by': K, 'keepAnchors': True}),
  'rejected', [('FS-OPS-001', [])])
T('transactions', 'member-of-wrong-type', 'removeElement\'s "cascade" is a boolean; the string "yes" makes the request '
  'malformed: every member has the JSON type schema/ops/0.1 gives it.', ['1.1.1'], house(),
  req({'op': 'removeElement', 'id': 'W8', 'cascade': 'yes'}), 'rejected', [('FS-OPS-001', [])])
T('transactions', 'length-not-a-number-or-string', 'A length is a JSON integer or a string: 2.5 is neither, so the '
  'request is malformed (FS-OPS-001), not a grammar failure.', ['1.1.1'], house(),
  req({'op': 'resizeRoom', 'room': 'Kitchen', 'side': 'east', 'by': 2.5}), 'rejected', [('FS-OPS-001', [])])
T('transactions', 'unknown-request-member', 'An apply request has "batch" and "context" only.', ['1.1.1'], house(),
  {'batch': [{'op': 'moveJunction', 'id': 'J8', 'to': [0, 0]}], 'dryRun': True}, 'rejected', [('FS-OPS-001', [])])
T('transactions', 'unknown-context-member', 'context has "locks" and "retired" only.', ['1.1.1'], house(),
  {'batch': [{'op': 'setRoomFinish', 'room': 'Kitchen', 'surface': 'floor', 'material': 'M1'}],
   'context': {'locks': [], 'user': 'matt'}}, 'rejected', [('FS-OPS-001', [])])
T('transactions', 'lock-of-two-kinds', 'A lock is exactly one of the three kinds.', ['1.1.1'], house(),
  req({'op': 'setRoomFinish', 'room': 'Kitchen', 'surface': 'floor', 'material': 'M1'},
      locks=[{'element': 'W8', 'length': 'W8'}]), 'rejected', [('FS-OPS-001', [])])
T('transactions', 'unknown-collection', 'addElement\'s collection is one of the collections of Core 1.1; "roofs" is '
  'reserved, not a collection of 0.1.', ['1.1.1'], house(),
  req({'op': 'addElement', 'collection': 'roofs', 'element': {}}), 'rejected', [('FS-OPS-001', [])])

crossing = house()
crossing['junctions']['J8'] = J(13 * FT, 13 * FT)
T('transactions', 'document-not-valid', 'Document A has crossing walls (FS-INV-104): the batch is rejected with '
  'FS-OPS-002 before any operation is looked at.', ['1.2.1', '7.1.1'], crossing,
  req({'op': 'setRoomFinish', 'room': 'Kitchen', 'surface': 'floor', 'material': 'M1'}),
  'rejected', [('FS-OPS-002', [])])
T('transactions', 'document-not-json', 'Document A is not well-formed JSON (FS-JSON-001): FS-OPS-002.', ['1.2.1'],
  None, req({'op': 'setProperty', 'id': '$project', 'path': '/name', 'value': 'House'}), 'rejected',
  [('FS-OPS-002', [])], raw_a=raw('{ "floorspec": "0.1", "project": { "name": "House" }\n'))
T('transactions', 'document-other-version', 'Document A declares Floorspec 0.2, which this applier does not '
  'implement (FS-DOC-001): FS-OPS-002.', ['1.2.1'], doc(floorspec='0.2'),
  req({'op': 'setProperty', 'id': '$project', 'path': '/name', 'value': 'House'}), 'rejected', [('FS-OPS-002', [])])
T('transactions', 'request-checked-before-document', 'Both the request (an empty batch) and A (crossing walls) are '
  'wrong. The request is checked before A (1.2, 7.1), so the rejection is FS-OPS-001 alone.',
  ['1.1.1', '1.2.1', '7.1.1', '7.1.2'], crossing, req(), 'rejected',
  [('FS-OPS-001', [])])
T('transactions', 'all-or-nothing', 'The first operation would succeed and the second names a junction that does '
  'not exist. The whole batch is rejected with the second\'s FS-OPS-003, and nothing of the first is returned.',
  ['1.2.2', '2.4.1', '7.1.1'], house(),
  req({'op': 'setRoomFinish', 'room': 'Kitchen', 'surface': 'floor', 'material': 'M1'},
      {'op': 'moveJunction', 'id': 'J99', 'to': [0, 0]}), 'rejected', [('FS-OPS-003', [])])


def drawn_room(r, B):
    ensure(r['created'] == ['J1', 'J2', 'J3', 'J4', 'R1', 'W1', 'W2', 'W3', 'W4'], r['created'])
    ensure(B['walls']['W4'] == {'end': 'J1', 'level': 'L1', 'start': 'J4', 'type': 'WT'}, B['walls']['W4'])


T('transactions', 'invalid-intermediate-states', 'A bedroom drawn wall by wall, its room added first: until the last '
  'wall closes the face, the room\'s anchor is in the unbounded face and the document is invalid. Only the end state '
  'is validated, so the batch commits. Each drawWall reuses the junction the previous one left at its start point.',
  ['5.4.1', '4.1.1', '4.6.1', '1.5.1'], level_doc(),
  req({'op': 'addRoom', 'level': 'L1', 'at': ["5'", "5'"], 'name': 'Bedroom', 'function': 'sleeping'},
      {'op': 'drawWall', 'level': 'L1', 'from': [0, 0], 'to': [0, "10'"], 'type': 'WT'},
      {'op': 'drawWall', 'level': 'L1', 'from': [0, "10'"], 'to': ["10'", "10'"], 'type': 'WT'},
      {'op': 'drawWall', 'level': 'L1', 'from': ["10'", "10'"], 'to': ["10'", 0], 'type': 'WT'},
      {'op': 'drawWall', 'level': 'L1', 'from': ["10'", 0], 'to': [0, 0], 'type': 'WT'}), check=drawn_room)
T('transactions', 'result-invalid', 'Removing the wall between the Kitchen and the Dining room joins their faces: two '
  'anchors in one face. The rejection carries the result\'s Core diagnostic, FS-INV-202.',
  ['1.2.3', '1.2.2', '2.2.1'], house(), req({'op': 'removeElement', 'id': 'W8'}), 'rejected',
  [('FS-INV-202', ['R1', 'R3'])])
T('transactions', 'result-schema-invalid', 'setProperty does not check values: "sideways" is not a justification, and '
  'the result fails the schema. The rejection is FS-SCH-001.', ['1.2.3', '2.3.1'], house(),
  req({'op': 'setProperty', 'id': 'W1', 'path': '/justification', 'value': 'sideways'}), 'rejected',
  [('FS-SCH-001', [])])
T('transactions', 'result-has-two-errors', 'A batch whose result has two errors - an anchor moved outside the house '
  'and an opening reaching past its wall\'s end - carries both Core diagnostics, sorted by code.',
  ['1.2.3', '7.1.1'], house(openings={'O1': {'wall': 'W8', 'offset': FT, 'fill': 'T-door-36'}}),
  req({'op': 'setProperty', 'id': 'R2', 'path': '/anchor', 'value': [-FT, 10 * FT]},
      {'op': 'moveOpening', 'opening': 'O1', 'at': "6'"}), 'rejected',
  [('FS-INV-201', ['R2']), ('FS-INV-302', ['O1'])])

noncanon = raw('''{
  "walls": {
    "W2": { "start": "J2", "end": "J3", "level": "L1", "type": "WT", "justification": "center", "extras": {} },
    "W1": { "end": "J2", "start": "J1", "type": "WT", "level": "L1", "base": { "offset": 0 } },
    "W4": { "level": "L1", "start": "J4", "end": "J1", "type": "WT" },
    "W3": { "level": "L1", "start": "J3", "end": "J4", "type": "WT" }
  },
  "junctions": {
    "J4": { "position": [4681728, 0], "level": "L1" },
    "J3": { "position": [4681728, 3901440], "level": "L1", "join": { "kind": "mitre" } },
    "J2": { "position": [0, 3901440], "level": "L1" },
    "J1": { "position": [0, 0], "level": "L1" }
  },
  "rooms": { "R1": { "level": "L1", "anchor": [2340864, 1950720], "name": "Living", "function": "unspecified" } },
  "types": { "WT": { "kind": "wallType", "layers": [ { "thickness": 128000, "function": "core" } ] } },
  "levels": { "L1": { "building": "B1", "elevation": 0, "height": 3456000 } },
  "buildings": { "B1": { "extras": {} } },
  "project": { "name": "Conformance" },
  "extensionsRequired": [],
  "floorspec": "0.1"
}
''')
T('transactions', 'committed-document-is-canonical', 'A is written with members out of order, explicit constant '
  'defaults and empty extras. B is returned exactly in canonical form (Core 9.2): sorted members, no constant '
  'defaults, indented by two spaces, one line feed at the end.', ['1.3.1', '1.6.1'], None,
  req({'op': 'setProperty', 'id': '$project', 'path': '/description', 'value': 'A canonical result.'}),
  raw_a=noncanon)
T('transactions', 'same-batch-same-bytes', 'A batch whose result depends on exact rounding - a junction one metre '
  'from a corner toward the opposite corner of a 12\' x 10\' room, on an irrational diagonal - gives the same bytes '
  'everywhere: 1280000 * 12 / sqrt(244) = 983323.24... and 1280000 * 10 / sqrt(244) = 819436.03..., so the junction '
  'is at [983323, 819436].', ['1.3.2', '3.2.1'], box(),
  req({'op': 'addJunction', 'position': '1 m from J1 toward J3', 'level': 'L1'}),
  check=resolved_eq({'op': 'addJunction', 'id': 'J5', 'level': 'L1', 'position': [983323, 819436]}))
T('transactions', 'resolved-echo', 'moveWall with a selector, a length in feet and toward: the echo is the two '
  'moveJunction primitives it expanded to, with IDs and integers - the Kitchen\'s east wall W8 (J7 -> J8, its left '
  'side west) moved 1\' toward the Dining room, east: J7 to [12\'+1\', 0] = [5071872, 0], J8 to [5071872, 3121152].',
  ['1.4.1', '4.2.1', '3.3.1'], house(),
  req({'op': 'moveWall', 'wall': 'east wall of Kitchen', 'by': "1'", 'toward': 'Dining'}),
  check=resolved_eq({'op': 'moveJunction', 'id': 'J7', 'to': [5071872, 0]},
                    {'op': 'moveJunction', 'id': 'J8', 'to': [5071872, 3121152]}))
T('transactions', 'there-and-back', 'Moving the Kitchen\'s corner J8 across the north wall and back again within one '
  'batch: normalization runs once, after the last operation, so nothing is ever split. B is A, nothing is created '
  'or removed, and the inverse is empty.', ['5.4.1', '1.6.1', '2.4.1'], house(),
  req({'op': 'moveJunction', 'id': 'J8', 'to': ["13'", "13'"]}, {'op': 'moveJunction', 'id': 'J8', 'to': ["12'", "8'"]}),
  check=lambda r, B: ensure(r['inverse'] == [] and r['created'] == [] and r['removed'] == [], r['inverse']))

# ================================================================================== ids
T('ids', 'mint-first', 'An addElement into types with no ID: no ID matches ^T[0-9]+$ ("T-door-36" does not), so '
  'the type is T1.', ['1.5.1', '2.1.1'], house(),
  req({'op': 'addElement', 'collection': 'types', 'element': {'kind': 'windowType', 'width': 3 * FT, 'height': 4 * FT}}),
  check=lambda r, B: ensure(r['created'] == ['T1'], r['created']))
gaps = box()
gaps['junctions']['J7'] = gaps['junctions'].pop('J4')
gaps['walls']['W3']['end'] = 'J7'
gaps['walls']['W4']['start'] = 'J7'
T('ids', 'one-more-than-the-largest', 'Junctions J1, J2, J3 and J7: the next junction is J8, never the free J4.',
  ['1.5.1'], gaps, req({'op': 'addJunction', 'level': 'L1', 'position': ["3'", "3'"]}),
  check=lambda r, B: ensure(r['created'] == ['J8'], r['created']))
T('ids', 'retired-ids-count', 'context.retired lists J12 and W40: the next junction is J13 and the next wall W41, '
  'although neither is in the document.', ['1.5.1'], box(),
  req({'op': 'drawWall', 'level': 'L1', 'from': ["3'", "3'"], 'to': ["6'", "3'"], 'type': 'WT'}, retired=['J12', 'W40', 'X1']),
  check=lambda r, B: ensure(r['created'] == ['J13', 'J14', 'W41'], r['created']))
T('ids', 'minted-earlier-in-the-batch-count', 'A junction minted (J5) and removed in the same batch still counts: the '
  'next one is J6.', ['1.5.1', '2.1.2'], box(),
  req({'op': 'addJunction', 'level': 'L1', 'position': ["3'", "3'"]}, {'op': 'removeElement', 'id': 'J5'},
      {'op': 'addJunction', 'level': 'L1', 'position': ["4'", "3'"]}),
  check=lambda r, B: ensure(r['created'] == ['J6'], r['created']))
prefixes = box(junctions={'J007': J(20 * FT, 3 * FT)},
               slabs={'SL9': {'level': 'L1', 'boundary': [[0, 0], [FT, 0], [0, -FT]], 'thickness': 200 * MM}})
T('ids', 'prefix-matches-exactly', 'A slab SL9 does not match ^S[0-9]+$, so the first separator is S1; J007 is '
  'junction number 7, so the next junction is J8; a new slab is SL10.', ['1.5.1'], prefixes,
  req({'op': 'drawSeparator', 'level': 'L1', 'from': 'J007', 'to': ["24'", "3'"]},
      {'op': 'addElement', 'collection': 'slabs', 'element': {'level': 'L1', 'boundary': [[0, 0], [0, -FT], [-FT, 0]], 'thickness': 200 * MM}}),
  check=lambda r, B: ensure(r['created'] == ['J8', 'S1', 'SL10'], r['created']))
opaque = box()
opaque['rooms']['J20'] = opaque['rooms'].pop('R1')
T('ids', 'ids-are-opaque', 'A room whose ID is J20: every ID in the working copy that matches ^J[0-9]+$ counts, '
  'whatever its collection, so the next junction is J21.', ['1.5.1'], opaque,
  req({'op': 'addJunction', 'level': 'L1', 'position': ["3'", "3'"]}),
  check=lambda r, B: ensure(r['created'] == ['J21'], r['created']))
T('ids', 'named-id-in-use', 'addJunction names W1, the ID of a wall: IDs are unique across collections, so it is '
  'rejected with FS-OPS-005.', ['1.5.2', '2.1.1', '7.1.1'], box(),
  req({'op': 'addJunction', 'id': 'W1', 'level': 'L1', 'position': ["3'", "3'"]}), 'rejected', [('FS-OPS-005', [])])
T('ids', 'named-id-retired', 'addElement names R9, which context.retired lists: FS-OPS-005.', ['1.5.2', '2.1.1'],
  box(), req({'op': 'addElement', 'collection': 'materials', 'id': 'R9', 'element': {'color': '#aabbcc'}}, retired=['R9']),
  'rejected', [('FS-OPS-005', [])])
T('ids', 'named-id-added-earlier', 'Two operations name the same new ID J9; the second is rejected.', ['1.5.2'], box(),
  req({'op': 'addJunction', 'id': 'J9', 'level': 'L1', 'position': ["3'", "3'"]},
      {'op': 'addJunction', 'id': 'J9', 'level': 'L1', 'position': ["4'", "3'"]}), 'rejected', [('FS-OPS-005', [])])
T('ids', 'composite-named-id-in-use', 'addOpening names O1, already an opening: FS-OPS-005.', ['1.5.2', '4.5.1'],
  door_on_south(FT), req({'op': 'addOpening', 'id': 'O1', 'wall': 'W2', 'at': 'centered', 'fill': 'T-door-36'}),
  'rejected', [('FS-OPS-005', [])])
T('ids', 'named-ids-kept', 'drawWall naming its wall "PARTY" and addOpening naming "HATCH": named IDs are used as '
  'given; only the junctions are minted.', ['1.5.1', '4.1.1', '4.5.1'], box(),
  req({'op': 'drawWall', 'id': 'PARTY', 'level': 'L1', 'from': ["2'", "7'"], 'to': ["8'", "7'"], 'type': 'WT'},
      {'op': 'addOpening', 'id': 'HATCH', 'wall': 'PARTY', 'at': 'centered', 'width': "2'", 'height': "2'", 'sill': "3'"}),
  check=lambda r, B: ensure(r['created'] == ['HATCH', 'J5', 'J6', 'PARTY'], r['created']))
T('ids', 'normalization-mints-after-the-batch', 'A wall drawn across the box mints J5, J6 and W5; normalization then '
  'mints the crossing junctions J7, J8 and the pieces W6 to W9 after them - never reusing a number the batch '
  'minted.', ['1.5.1', '5.2.1'], box(),
  req({'op': 'drawWall', 'level': 'L1', 'from': ["-2'", "6'"], 'to': ["14'", "6'"], 'type': 'WT'}),
  check=lambda r, B: ensure(r['created'] == ['J5', 'J6', 'J7', 'J8', 'W5', 'W6', 'W7', 'W8', 'W9'], r['created']))

T('ids', 'removed-ids-are-not-minted-again', 'The courtyard wall W7 is removed, then a wall drawn: W7 was in A, so '
  'minting skips it and the new wall is W8, although no wall in the working copy is numbered above 6.',
  ['1.5.1', '1.4.1'], courtyard(),
  req({'op': 'removeElement', 'id': 'W7'}, {'op': 'drawWall', 'level': 'L1', 'from': ["2'", "7'"], 'to': ["5'", "7'"], 'type': 'WT'}),
  check=lambda r, B: ensure(r['created'] == ['J8', 'J9', 'W8'] and r['removed'] == ['W7'], r['created']))
T('ids', 'named-and-removed-ids-are-not-minted-again', 'A junction named J9, removed again, then a junction minted: '
  'J9 was named earlier in the batch, so the new one is J10 - and replaying the resolved echo, which names every ID, '
  'mints the same.', ['1.5.1', '1.4.1'], box(),
  req({'op': 'addJunction', 'id': 'J9', 'level': 'L1', 'position': ["3'", "3'"]}, {'op': 'removeElement', 'id': 'J9'},
      {'op': 'drawWall', 'level': 'L1', 'from': ["-1'", "5'"], 'to': ["1'", "5'"], 'type': 'WT'}),
  check=lambda r, B: ensure(r['created'] == ['J10', 'J11', 'J12', 'W5', 'W6', 'W7'], r['created']))

# ================================================================================== primitives
T('primitives', 'add-element', 'addElement adds a material exactly as given, under the ID it names.', ['2.1.1'],
  box(), req({'op': 'addElement', 'collection': 'materials', 'id': 'OAK', 'element': {'name': 'White oak', 'color': '#c8a165'}}),
  check=lambda r, B: ensure(B['materials']['OAK'] == {'color': '#c8a165', 'name': 'White oak'}, B['materials']))
T('primitives', 'add-element-content-unchecked', 'addElement adds an opening on wall W5 before W5 exists; its content '
  'is not checked when it is added, and by the end of the batch W5 exists, so the batch commits.',
  ['2.1.1', '5.4.1'], box(),
  req({'op': 'addElement', 'collection': 'openings', 'element': {'wall': 'W5', 'offset': 0, 'width': FT, 'height': 3 * FT}},
      {'op': 'addJunction', 'level': 'L1', 'position': ["2'", "7'"]},
      {'op': 'addJunction', 'level': 'L1', 'position': ["5'", "7'"]},
      {'op': 'addWall', 'id': 'W5', 'level': 'L1', 'start': 'J5', 'end': 'J6', 'type': 'WT'}),
  check=lambda r, B: ensure(B['openings']['O1']['wall'] == 'W5', B['openings']))
T('primitives', 'add-element-invalid-content', 'addElement adds a level with no elevation or height: the operation '
  'does not check it, and the result fails the schema (FS-SCH-001), not the request (FS-OPS-001).',
  ['2.1.1', '1.2.3'], box(), req({'op': 'addElement', 'collection': 'levels', 'element': {'building': 'B1'}}),
  'rejected', [('FS-SCH-001', [])])
T('primitives', 'add-junction-as-add-element', 'addElement into junctions, with an ID minted.', ['2.1.2'], box(),
  req({'op': 'addElement', 'collection': 'junctions', 'element': {'level': 'L1', 'position': [FT, FT], 'name': 'Post'}}))
T('primitives', 'add-junction-shorthand', 'addJunction is addElement into junctions: the same document as the previous '
  'test, byte for byte, the name carried as every element may carry one.', ['2.1.2'], box(),
  req({'op': 'addJunction', 'level': 'L1', 'position': ["1'", "1'"], 'name': 'Post'}), same_as='add-junction-as-add-element')
T('primitives', 'add-wall-as-add-element', 'addElement into walls: a free-standing wall inside the room.', ['2.1.2'],
  box(junctions={'J5': J(2 * FT, 7 * FT), 'J6': J(5 * FT, 7 * FT)}),
  req({'op': 'addElement', 'collection': 'walls', 'element': {'level': 'L1', 'start': 'J5', 'end': 'J6', 'type': 'WT',
                                                              'justification': 'exteriorFace', 'name': 'Half wall'}}))
T('primitives', 'add-wall-shorthand', 'addWall is addElement into walls: the same document as the previous test.',
  ['2.1.2'], box(junctions={'J5': J(2 * FT, 7 * FT), 'J6': J(5 * FT, 7 * FT)}),
  req({'op': 'addWall', 'level': 'L1', 'start': 'J5', 'end': 'J6', 'type': 'WT', 'justification': 'exteriorFace',
       'name': 'Half wall'}), same_as='add-wall-as-add-element')
T('primitives', 'add-separator-as-add-element', 'addElement into separators: a line marking a paved area outside.', ['2.1.2'],
  box(junctions={'J5': J(16 * FT, 2 * FT), 'J6': J(19 * FT, 2 * FT)}),
  req({'op': 'addElement', 'collection': 'separators', 'element': {'level': 'L1', 'start': 'J5', 'end': 'J6'}}))
T('primitives', 'add-separator-shorthand', 'addSeparator is addElement into separators.', ['2.1.2'],
  box(junctions={'J5': J(16 * FT, 2 * FT), 'J6': J(19 * FT, 2 * FT)}),
  req({'op': 'addSeparator', 'level': 'L1', 'start': 'J5', 'end': 'J6'}), same_as='add-separator-as-add-element')
T('primitives', 'remove-missing', 'removeElement of an ID that does not exist: FS-OPS-003.', ['2.2.1', '7.1.1'], box(),
  req({'op': 'removeElement', 'id': 'W99'}), 'rejected', [('FS-OPS-003', [])])
T('primitives', 'remove-junction-blocked', 'Removing junction J1 without cascade is blocked by the two walls that end '
  'at it: FS-OPS-006 names J1, W1 and W4.', ['2.2.1', '7.1.1'], box(), req({'op': 'removeElement', 'id': 'J1'}),
  'rejected', [('FS-OPS-006', ['J1', 'W1', 'W4'])])
T('primitives', 'remove-wall-blocked', 'Removing wall W5 without cascade is blocked by its gate O1.', ['2.2.1'],
  garden(), req({'op': 'removeElement', 'id': 'W5'}), 'rejected', [('FS-OPS-006', ['O1', 'W5'])])
T('primitives', 'remove-level-blocked', 'Removing level L2 without cascade is blocked by everything on it - its '
  'junctions, walls, room and slab - and by the wall on L1 whose top is L2.', ['2.2.1'],
  upstairs(walls={'W1': W('J1', 'J2', top={'level': 'L2'})}), req({'op': 'removeElement', 'id': 'L2'}), 'rejected',
  [('FS-OPS-006', ['L2', 'K1', 'K2', 'K3', 'K4', 'R2', 'SL1', 'V1', 'V2', 'V3', 'V4', 'W1'])])
T('primitives', 'remove-building-blocked', 'Removing building B1 without cascade is blocked by its levels.', ['2.2.1'],
  upstairs(), req({'op': 'removeElement', 'id': 'B1'}), 'rejected', [('FS-OPS-006', ['B1', 'L1', 'L2'])])
T('primitives', 'remove-type-blocked', 'A type is blocked by every element that refers to it.', ['2.2.1'],
  door_on_south(FT), req({'op': 'removeElement', 'id': 'T-door-36'}), 'rejected', [('FS-OPS-006', ['O1', 'T-door-36'])])
T('primitives', 'remove-type-cascade-still-blocked', 'cascade does not apply to a type: removing WT with cascade true '
  'is still blocked by the four walls that use it.', ['2.2.1', '2.2.2'], box(),
  req({'op': 'removeElement', 'id': 'WT', 'cascade': True}), 'rejected', [('FS-OPS-006', ['W1', 'W2', 'W3', 'W4', 'WT'])])
T('primitives', 'remove-material-blocked', 'A material is blocked by the room that uses it as a finish and the wall '
  'type that uses it in a layer.', ['2.2.1'],
  box(materials={'GYP': {'color': '#f4f4f0'}}, rooms={'R1': R(6 * FT, 5 * FT, 'Living', wallFinish='GYP')},
      types={'WT': {'kind': 'wallType', 'layers': [{'thickness': T100, 'function': 'core', 'material': 'GYP'}]}}),
  req({'op': 'removeElement', 'id': 'GYP', 'cascade': True}), 'rejected', [('FS-OPS-006', ['GYP', 'R1', 'WT'])])
T('primitives', 'remove-asset-blocked', 'An asset is blocked by the material whose texture it is.', ['2.2.1'],
  box(materials={'TILE': {'texture': {'asset': 'A1', 'size': [12 * IN, 12 * IN]}}},
      assets={'A1': {'path': 'textures/tile.png', 'sha256': 'ab' * 32, 'mediaType': 'image/png'}}),
  req({'op': 'removeElement', 'id': 'A1'}), 'rejected', [('FS-OPS-006', ['A1', 'TILE'])])
T('primitives', 'remove-unused-type', 'A type nothing refers to is removed.', ['2.2.1'], box(),
  req({'op': 'removeElement', 'id': 'T-door-36'}), check=lambda r, B: ensure(r['removed'] == ['T-door-36'], r['removed']))
T('primitives', 'remove-nothing-depends-on', 'An opening, a slab and a room are removed; nothing blocks them and '
  'cascade changes nothing.', ['2.2.1', '2.2.2'], upstairs(),
  req({'op': 'removeElement', 'id': 'O1'}, {'op': 'removeElement', 'id': 'SL1', 'cascade': True},
      {'op': 'removeElement', 'id': 'R2', 'cascade': True}),
  check=lambda r, B: ensure(r['removed'] == ['O1', 'R2', 'SL1'], r['removed']))
T('primitives', 'remove-wall-cascade', 'Removing W5 with cascade takes its gate O1, and - as removing a wall always '
  'does - unsets the join at G2 that names it. Nothing else changes; G1 is left unused.', ['2.2.2'], garden(),
  req({'op': 'removeElement', 'id': 'W5', 'cascade': True}),
  check=lambda r, B: ensure(r['removed'] == ['O1', 'W5'] and 'join' not in B['junctions']['G2'], B['junctions']['G2']))
T('primitives', 'remove-wall-unsets-join', 'Removing W5 (its gate first) without cascade still unsets the join at G2 '
  'that names it.', ['2.2.1', '2.2.2'], garden(),
  req({'op': 'removeElement', 'id': 'O1'}, {'op': 'removeElement', 'id': 'W5'}),
  check=lambda r, B: ensure('join' not in B['junctions']['G2'], B['junctions']['G2']))
T('primitives', 'remove-junction-cascade', 'Removing G2 with cascade takes the two walls that end at it and, through '
  'W5, its gate - and nothing else: G1 and G3 stay.', ['2.2.2'], garden(),
  req({'op': 'removeElement', 'id': 'G2', 'cascade': True}),
  check=lambda r, B: ensure(r['removed'] == ['G2', 'O1', 'W5', 'W6'], r['removed']))
T('primitives', 'remove-level-cascade', 'Removing L2 with cascade takes its junctions, walls, room and slab, and the '
  'window on its wall V1; L1 is untouched.', ['2.2.2'], upstairs(),
  req({'op': 'removeElement', 'id': 'L2', 'cascade': True}),
  check=lambda r, B: ensure(r['removed'] == ['K1', 'K2', 'K3', 'K4', 'L2', 'O1', 'R2', 'SL1', 'V1', 'V2', 'V3', 'V4'], r['removed']))
second = upstairs(buildings={'B2': {'name': 'Garage'}})
second['levels']['L2']['building'] = 'B2'
T('primitives', 'remove-building-cascade', 'Removing building B2 with cascade takes its level L2 and everything L2 '
  'takes.', ['2.2.2'], second, req({'op': 'removeElement', 'id': 'B2', 'cascade': True}),
  check=lambda r, B: ensure(r['removed'] == ['B2', 'K1', 'K2', 'K3', 'K4', 'L2', 'O1', 'R2', 'SL1', 'V1', 'V2', 'V3', 'V4'], r['removed']))
T('primitives', 'remove-level-cascade-exactly', 'Removing L2 with cascade takes exactly what the table lists: the wall '
  'W1 on L1, whose top is level L2, is not taken, so it is left referring to a missing level and the result is '
  'invalid (FS-INV-002).', ['2.2.2', '1.2.3'], upstairs(walls={'W1': W('J1', 'J2', top={'level': 'L2'})}),
  req({'op': 'removeElement', 'id': 'L2', 'cascade': True}), 'rejected', [('FS-INV-002', ['W1'])])
T('primitives', 'set-property', 'setProperty sets a member.', ['2.3.1'], box(),
  req({'op': 'setProperty', 'id': 'R1', 'path': '/function', 'value': 'living'}),
  check=lambda r, B: ensure(B['rooms']['R1']['function'] == 'living', B['rooms']))
T('primitives', 'set-property-creates-objects', 'setProperty of /base/offset on a wall with no base creates the base '
  'object on the way.', ['2.3.1'], box(), req({'op': 'setProperty', 'id': 'W1', 'path': '/base/offset', 'value': 12800}),
  check=lambda r, B: ensure(B['walls']['W1']['base'] == {'offset': 12800}, B['walls']['W1']))
T('primitives', 'set-property-in-array', 'A path may index into an array: the wall type\'s first layer\'s thickness.',
  ['2.3.1'], box(), req({'op': 'setProperty', 'id': 'WT', 'path': '/layers/0/thickness', 'value': 150 * MM}),
  check=lambda r, B: ensure(B['types']['WT']['layers'][0]['thickness'] == 192000, B['types']['WT']))
T('primitives', 'set-property-missing-element', 'setProperty of an element that does not exist: FS-OPS-003.',
  ['2.3.1'], box(), req({'op': 'setProperty', 'id': 'R7', 'path': '/name', 'value': 'Den'}), 'rejected',
  [('FS-OPS-003', [])])
T('primitives', 'set-property-empty-path', 'setProperty with an empty path, which would replace the element itself: '
  'FS-OPS-003.', ['2.3.1'], box(), req({'op': 'setProperty', 'id': 'R1', 'path': '', 'value': {}}), 'rejected',
  [('FS-OPS-003', ['R1'])])
T('primitives', 'set-property-project', 'setProperty of $project.', ['2.3.1'], box(),
  req({'op': 'setProperty', 'id': '$project', 'path': '/description', 'value': 'A small house.'}),
  check=lambda r, B: ensure(B['project']['description'] == 'A small house.', B['project']))
T('primitives', 'set-property-site-creates-site', 'Setting a member of $site when the project has no site creates the '
  'site.', ['2.3.1', '1.6.1'], box(), req({'op': 'setProperty', 'id': '$site', 'path': '/trueNorth', 'value': -12500000}),
  check=lambda r, B: ensure(B['site'] == {'trueNorth': -12500000}, B.get('site')))
T('primitives', 'set-property-document', 'setProperty of $document addresses the document\'s top-level members other '
  'than its collections.', ['2.3.1'], box(),
  req({'op': 'setProperty', 'id': '$document', 'path': '/extensionsUsed', 'value': {'EXT_acoustics': '1.0'}},
      {'op': 'setProperty', 'id': '$document', 'path': '/extras/importer', 'value': 'conformance'}),
  check=lambda r, B: ensure(B['extensionsUsed'] == {'EXT_acoustics': '1.0'} and B['extras'] == {'importer': 'conformance'}, B))
T('primitives', 'set-property-document-collection', '$document does not address a collection: /walls is not one of '
  'its members (2.3), so FS-OPS-003.', ['2.3.1'], box(),
  req({'op': 'setProperty', 'id': '$document', 'path': '/walls', 'value': {}}), 'rejected', [('FS-OPS-003', [])])
T('primitives', 'unset-property', 'unsetProperty removes a member, so its default applies again: the room has no name.',
  ['2.3.1'], box(), req({'op': 'unsetProperty', 'id': 'R1', 'path': '/name'}),
  check=lambda r, B: ensure('name' not in B['rooms']['R1'], B['rooms']))
T('primitives', 'unset-property-missing-member', 'unsetProperty of a member the room does not have: FS-OPS-003.',
  ['2.3.1'], box(), req({'op': 'unsetProperty', 'id': 'R1', 'path': '/floorFinish'}), 'rejected',
  [('FS-OPS-003', ['R1'])])
T('primitives', 'unset-property-no-site', 'unsetProperty of $site when there is no site: the member is not there.',
  ['2.3.1'], box(), req({'op': 'unsetProperty', 'id': '$site', 'path': '/trueNorth'}), 'rejected', [('FS-OPS-003', [])])
T('primitives', 'unset-property-empty-path', 'unsetProperty with an empty path: FS-OPS-003.', ['2.3.1'], box(),
  req({'op': 'unsetProperty', 'id': 'W1', 'path': ''}), 'rejected', [('FS-OPS-003', ['W1'])])
T('primitives', 'move-junction-as-set-property', 'setProperty of a junction\'s /position.', ['2.4.1'], house(),
  req({'op': 'setProperty', 'id': 'J8', 'path': '/position', 'value': [12 * FT, 9 * FT]}))
T('primitives', 'move-junction', 'moveJunction is setProperty of /position: the same document as the previous test.',
  ['2.4.1'], house(), req({'op': 'moveJunction', 'id': 'J8', 'to': ["12'", "9'"]}), same_as='move-junction-as-set-property')
T('primitives', 'move-junction-not-a-junction', 'moveJunction names a wall: it resolves to no junction, FS-OPS-003.',
  ['2.4.1', '3.3.1'], house(), req({'op': 'moveJunction', 'id': 'W8', 'to': [0, 0]}), 'rejected', [('FS-OPS-003', [])])
T('primitives', 'references-in-primitives', 'A primitive may use the reference grammar: moveJunction of "end of '
  'wall between Kitchen and Pantry" (J8) to "1\' north of J8" - resolved against the document before the operation: '
  '[12\', 9\'].', ['3.3.1', '3.2.1', '2.4.1'], house(),
  req({'op': 'moveJunction', 'id': 'end of wall between Kitchen and Pantry', 'to': "1' north of J8"}),
  check=resolved_eq({'op': 'moveJunction', 'id': 'J8', 'to': [4681728, 3511296]}))
T('primitives', 'add-wall-references', 'addWall\'s start and end are references: "start of W2" is J2, "end of W2" '
  'is J3 - a second wall between the same junctions, which the result rejects (FS-INV-103).', ['2.1.2', '3.3.1'],
  box(), req({'op': 'addWall', 'level': 'L1', 'start': 'start of W2', 'end': 'end of W2', 'type': 'WT'}),
  'rejected', [('FS-INV-103', ['W2', 'W5'])])

T('primitives', 'shorthand-reference-missing', 'addWall\'s start is a reference, resolved before the wall is added: '
  'J99 names no junction, FS-OPS-003 - where addElement with the same content would be added and rejected at '
  'validation.', ['2.1.2', '3.3.1'], box(), req({'op': 'addWall', 'level': 'L1', 'start': 'J99', 'end': 'J1', 'type': 'WT'}),
  'rejected', [('FS-OPS-003', [])])
T('primitives', 'add-element-reference-missing', 'The same wall through addElement: its content is not resolved or '
  'checked when it is added, and the result fails validation, FS-INV-002.', ['2.1.1', '2.1.2'], box(),
  req({'op': 'addElement', 'collection': 'walls', 'element': {'level': 'L1', 'start': 'J99', 'end': 'J1', 'type': 'WT'}}),
  'rejected', [('FS-INV-002', ['W5'])])
T('primitives', 'value-is-not-resolved', 'setProperty\'s value is taken as given, never resolved: "1\'" stays a string, '
  'and the result fails the schema.', ['2.3.1', '1.2.3'], box(),
  req({'op': 'setProperty', 'id': 'W1', 'path': '/base/offset', 'value': "1'"}), 'rejected', [('FS-SCH-001', [])])
T('primitives', 'set-property-through-a-scalar', 'A path that leads through a string: FS-OPS-003.', ['2.3.1'], box(),
  req({'op': 'setProperty', 'id': 'R1', 'path': '/name/first', 'value': 'x'}), 'rejected', [('FS-OPS-003', ['R1'])])
T('primitives', 'set-property-missing-index', 'A path to an array index that does not exist: FS-OPS-003.', ['2.3.1'], box(),
  req({'op': 'setProperty', 'id': 'WT', 'path': '/layers/3/thickness', 'value': 1}), 'rejected', [('FS-OPS-003', ['WT'])])
T('primitives', 'set-property-not-a-pointer', 'A path that is not a JSON Pointer: FS-OPS-003.', ['2.3.1'], box(),
  req({'op': 'setProperty', 'id': 'R1', 'path': 'name', 'value': 'x'}), 'rejected', [('FS-OPS-003', ['R1'])])

# ================================================================================== references


def length_test(slug, description, xs, expected, covers=('3.1.1', '3.2.1')):
    """The Office moved by a vector of two lengths: its anchor (25', 5') moves by exactly them."""
    def check(r, B):
        last = r['resolved'][-1]
        ensure(last == {'op': 'setProperty', 'id': 'R2', 'path': '/anchor', 'value': [25 * FT + expected[0], 5 * FT + expected[1]]}, last)
    T('references', slug, description + ' (The Office is moved by them, as a vector.)', list(covers), two_rooms_apart(),
      req({'op': 'moveRoom', 'room': 'Office', 'by': xs}), check=check)


length_test('feet-inches-fraction', '12\'6-1/2" is 12 ft + 6 1/2 in = 4681728 + 211328 = 4893056; 6 1/2" (a space '
            'before the fraction) is 211328.', ["12'6-1/2\"", '6 1/2"'], [4893056, 211328])
length_test('fraction-and-negative', '3/4 in is 24384; -2\' is -780288.', ['3/4 in', "-2'"], [24384, -780288])
length_test('metric', '3.81 m and 381 cm are both 4876800.', ['3.81 m', '381cm'], [4876800, 4876800])
length_test('millimetres', '3810mm is 4876800; .5 m is 640000.', ['3810mm', '.5 m'], [4876800, 640000])
length_test('a-third-of-an-inch', '1/3" is 32512 / 3 = 10837.33..., rounded once to 10837; 2/3" is 21674.67..., '
            'rounded to 21675.', ['1/3"', '2/3"'], [10837, 21675])
length_test('ties-to-even', '1/65024 in is exactly half a base unit, rounded to the even 0; 3/65024" is 1.5, '
            'rounded to 2. (5/65024 in, 2.5, would also round to 2.)', ['1/65024 in', '3/65024"'], [0, 2])
length_test('letters-and-whitespace', 'Letters are case-insensitive and whitespace between tokens is ignored: '
            '"12 FT 6 IN" and " 2 \' - 6 \" " are 4876800 and 975360.', ['12 FT 6 IN', ' 2 \' - 6 " '], [4876800, 975360])
length_test('decimal-feet-and-inches', '1.5\' is 585216 and 6.25" is 203200.', ["1.5'", '6.25"'], [585216, 203200])
T('references', 'zero-denominator', 'A fraction with a zero denominator, 1/0": FS-OPS-012.', ['3.1.1', '7.1.1'],
  box(), req({'op': 'moveJunction', 'id': 'J1', 'to': ['1/0"', 0]}), 'rejected', [('FS-OPS-012', [])])
T('references', 'not-a-length', '"12 feet" does not match the grammar: FS-OPS-012.', ['3.1.1'], box(),
  req({'op': 'moveWall', 'wall': 'W3', 'by': '12 feet'}), 'rejected', [('FS-OPS-012', [])])
T('references', 'number-without-unit', 'A string length needs a unit: "3810" is FS-OPS-012 (an integer 3810 would be '
  'base units).', ['3.1.1'], box(), req({'op': 'moveWall', 'wall': 'W3', 'by': '3810'}), 'rejected', [('FS-OPS-012', [])])
T('references', 'fraction-of-a-foot', 'Feet take a decimal, not a fraction: 1 1/2\' is FS-OPS-012.', ['3.1.1'], box(),
  req({'op': 'moveWall', 'wall': 'W3', 'by': "1 1/2'"}), 'rejected', [('FS-OPS-012', [])])
T('references', 'point-from-toward', '"1\' from J1 toward Q", with Q at (3\', 4\'): one foot along a 3-4-5 '
  'line, (0.6\', 0.8\') = (234086.4, 312115.2), rounded once per coordinate to [234086, 312115].', ['3.2.1'],
  box(junctions={'Q': J(3 * FT, 4 * FT), 'P': J(0, 20 * FT)}),
  req({'op': 'moveJunction', 'id': 'P', 'to': "1' from J1 toward Q"}),
  check=resolved_eq({'op': 'moveJunction', 'id': 'P', 'to': [234086, 312115]}))
T('references', 'point-toward-itself', '"1\' from J1 toward J1" has no direction: two junctions with the same '
  'position are rejected with FS-OPS-003.', ['3.2.1'], box(junctions={'P': J(0, 20 * FT)}),
  req({'op': 'moveJunction', 'id': 'P', 'to': "1' from J1 toward J1"}), 'rejected', [('FS-OPS-003', [])])
T('references', 'point-direction-of', '"12\' east of J4" is J4\'s position plus [12\', 0]: [24\', 0].', ['3.2.1'],
  box(), req({'op': 'addJunction', 'level': 'L1', 'position': "12' east of J4"}),
  check=resolved_eq({'op': 'addJunction', 'id': 'J5', 'level': 'L1', 'position': [9363456, 0]}))
T('references', 'point-a-junction', 'A point may be a junction: drawWall to "end of W1" (J2) uses J2 itself.',
  ['3.2.1', '4.1.1'], box(), req({'op': 'drawWall', 'level': 'L1', 'from': ["-4'", "10'"], 'to': 'end of W1', 'type': 'WT'}),
  check=resolved_eq({'op': 'addJunction', 'id': 'J5', 'level': 'L1', 'position': [-1560576, 3901440]},
                    {'op': 'addWall', 'id': 'W5', 'level': 'L1', 'start': 'J5', 'end': 'J2', 'type': 'WT'}))
T('references', 'vector-string', 'moveRoom by "1\' 6\\" west": [-585216, 0].', ['3.2.1', '4.3.1'], two_rooms_apart(),
  req({'op': 'moveRoom', 'room': 'Office', 'by': "1' 6\" west"}),
  check=lambda r, B: ensure(pos(B, 'J5') == [20 * FT - 585216, 0], pos(B, 'J5')))
T('references', 'vector-array', 'A vector [dx, dy] of lengths: ["1\'", "-6\\""] is [390144, -195072].', ['3.2.1', '4.3.1'],
  two_rooms_apart(), req({'op': 'moveRoom', 'room': 'Office', 'by': ["1'", '-6"']}),
  check=lambda r, B: ensure(pos(B, 'J5') == [20 * FT + FT, -195072], pos(B, 'J5')))
T('references', 'point-not-a-point', '"somewhere nice" is neither a point form nor a junction reference: FS-OPS-012.',
  ['3.2.1', '7.1.1'], box(), req({'op': 'addJunction', 'level': 'L1', 'position': 'somewhere nice'}), 'rejected',
  [('FS-OPS-012', [])])
T('references', 'vector-not-a-vector', '"2\' up" names no direction: FS-OPS-012.', ['3.2.1'], two_rooms_apart(),
  req({'op': 'moveRoom', 'room': 'Office', 'by': "2' up"}), 'rejected', [('FS-OPS-012', [])])
T('references', 'point-junction-missing', '"3\' east of J9" names a junction that does not exist: FS-OPS-003.',
  ['3.2.1', '3.3.1'], box(), req({'op': 'addJunction', 'level': 'L1', 'position': "3' east of J9"}), 'rejected',
  [('FS-OPS-003', [])])
T('references', 'room-name-ignores-case', 'A room name is compared ignoring case: "kitchen" is R1.', ['3.3.1', '4.6.1'],
  house(materials={'OAK': {'color': '#c8a165'}}),
  req({'op': 'setRoomFinish', 'room': 'kitchen', 'surface': 'floor', 'material': 'OAK'}),
  check=resolved_eq({'op': 'setProperty', 'id': 'R1', 'path': '/floorFinish', 'value': 'OAK'}))
T('references', 'room-name-ambiguous', 'Two rooms named Kitchen: the name matches both, FS-OPS-004 lists them.',
  ['3.3.1', '7.1.1'], house(rooms={'R2': R(6 * FT, 10 * FT, 'kitchen')}),
  req({'op': 'resizeRoom', 'room': 'Kitchen', 'side': 'east', 'by': K}), 'rejected', [('FS-OPS-004', ['R1', 'R2'])])
T('references', 'id-and-name-match', 'A room named "R3" and the room whose ID is R3: the string matches both, so it '
  'is ambiguous.', ['3.3.1'], house(rooms={'R2': R(6 * FT, 10 * FT, 'R3')}),
  req({'op': 'setProperty', 'id': 'R3', 'path': '/function', 'value': 'living'}), 'rejected', [('FS-OPS-004', ['R2', 'R3'])])
T('references', 'name-matches-nothing', '"Garage" names no room: FS-OPS-003.', ['3.3.1'], house(),
  req({'op': 'resizeRoom', 'room': 'Garage', 'side': 'east', 'by': K}), 'rejected', [('FS-OPS-003', [])])
T('references', 'side-wall-of', '"south wall of Dining" is W6.', ['3.3.1', '3.4.1'], house(),
  req({'op': 'setProperty', 'id': 'south wall of Dining', 'path': '/name', 'value': 'Dining south'}),
  check=first_resolved({'op': 'setProperty', 'id': 'W6', 'path': '/name', 'value': 'Dining south'}))
T('references', 'side-of-two-walls', 'The Dining room\'s west side is two walls, W8 and W9: "west wall of Dining" is '
  'ambiguous, FS-OPS-004.', ['3.3.1', '3.4.1'], house(),
  req({'op': 'setProperty', 'id': 'west wall of Dining', 'path': '/name', 'value': 'x'}), 'rejected',
  [('FS-OPS-004', ['W8', 'W9'])])
T('references', 'no-separator-on-that-side', 'The Kitchen\'s east side is a wall: "east separator of Kitchen" matches '
  'nothing.', ['3.3.1'], house(), req({'op': 'removeElement', 'id': 'east separator of Kitchen'}), 'rejected',
  [('FS-OPS-003', [])])
T('references', 'wall-between', '"wall between Kitchen and Pantry" is W10.', ['3.3.1', '3.4.1'], house(),
  req({'op': 'setProperty', 'id': 'wall between pantry and KITCHEN', 'path': '/name', 'value': 'Pantry wall'}),
  check=first_resolved({'op': 'setProperty', 'id': 'W10', 'path': '/name', 'value': 'Pantry wall'}))
T('references', 'wall-between-rooms-apart', 'The Living room and the Office share no wall: FS-OPS-003.', ['3.3.1'],
  two_rooms_apart(), req({'op': 'removeWall', 'wall': 'wall between Living and Office'}), 'rejected', [('FS-OPS-003', [])])
T('references', 'start-of-wall', '"start of wall between Kitchen and Dining" is J7, the start of W8.', ['3.3.1'],
  house(), req({'op': 'setProperty', 'id': 'start of wall between Kitchen and Dining', 'path': '/name', 'value': 'T'}),
  check=first_resolved({'op': 'setProperty', 'id': 'J7', 'path': '/name', 'value': 'T'}))
T('references', 'separator-selectors', 'In an open plan, "east separator of Kitchen" and "separator between Dining and '
  'Kitchen" are both S1.', ['3.3.1', '3.4.1'], open_plan(),
  req({'op': 'setProperty', 'id': 'east separator of Kitchen', 'path': '/name', 'value': 'Counter line'},
      {'op': 'unsetProperty', 'id': 'separator between Dining and Kitchen', 'path': '/name'}),
  check=lambda r, B: ensure([p['id'] for p in r['resolved']] == ['S1', 'S1'], r['resolved']))
T('references', 'selector-of-wrong-kind', 'addOpening\'s wall is "Kitchen", which names a room, not a wall: '
  'FS-OPS-003.', ['3.3.1', '4.5.1'], house(),
  req({'op': 'addOpening', 'wall': 'Kitchen', 'at': 'centered', 'fill': 'T-door-36'}), 'rejected', [('FS-OPS-003', [])])
T('references', 'diagonal-wall-is-east', 'A wall at exactly 45 degrees belongs to the side counter-clockwise before '
  'it: the chamfer W3, facing north-east, is on the east side with W4, so "east wall of Study" is ambiguous.',
  ['3.3.1', '3.4.1'], chamfered(), req({'op': 'setProperty', 'id': 'east wall of Study', 'path': '/name', 'value': 'x'}),
  'rejected', [('FS-OPS-004', ['W3', 'W4'])])
T('references', 'diagonal-wall-not-north', '...and is not on the north side: "north wall of Study" is W2 alone.',
  ['3.3.1', '3.4.1'], chamfered(), req({'op': 'setProperty', 'id': 'north wall of Study', 'path': '/name', 'value': 'North'}),
  check=first_resolved({'op': 'setProperty', 'id': 'W2', 'path': '/name', 'value': 'North'}))
T('references', 'faces-of-a-crossed-level', 'The first operation moves J8 so that W8 crosses the north wall; the '
  'second asks for "north wall of Kitchen" on that working copy. Its level breaks Core 5.3: FS-OPS-007 names L1.',
  ['3.4.1', '7.1.1'], house(),
  req({'op': 'moveJunction', 'id': 'J8', 'to': ["13'", "13'"]},
      {'op': 'setProperty', 'id': 'north wall of Kitchen', 'path': '/name', 'value': 'x'}), 'rejected',
  [('FS-OPS-007', ['L1'])])
T('references', 'faces-anchor-outside', 'The first operation moves the Kitchen\'s anchor outside the house; "north '
  'wall of Kitchen" then finds the anchor in no bounded face: FS-OPS-007.', ['3.4.1'], house(),
  req({'op': 'setProperty', 'id': 'R1', 'path': '/anchor', 'value': [-FT, -FT]},
      {'op': 'resizeRoom', 'room': 'Kitchen', 'side': 'north', 'by': K}), 'rejected', [('FS-OPS-007', ['L1'])])
T('references', 'faces-coincident-junctions', 'Two junctions at one position (Core 5.1) leave a level with no faces '
  'to give: FS-OPS-007.', ['3.4.1'], house(),
  req({'op': 'addJunction', 'level': 'L1', 'position': 'J8'}, {'op': 'moveRoom', 'room': 'Pantry', 'by': "1' north"}),
  'rejected', [('FS-OPS-007', ['L1'])])
T('references', 'faces-anchor-on-a-wall', 'An anchor on a location line is in no face.', ['3.4.1'], house(),
  req({'op': 'setProperty', 'id': 'R3', 'path': '/anchor', 'value': [24 * FT, 6 * FT]},
      {'op': 'removeWall', 'wall': 'wall between Kitchen and Dining', 'keep': 'Kitchen'}), 'rejected',
  [('FS-OPS-007', ['L1'])])

oblique = box(junctions={'J5': J(2 * FT, 2 * FT), 'J6': J(5 * FT, 7 * FT)}, walls={'W5': W('J5', 'J6')})
T('references', 'centered-on-an-oblique-wall', 'A 30-inch opening centred on W5, from (2\', 2\') to (5\', 7\'): '
  'L = sqrt(34) ft = 2274910.90 base units, so the near edge is at (L - 975360) / 2 = 649775.45, rounded to '
  '649775.', ['3.5.1', '4.5.1'], oblique,
  req({'op': 'addOpening', 'wall': 'W5', 'at': 'centered', 'width': '30"', 'height': "6' 8\""}),
  check=resolved_eq({'op': 'addElement', 'collection': 'openings', 'id': 'O1',
                     'element': {'wall': 'W5', 'offset': 649775, 'width': 975360, 'height': DOOR_H}}))
T('references', 'from-start', '"18\\" from start" puts the near edge 18 in from the wall\'s start: 585216.', ['3.5.1'],
  box(), req({'op': 'addOpening', 'wall': 'W2', 'at': '18" from start', 'fill': 'T-door-36'}),
  check=lambda r, B: ensure(B['openings']['O1']['offset'] == 585216, B['openings']))
T('references', 'from-end', '"2\' from end" on W2 (12\'): L - 2\' - 36" = 4681728 - 780288 - 1170432 = 2731008.',
  ['3.5.1'], box(), req({'op': 'addOpening', 'wall': 'W2', 'at': "2' from end", 'fill': 'T-door-36'}),
  check=lambda r, B: ensure(B['openings']['O1']['offset'] == 2731008, B['openings']))
T('references', 'from-end-oblique', '"1\' from end" on the oblique W5: sqrt(34) ft - 1\' - 30" = 909406.90, '
  'rounded to 909407.', ['3.5.1'], oblique,
  req({'op': 'addOpening', 'wall': 'W5', 'at': "1' from end", 'width': '30"', 'height': "6'"}),
  check=lambda r, B: ensure(B['openings']['O1']['offset'] == 909407, B['openings']))
T('references', 'position-length-and-integer', 'A position may be a length or an integer offset.', ['3.5.1', '4.5.1'],
  box(), req({'op': 'addOpening', 'wall': 'W2', 'at': "3'", 'fill': 'T-door-36'},
             {'op': 'addOpening', 'wall': 'W4', 'at': 128000, 'fill': 'T-door-36'}),
  check=lambda r, B: ensure(B['openings']['O1']['offset'] == 3 * FT and B['openings']['O2']['offset'] == 128000, B['openings']))

# ================================================================================== composites
T('composites', 'draw-wall', 'drawWall between two new points: two junctions are added at the points, then the wall.',
  ['4.1.1'], box(), req({'op': 'drawWall', 'level': 'L1', 'from': ["2'", "7'"], 'to': ["5'", "7'"], 'type': 'WT', 'name': 'Half wall'}),
  check=resolved_eq({'op': 'addJunction', 'id': 'J5', 'level': 'L1', 'position': [780288, 2731008]},
                    {'op': 'addJunction', 'id': 'J6', 'level': 'L1', 'position': [1950720, 2731008]},
                    {'op': 'addWall', 'id': 'W5', 'level': 'L1', 'start': 'J5', 'end': 'J6', 'type': 'WT', 'name': 'Half wall'}))
T('composites', 'draw-wall-reuses-a-junction', 'drawWall from [0, 0], where J1 already is: J1 is used, and only the '
  'other end is added.', ['4.1.1'], box(),
  req({'op': 'drawWall', 'level': 'L1', 'from': [0, 0], 'to': ["-3'", "-3'"], 'type': 'WT'}),
  check=resolved_eq({'op': 'addJunction', 'id': 'J5', 'level': 'L1', 'position': [-1170432, -1170432]},
                    {'op': 'addWall', 'id': 'W5', 'level': 'L1', 'start': 'J1', 'end': 'J5', 'type': 'WT'}))
T('composites', 'draw-wall-every-member', 'drawWall passes every wall member it is given to addWall.', ['4.1.1'],
  upstairs(), req({'op': 'drawWall', 'id': 'W9', 'level': 'L1', 'from': "2' north of J1", 'to': "2' north of J4",
                   'type': 'WT', 'layers': [{'thickness': 64000, 'function': 'core'}], 'justification': 'interiorFace',
                   'base': {'offset': 12800}, 'top': {'level': 'L2'}, 'name': 'Low wall', 'extras': {'source': 'sketch'}}),
  check=lambda r, B: ensure(r['resolved'][-1] == {'op': 'addWall', 'id': 'W9', 'level': 'L1', 'start': 'J5', 'end': 'J6',
                                                   'type': 'WT', 'layers': [{'thickness': 64000, 'function': 'core'}],
                                                   'justification': 'interiorFace', 'base': {'offset': 12800},
                                                   'top': {'level': 'L2'}, 'name': 'Low wall', 'extras': {'source': 'sketch'}}, r['resolved'][-1]))
T('composites', 'draw-separator', 'An open kitchen: a separator drawn across the room between two new junctions on '
  'its walls (which normalization splits there), and a room added in the new face.', ['4.1.1', '4.6.1'],
  box(), req({'op': 'drawSeparator', 'level': 'L1', 'from': ["8'", 0], 'to': ["8'", "10'"]},
             {'op': 'addRoom', 'level': 'L1', 'at': ["10'", "5'"], 'name': 'Kitchen', 'function': 'kitchen'}),
  check=lambda r, B: ensure(r['resolved'][2] == {'op': 'addSeparator', 'id': 'S1', 'level': 'L1', 'start': 'J5', 'end': 'J6'}, r['resolved']))
T('composites', 'move-wall', 'moveWall moves a wall towards its left (exterior) side for a positive "by": the north '
  'wall W2 (J2 -> J3, left is north) 1\' north.', ['4.2.1'], box(), req({'op': 'moveWall', 'wall': 'W2', 'by': "1'"}),
  check=resolved_eq({'op': 'moveJunction', 'id': 'J2', 'to': [0, 11 * FT]},
                    {'op': 'moveJunction', 'id': 'J3', 'to': [12 * FT, 11 * FT]}))
T('composites', 'move-wall-negative', 'A negative "by" moves the wall to its right: the north wall 1\' south, into '
  'the room.', ['4.2.1'], box(), req({'op': 'moveWall', 'wall': 'north wall of Living', 'by': "-1'"}),
  check=resolved_eq({'op': 'moveJunction', 'id': 'J2', 'to': [0, 9 * FT]},
                    {'op': 'moveJunction', 'id': 'J3', 'to': [12 * FT, 9 * FT]}))
T('composites', 'move-wall-toward', 'With "toward", the sign of "by" is chosen so the wall moves into that room: '
  'W10 (J2 -> J8, left is north, into the Pantry) moved toward the Kitchen goes south, whatever the sign given.',
  ['4.2.1'], house(), req({'op': 'moveWall', 'wall': 'W10', 'by': "1'", 'toward': 'Kitchen'}),
  check=resolved_eq({'op': 'moveJunction', 'id': 'J2', 'to': [0, 7 * FT]},
                    {'op': 'moveJunction', 'id': 'J8', 'to': [12 * FT, 7 * FT]}))
diag_wall = box(junctions={'J5': J(2 * FT, 2 * FT), 'J6': J(5 * FT, 6 * FT)}, walls={'W5': W('J5', 'J6')})
T('composites', 'move-wall-oblique', 'An oblique wall from (2\', 2\') to (5\', 6\') - a 3-4-5 triangle - moved 1 m '
  'to its left: the unit left normal is (-4/5, 3/5), so the displacement is [-1024000, 768000].', ['4.2.1'], diag_wall,
  req({'op': 'moveWall', 'wall': 'W5', 'by': '1 m'}),
  check=resolved_eq({'op': 'moveJunction', 'id': 'J5', 'to': [2 * FT - 1024000, 2 * FT + 768000]},
                    {'op': 'moveJunction', 'id': 'J6', 'to': [5 * FT - 1024000, 6 * FT + 768000]}))
irr_wall = box(junctions={'J5': J(2 * FT, 2 * FT), 'J6': J(5 * FT, 7 * FT)}, walls={'W5': W('J5', 'J6')})
T('composites', 'move-wall-rounding', 'W5 from (2\', 2\') to (5\', 7\') moved 6" to its left: the displacement '
  '195072 * (-5, 3) / sqrt(34) = (-167272.86, 100363.72) is rounded once per coordinate to [-167273, 100364].',
  ['4.2.1', '1.3.2'], irr_wall, req({'op': 'moveWall', 'wall': 'W5', 'by': '6"'}),
  check=resolved_eq({'op': 'moveJunction', 'id': 'J5', 'to': [2 * FT - 167273, 2 * FT + 100364]},
                    {'op': 'moveJunction', 'id': 'J6', 'to': [5 * FT - 167273, 7 * FT + 100364]}))
T('composites', 'move-wall-toward-a-room-not-beside-it', 'moveWall toward the Pantry, which W8 does not bound: '
  'FS-OPS-008.', ['4.2.1', '7.1.1'], house(), req({'op': 'moveWall', 'wall': 'W8', 'by': "1'", 'toward': 'Pantry'}),
  'rejected', [('FS-OPS-008', ['W8'])])
T('composites', 'move-room', 'moveRoom moves every junction on the Office\'s outer cycle, by ID, and its anchor.',
  ['4.3.1'], two_rooms_apart(), req({'op': 'moveRoom', 'room': 'Office', 'by': "2' west"}),
  check=resolved_eq({'op': 'moveJunction', 'id': 'J5', 'to': [18 * FT, 0]},
                    {'op': 'moveJunction', 'id': 'J6', 'to': [18 * FT, 10 * FT]},
                    {'op': 'moveJunction', 'id': 'J7', 'to': [28 * FT, 10 * FT]},
                    {'op': 'moveJunction', 'id': 'J8', 'to': [28 * FT, 0]},
                    {'op': 'setProperty', 'id': 'R2', 'path': '/anchor', 'value': [23 * FT, 5 * FT]}))
T('composites', 'move-room-stretches-neighbours', 'Moving the Pantry 1\'6" north moves the four junctions of its '
  'cycle - J2 and J8 included, which it shares with the Kitchen - so the Kitchen grows and the Dining room changes '
  'shape.', ['4.3.1'], house(), req({'op': 'moveRoom', 'room': 'Pantry', 'by': "1' 6\" north"}),
  check=lambda r, B: ensure([p['id'] for p in r['resolved']] == ['J2', 'J3', 'J4', 'J8', 'R2'], r['resolved']))


def kitchen_wider(r, B):
    ensure(r['resolved'] == [
        {'op': 'addJunction', 'id': 'J9', 'level': 'L1', 'position': [14 * FT, 8 * FT]},
        {'op': 'setProperty', 'id': 'W8', 'path': '/end', 'value': 'J9'},
        {'op': 'addWall', 'id': 'W11', 'level': 'L1', 'start': 'J8', 'end': 'J9', 'type': 'WT'},
        {'op': 'moveJunction', 'id': 'J7', 'to': [14 * FT, 0]},
        {'op': 'setProperty', 'id': 'R1', 'path': '/anchor', 'value': [7 * FT, 4 * FT]},
        {'op': 'setProperty', 'id': 'R3', 'path': '/anchor', 'value': [19 * FT, 6 * FT]}], r['resolved'])
    ensure(pos(B, 'J8') == [12 * FT, 8 * FT], 'J8 stays for the Pantry')


T('composites', 'make-the-kitchen-two-feet-wider', '"Make the kitchen 2 ft wider": resizeRoom east by 2\'. The '
  'Kitchen\'s east side is W8 alone (J7 -> J8). At J7 the side does not continue, so J7 moves 2\' east; at J8 it '
  'continues north as the Pantry\'s W9, so J8 stays and the run is reconnected to a new junction J9 at (14\', 8\') '
  'by a jog W11 with W8\'s type. The Kitchen\'s anchor and the Dining room\'s - across W8 - move 1\' east.',
  ['4.4.1', '1.4.1'], house(), req({'op': 'resizeRoom', 'room': 'Kitchen', 'side': 'east', 'by': "2'"}),
  check=kitchen_wider)
T('composites', 'make-the-dining-room-wider', 'resizeRoom of the Dining room east by 2\': both ends of its east side '
  'W5 are corners that do not continue, so both move, and the walls meeting them stretch.', ['4.4.1'], house(),
  req({'op': 'resizeRoom', 'room': 'Dining', 'side': 'east', 'by': K}),
  check=resolved_eq({'op': 'moveJunction', 'id': 'J5', 'to': [26 * FT, 12 * FT]},
                    {'op': 'moveJunction', 'id': 'J6', 'to': [26 * FT, 0]},
                    {'op': 'setProperty', 'id': 'R3', 'path': '/anchor', 'value': [19 * FT, 6 * FT]}))
T('composites', 'resize-a-side-of-two-walls', 'The Dining room\'s west side is a run of two walls, W9 and W8 (J4 -> J8 '
  '-> J7 as its cycle walks them). Resizing it 2\' west moves all three junctions; the anchors of the Dining room '
  'and of both rooms across the run - Kitchen and Pantry - move 1\' west.', ['4.4.1'], house(),
  req({'op': 'resizeRoom', 'room': 'Dining', 'side': 'west', 'by': K}),
  check=resolved_eq({'op': 'moveJunction', 'id': 'J4', 'to': [10 * FT, 12 * FT]},
                    {'op': 'moveJunction', 'id': 'J7', 'to': [10 * FT, 0]},
                    {'op': 'moveJunction', 'id': 'J8', 'to': [10 * FT, 8 * FT]},
                    {'op': 'setProperty', 'id': 'R3', 'path': '/anchor', 'value': [17 * FT, 6 * FT]},
                    {'op': 'setProperty', 'id': 'R1', 'path': '/anchor', 'value': [5 * FT, 4 * FT]},
                    {'op': 'setProperty', 'id': 'R2', 'path': '/anchor', 'value': [5 * FT, 10 * FT]}))
T('composites', 'resize-inwards', 'A negative "by" moves the side inwards: the Dining room 2\' narrower.', ['4.4.1'],
  house(), req({'op': 'resizeRoom', 'room': 'Dining', 'side': 'east', 'by': "-2'"}),
  check=lambda r, B: ensure(pos(B, 'J5') == [22 * FT, 12 * FT] and B['rooms']['R3']['anchor'] == [17 * FT, 6 * FT], B['rooms']))
T('composites', 'resize-anchor-ties-to-even', 'Resizing by 3 base units moves the anchors by 3 / 2 = 1.5, rounded to '
  'the even 2; by 1 base unit, 0.5 rounds to 0.', ['4.4.1'], house(),
  req({'op': 'resizeRoom', 'room': 'Dining', 'side': 'east', 'by': 3},
      {'op': 'resizeRoom', 'room': 'Dining', 'side': 'east', 'by': 1}),
  check=lambda r, B: ensure(B['rooms']['R3']['anchor'] == [18 * FT + 2, 6 * FT] and pos(B, 'J5') == [24 * FT + 4, 12 * FT], B['rooms']['R3']))
T('composites', 'resize-a-separator-side', 'In the open plan the Kitchen\'s east side is the separator S1, continuing '
  'north as the wall W9: the jog at J8 is a separator, like the run edge it adjoins.', ['4.4.1'], open_plan(),
  req({'op': 'resizeRoom', 'room': 'Kitchen', 'side': 'east', 'by': K}),
  check=lambda r, B: ensure(r['resolved'][2] == {'op': 'addSeparator', 'id': 'S2', 'level': 'L1', 'start': 'J8', 'end': 'J9'}, r['resolved']))
T('composites', 'resize-missing-side', 'The triangle has no north side: FS-OPS-008.', ['4.4.1', '7.1.1'], triangle(),
  req({'op': 'resizeRoom', 'room': 'Nook', 'side': 'north', 'by': K}), 'rejected', [('FS-OPS-008', ['R1'])])
T('composites', 'resize-oblique-side', 'The triangle\'s east side is its hypotenuse, which faces north-east, not '
  'exactly east: FS-OPS-008.', ['4.4.1'], triangle(),
  req({'op': 'resizeRoom', 'room': 'Nook', 'side': 'east', 'by': K}), 'rejected', [('FS-OPS-008', ['R1'])])
T('composites', 'resize-jogged-side', 'The L-shaped room\'s east side is two walls on two lines: FS-OPS-008.',
  ['4.4.1'], l_shaped(), req({'op': 'resizeRoom', 'room': 'Den', 'side': 'east', 'by': K}), 'rejected',
  [('FS-OPS-008', ['R1'])])
T('composites', 'resize-both-ends-continue', 'The box with walls continuing its north side both ways: resizing north '
  'makes a jog at each end, P0 first, and moves no junction.', ['4.4.1'],
  box(junctions={'J5': J(-4 * FT, 10 * FT), 'J6': J(16 * FT, 10 * FT)}, walls={'W5': W('J5', 'J2'), 'W6': W('J3', 'J6')}),
  req({'op': 'resizeRoom', 'room': 'Living', 'side': 'north', 'by': "1'"}),
  check=resolved_eq({'op': 'addJunction', 'id': 'J7', 'level': 'L1', 'position': [12 * FT, 11 * FT]},
                    {'op': 'setProperty', 'id': 'W2', 'path': '/end', 'value': 'J7'},
                    {'op': 'addWall', 'id': 'W7', 'level': 'L1', 'start': 'J3', 'end': 'J7', 'type': 'WT'},
                    {'op': 'addJunction', 'id': 'J8', 'level': 'L1', 'position': [0, 11 * FT]},
                    {'op': 'setProperty', 'id': 'W2', 'path': '/start', 'value': 'J8'},
                    {'op': 'addWall', 'id': 'W8', 'level': 'L1', 'start': 'J2', 'end': 'J8', 'type': 'WT'},
                    {'op': 'setProperty', 'id': 'R1', 'path': '/anchor', 'value': [6 * FT, 5 * FT + FT // 2]}))
T('composites', 'add-a-door-between-kitchen-and-dining', '"Add a 36-inch door centered between the kitchen and dining '
  'room": the wall between them is W8, 8\' long, so the door\'s near edge is at (3121152 - 1170432) / 2 = 975360. '
  'Its width comes from the fill type.', ['4.5.1', '3.5.1', '3.3.1'], house(),
  req({'op': 'addOpening', 'wall': 'wall between Kitchen and Dining', 'at': 'centered', 'fill': 'T-door-36'}),
  check=resolved_eq({'op': 'addElement', 'collection': 'openings', 'id': 'O1',
                     'element': {'wall': 'W8', 'offset': 975360, 'fill': 'T-door-36'}}))
T('composites', 'add-opening-own-width', 'An opening with its own width and height and no fill: centred by its own '
  'width, 30" on a 12\' wall: (4681728 - 975360) / 2 = 1853184.', ['4.5.1'], box(),
  req({'op': 'addOpening', 'wall': 'W2', 'at': 'centered', 'width': '30"', 'height': "4'", 'sill': "3'", 'name': 'Window'}),
  check=lambda r, B: ensure(B['openings']['O1'] == {'height': 4 * FT, 'name': 'Window', 'offset': 1853184, 'sill': 3 * FT,
                                                     'wall': 'W2', 'width': 975360}, B['openings']))
T('composites', 'add-opening-width-overrides-fill', 'A width member overrides the fill\'s: a 36" door type hung in a '
  '32" opening is centred by 32".', ['4.5.1'], box(),
  req({'op': 'addOpening', 'wall': 'W2', 'at': 'centered', 'fill': 'T-door-36', 'width': '32"', 'hinge': 'end', 'swing': 'left'}),
  check=lambda r, B: ensure(B['openings']['O1']['offset'] == (4681728 - 32 * IN) // 2, B['openings']))
T('composites', 'add-opening-without-width', 'An opening with neither a width nor a fill: FS-OPS-003.', ['4.5.1'], box(),
  req({'op': 'addOpening', 'wall': 'W2', 'at': 0, 'height': "6' 8\""}), 'rejected', [('FS-OPS-003', [])])
T('composites', 'add-opening-fill-without-width', 'An opening whose fill, a window type, gives no width: FS-OPS-003.',
  ['4.5.1'], box(types={'WIN': {'kind': 'windowType', 'height': 4 * FT}}),
  req({'op': 'addOpening', 'wall': 'W2', 'at': 'centered', 'fill': 'WIN'}), 'rejected', [('FS-OPS-003', [])])
T('composites', 'move-opening', 'moveOpening is setProperty of the offset: the door moved to 2\' from its wall\'s '
  'end.', ['4.5.1', '3.5.1'], door_on_south(FT), req({'op': 'moveOpening', 'opening': 'O1', 'at': "2' from end"}),
  check=resolved_eq({'op': 'setProperty', 'id': 'O1', 'path': '/offset', 'value': 12 * FT - 2 * FT - DOOR_W}))
T('composites', 'add-room', 'addRoom names the face the Pantry\'s walls enclose, which has no room yet.', ['4.6.1'],
  dict(house(), rooms={'R1': R(6 * FT, 4 * FT, 'Kitchen'), 'R3': R(18 * FT, 6 * FT, 'Dining')}),
  req({'op': 'addRoom', 'level': 'L1', 'at': ["6'", "10'"], 'name': 'Pantry', 'function': 'storage', 'floorFinish': 'TILE'},
      {'op': 'addElement', 'collection': 'materials', 'id': 'TILE', 'element': {'color': '#e0ddd5'}}),
  check=resolved_eq({'op': 'addElement', 'collection': 'rooms', 'id': 'R4',
                     'element': {'level': 'L1', 'anchor': [6 * FT, 10 * FT], 'name': 'Pantry', 'function': 'storage', 'floorFinish': 'TILE'}},
                    {'op': 'addElement', 'collection': 'materials', 'id': 'TILE', 'element': {'color': '#e0ddd5'}}))
T('composites', 'set-room-finish', 'setRoomFinish of each surface is setProperty of /wallFinish, /floorFinish and '
  '/ceilingFinish.', ['4.6.1'], house(materials={'OAK': {}, 'PAINT': {}, 'PLASTER': {}}),
  req({'op': 'setRoomFinish', 'room': 'Dining', 'surface': 'wall', 'material': 'PAINT'},
      {'op': 'setRoomFinish', 'room': 'Dining', 'surface': 'floor', 'material': 'OAK'},
      {'op': 'setRoomFinish', 'room': 'Dining', 'surface': 'ceiling', 'material': 'PLASTER'}),
  check=resolved_eq({'op': 'setProperty', 'id': 'R3', 'path': '/wallFinish', 'value': 'PAINT'},
                    {'op': 'setProperty', 'id': 'R3', 'path': '/floorFinish', 'value': 'OAK'},
                    {'op': 'setProperty', 'id': 'R3', 'path': '/ceilingFinish', 'value': 'PLASTER'}))
T('composites', 'remove-wall-keep', '"Open up the kitchen into the dining room": removeWall of the wall between them, '
  'keeping the Kitchen. The Dining room is removed first, then the wall with cascade - taking its door.',
  ['4.7.1'], house(openings={'O1': {'wall': 'W8', 'offset': 975360, 'fill': 'T-door-36'}}),
  req({'op': 'removeWall', 'wall': 'wall between Kitchen and Dining', 'keep': 'Kitchen'}),
  check=lambda r, B: ensure(r['resolved'] == [{'op': 'removeElement', 'id': 'R3'}, {'op': 'removeElement', 'id': 'W8', 'cascade': True}]
                            and r['removed'] == ['O1', 'R3', 'W8'], r['resolved']))
T('composites', 'remove-wall-without-keep', 'removeWall of a wall with a room on each side and no keep: FS-OPS-008.',
  ['4.7.1', '7.1.1'], house(), req({'op': 'removeWall', 'wall': 'W8'}), 'rejected', [('FS-OPS-008', ['W8'])])
T('composites', 'remove-wall-keep-another-room', 'keep names the Pantry, which is on neither side of W8: FS-OPS-008.',
  ['4.7.1'], house(), req({'op': 'removeWall', 'wall': 'W8', 'keep': 'Pantry'}), 'rejected', [('FS-OPS-008', ['W8'])])
T('composites', 'remove-wall-one-room', 'A garden wall with no room on either side is removed with its gate; no room '
  'is removed and keep is not needed.', ['4.7.1'], garden(), req({'op': 'removeWall', 'wall': 'W5'}),
  check=resolved_eq({'op': 'removeElement', 'id': 'W5', 'cascade': True}))

def kitchen_from_the_south(r, B):
    ensure(r['resolved'] == [
        {'op': 'addJunction', 'id': 'J9', 'level': 'L1', 'position': [12 * FT, FT]},
        {'op': 'setProperty', 'id': 'W7', 'path': '/start', 'value': 'J9'},
        {'op': 'moveJunction', 'id': 'J1', 'to': [0, FT]},
        {'op': 'setProperty', 'id': 'R1', 'path': '/anchor', 'value': [6 * FT, 4 * FT + FT // 2]}], r['resolved'])
    ensure(B['walls']['W8']['end'] == 'J9' and B['walls']['W11'] == {'end': 'J8', 'level': 'L1', 'start': 'J9', 'type': 'WT'},
           B['walls'])


T('composites', 'shrink-the-kitchen-from-the-south', '"Take a foot off the kitchen from the south": resizeRoom south by '
  '-1\'. The south side W7 continues east from J7 as the Dining room\'s W6, and J7 is a T: the Kitchen\'s own east '
  'wall W8 leaves it north, in the direction of v = (0, 1\'). So no jog edge is added: the run is reconnected to a new '
  'junction J9 at (12\', 1\') on W8, normalization splits W8 there, and its first piece, J7 -> J9, is the jog. J1 '
  'moves 1\' north and the Kitchen\'s anchor half of it.', ['4.4.1', '5.2.1'], house(),
  req({'op': 'resizeRoom', 'room': 'Kitchen', 'side': 'south', 'by': "-1'"}), check=kitchen_from_the_south)
T('composites', 'shrink-past-the-t', 'Shrinking the Kitchen from the south by 8\': W8, the edge leaving J7 in the '
  'direction of v, is 8\' long - not longer than |v| - so FS-OPS-008.', ['4.4.1', '7.1.1'], house(),
  req({'op': 'resizeRoom', 'room': 'Kitchen', 'side': 'south', 'by': "-8'"}), 'rejected', [('FS-OPS-008', ['R1'])])
T('composites', 'move-opening-without-width', 'The door\'s fill is unset, so it has no width, and moveOpening cannot '
  'place it: FS-OPS-003 names the opening.', ['4.5.1'], door_on_south(FT),
  req({'op': 'unsetProperty', 'id': 'O1', 'path': '/fill'}, {'op': 'moveOpening', 'opening': 'O1', 'at': 'centered'}),
  'rejected', [('FS-OPS-003', ['O1'])])
T('composites', 'remove-wall-on-a-crossed-level', 'removeWall by ID reads the faces either side of the wall; after '
  'the first operation makes W8 cross the north wall, its level has none to give: FS-OPS-007.', ['3.4.1', '4.7.1'],
  house(), req({'op': 'moveJunction', 'id': 'J8', 'to': ["13'", "13'"]}, {'op': 'removeWall', 'wall': 'W5'}),
  'rejected', [('FS-OPS-007', ['L1'])])
T('composites', 'created-elements-carry-common-members', 'addRoom and addOpening pass name, extensions and extras '
  'into the element as given.', ['4.5.1', '4.6.1'], dict(house(), extensionsUsed={'EXT_acoustics': '1.0'}),
  req({'op': 'addOpening', 'wall': 'W3', 'at': "2'", 'width': "2'", 'height': "3'", 'sill': "3'", 'name': 'Pantry window',
       'extras': {'glazing': 'double'}},
      {'op': 'drawSeparator', 'level': 'L1', 'from': ["24'", "6'"], 'to': ["28'", "6'"], 'name': 'Patio edge',
       'extensions': {'EXT_acoustics': {}}}),
  check=lambda r, B: ensure(B['openings']['O1']['extras'] == {'glazing': 'double'} and B['separators']['S1']['name'] == 'Patio edge', B))



def four_windows(offset=4 * FT):
    """The box with a 2' window on each wall at `offset`: O1 on W1 (J1 -> J2, running north), O2 on
    W2 (running east), O3 on W3 (running south), O4 on W4 (running west)."""
    return box(openings={f'O{i}': {'wall': f'W{i}', 'offset': offset, 'width': 2 * FT, 'height': 3 * FT, 'sill': 3 * FT}
                         for i in range(1, 5)})


def offsets(*values):
    """A check: the resolved echo sets O1's, O2's ... /offset to these values, in order."""
    return resolved_eq(*({'op': 'setProperty', 'id': f'O{i}', 'path': '/offset', 'value': v}
                         for i, v in enumerate(values, 1)))


T('composites', 'move-opening-by', 'moveOpening with "by" moves the opening along its wall: the new offset is the old '
  'plus "by", so a positive "by" moves the door 2\' toward the end of its wall W4.', ['4.5.2'], door_on_south(FT),
  req({'op': 'moveOpening', 'opening': 'O1', 'by': "2'"}),
  check=resolved_eq({'op': 'setProperty', 'id': 'O1', 'path': '/offset', 'value': 3 * FT}))
T('composites', 'move-opening-by-negative', 'A negative "by" moves the opening toward its wall\'s start: 4\' less '
  '1\' 6" is 2\' 6", 975360.', ['4.5.2', '3.1.1'], door_on_south(4 * FT),
  req({'op': 'moveOpening', 'opening': 'O1', 'by': "-1' 6\""}),
  check=resolved_eq({'op': 'setProperty', 'id': 'O1', 'path': '/offset', 'value': 975360}))
T('composites', 'move-opening-toward-start-and-end', 'With "toward": "end" or "start" the sign of "by" is chosen, '
  'whatever is given: -1\' toward the end moves the door from 4\' to 5\', and 2\' toward the start from 5\' to 3\'.',
  ['4.5.2'], door_on_south(4 * FT),
  req({'op': 'moveOpening', 'opening': 'O1', 'by': "-1'", 'toward': 'end'},
      {'op': 'moveOpening', 'opening': 'O1', 'by': "2'", 'toward': 'start'}),
  check=resolved_eq({'op': 'setProperty', 'id': 'O1', 'path': '/offset', 'value': 5 * FT},
                    {'op': 'setProperty', 'id': 'O1', 'path': '/offset', 'value': 3 * FT}))
T('composites', 'move-opening-toward-north-and-east', 'A window on each wall of the box, each 1\' toward north or '
  'east: W1 runs north and W2 east, so O1 and O2 move toward their walls\' ends (4\' to 5\'); W3 runs south and W4 '
  'west, so O3 and O4 move toward their walls\' starts (4\' to 3\').', ['4.5.2'], four_windows(),
  req({'op': 'moveOpening', 'opening': 'O1', 'by': "1'", 'toward': 'north'},
      {'op': 'moveOpening', 'opening': 'O2', 'by': "1'", 'toward': 'east'},
      {'op': 'moveOpening', 'opening': 'O3', 'by': "1'", 'toward': 'north'},
      {'op': 'moveOpening', 'opening': 'O4', 'by': "1'", 'toward': 'east'}),
  check=offsets(5 * FT, 5 * FT, 3 * FT, 3 * FT))
T('composites', 'move-opening-toward-south-and-west', 'The same windows 1\' toward south or west: O1 and O2 move '
  'toward their walls\' starts (4\' to 3\'), O3 and O4 toward their ends (4\' to 5\').', ['4.5.2'], four_windows(),
  req({'op': 'moveOpening', 'opening': 'O1', 'by': "1'", 'toward': 'south'},
      {'op': 'moveOpening', 'opening': 'O2', 'by': "1'", 'toward': 'west'},
      {'op': 'moveOpening', 'opening': 'O3', 'by': "-1'", 'toward': 'south'},
      {'op': 'moveOpening', 'opening': 'O4', 'by': "1'", 'toward': 'west'}),
  check=offsets(3 * FT, 3 * FT, 5 * FT, 5 * FT))
T('composites', 'move-opening-toward-on-an-oblique-wall', 'W5 runs from (2\', 2\') to (5\', 6\'), d = (3\', 4\'): '
  'd . east > 0, so 1\' toward east moves the window toward W5\'s end (1\' to 2\'); d . south < 0, so 2\' toward '
  'south moves it toward the start, to 0.', ['4.5.2'],
  dict(diag_wall, openings={'O1': {'wall': 'W5', 'offset': FT, 'width': FT, 'height': 3 * FT}}),
  req({'op': 'moveOpening', 'opening': 'O1', 'by': "1'", 'toward': 'east'},
      {'op': 'moveOpening', 'opening': 'O1', 'by': "2'", 'toward': 'south'}),
  check=resolved_eq({'op': 'setProperty', 'id': 'O1', 'path': '/offset', 'value': 2 * FT},
                    {'op': 'setProperty', 'id': 'O1', 'path': '/offset', 'value': 0}))
T('composites', 'move-opening-toward-perpendicular', 'W1 runs north, exactly perpendicular to east: the window on it '
  'cannot move toward the east along it, so FS-OPS-008 names the wall.', ['4.5.2', '7.1.1'], four_windows(),
  req({'op': 'moveOpening', 'opening': 'O1', 'by': "1'", 'toward': 'east'}), 'rejected', [('FS-OPS-008', ['W1'])])
T('composites', 'move-opening-past-the-wall-end', 'The door at 8\' on the 12\' wall W4 moved 2\' toward its end: '
  '10\' + 36" runs past the end, so the result is invalid and the rejection carries FS-INV-302.', ['4.5.2', '1.2.3'],
  door_on_south(8 * FT), req({'op': 'moveOpening', 'opening': 'O1', 'by': "2'"}), 'rejected', [('FS-INV-302', ['O1'])])
T('composites', 'move-opening-before-the-wall-start', 'The door at 1\' moved 2\' toward its wall\'s start: its offset '
  'would be -1\', and an offset is never negative, so the result is invalid.', ['4.5.2', '1.2.3'],
  door_on_south(FT), req({'op': 'moveOpening', 'opening': 'O1', 'by': "2'", 'toward': 'start'}), 'rejected',
  [('FS-SCH-001', [])])
T('composites', 'move-opening-at-and-by', 'moveOpening takes exactly one of "at" and "by": both is FS-OPS-001.',
  ['1.1.1', '4.5.2'], door_on_south(FT), req({'op': 'moveOpening', 'opening': 'O1', 'at': 'centered', 'by': "1'"}),
  'rejected', [('FS-OPS-001', [])])
T('composites', 'move-opening-neither-at-nor-by', 'moveOpening with neither "at" nor "by": FS-OPS-001.', ['1.1.1'],
  door_on_south(FT), req({'op': 'moveOpening', 'opening': 'O1'}), 'rejected', [('FS-OPS-001', [])])
T('composites', 'move-opening-toward-without-by', '"toward" is allowed only with "by": with "at" it is FS-OPS-001.',
  ['1.1.1', '4.5.2'], door_on_south(FT), req({'op': 'moveOpening', 'opening': 'O1', 'at': 0, 'toward': 'east'}),
  'rejected', [('FS-OPS-001', [])])
T('composites', 'move-opening-by-without-an-offset', 'The door\'s offset is unset earlier in the batch, so there is no '
  'offset to move it from: FS-OPS-003 names the opening.', ['4.5.2', '7.1.1'], door_on_south(FT),
  req({'op': 'unsetProperty', 'id': 'O1', 'path': '/offset'}, {'op': 'moveOpening', 'opening': 'O1', 'by': "1'"}),
  'rejected', [('FS-OPS-003', ['O1'])])
T('composites', 'add-level-above', '"Add a second floor": addLevel above L1 sits on top of it, at L1\'s elevation plus '
  'its height, 0 + 3456000. Its height is 8\', 3121152, and its ID is minted.', ['4.8.1', '1.5.1'], box(),
  req({'op': 'addLevel', 'building': 'B1', 'above': 'L1', 'height': "8'", 'name': 'Second floor'}),
  check=resolved_eq({'op': 'addElement', 'collection': 'levels', 'id': 'L2',
                     'element': {'building': 'B1', 'elevation': H, 'height': 8 * FT, 'name': 'Second floor'}}))
T('composites', 'add-level-below', '"Add a basement": addLevel below L1 is the new level\'s own height under L1\'s '
  'floor, 0 - 8\' = -3121152.', ['4.8.1'], box(),
  req({'op': 'addLevel', 'building': 'B1', 'below': 'L1', 'height': "8'", 'name': 'Basement'}),
  check=resolved_eq({'op': 'addElement', 'collection': 'levels', 'id': 'L2',
                     'element': {'building': 'B1', 'elevation': -8 * FT, 'height': 8 * FT, 'name': 'Basement'}}))
T('composites', 'add-level-explicit', 'addLevel with an explicit elevation, a named ID and extras: lengths in the '
  'reference grammar - -8\' and 7\' 6" - are resolved to integers.', ['4.8.1', '3.1.1'], box(),
  req({'op': 'addLevel', 'id': 'L0', 'building': 'B1', 'elevation': "-8'", 'height': "7' 6\"", 'extras': {'use': 'storage'}}),
  check=resolved_eq({'op': 'addElement', 'collection': 'levels', 'id': 'L0',
                     'element': {'building': 'B1', 'elevation': -8 * FT, 'height': 7 * FT + 6 * IN, 'extras': {'use': 'storage'}}}))
T('composites', 'add-level-stacked', 'Levels added earlier in the batch are in the working copy: L2 above L1, then L3 '
  'above L2 at 3456000 + 3121152, then L4 below L1.', ['4.8.1'], box(),
  req({'op': 'addLevel', 'building': 'B1', 'above': 'L1', 'height': "8'"},
      {'op': 'addLevel', 'building': 'B1', 'above': 'L2', 'height': "9'"},
      {'op': 'addLevel', 'building': 'B1', 'below': 'L1', 'height': 2500 * MM}),
  check=resolved_eq({'op': 'addElement', 'collection': 'levels', 'id': 'L2', 'element': {'building': 'B1', 'elevation': H, 'height': 8 * FT}},
                    {'op': 'addElement', 'collection': 'levels', 'id': 'L3', 'element': {'building': 'B1', 'elevation': H + 8 * FT, 'height': 9 * FT}},
                    {'op': 'addElement', 'collection': 'levels', 'id': 'L4', 'element': {'building': 'B1', 'elevation': -2500 * MM, 'height': 2500 * MM}}))
T('composites', 'add-level-elevation-and-above', 'addLevel takes exactly one of "elevation", "above" and "below": '
  'two is FS-OPS-001.', ['1.1.1', '4.8.1'], box(),
  req({'op': 'addLevel', 'building': 'B1', 'elevation': 0, 'above': 'L1', 'height': "8'"}), 'rejected', [('FS-OPS-001', [])])
T('composites', 'add-level-above-and-below', '"above" and "below" together: FS-OPS-001.', ['1.1.1'], box(),
  req({'op': 'addLevel', 'building': 'B1', 'above': 'L1', 'below': 'L1', 'height': "8'"}), 'rejected', [('FS-OPS-001', [])])
T('composites', 'add-level-no-elevation', 'addLevel with none of "elevation", "above" and "below": FS-OPS-001.',
  ['1.1.1'], box(), req({'op': 'addLevel', 'building': 'B1', 'height': "8'"}), 'rejected', [('FS-OPS-001', [])])
T('composites', 'add-level-above-an-unknown-level', '"above" names L9, which does not exist: FS-OPS-003, with no '
  'elements, since the reference is in the request.', ['4.8.1', '3.3.1'], box(),
  req({'op': 'addLevel', 'building': 'B1', 'above': 'L9', 'height': "8'"}), 'rejected', [('FS-OPS-003', [])])
T('composites', 'add-level-below-a-room', '"below" names the room Living: only levels count as matches, so it '
  'resolves to nothing.', ['4.8.1', '3.3.1'], box(),
  req({'op': 'addLevel', 'building': 'B1', 'below': 'Living', 'height': "8'"}), 'rejected', [('FS-OPS-003', [])])
T('composites', 'add-level-in-an-unknown-building', '"building" names B9, which does not exist: FS-OPS-003.',
  ['4.8.1'], box(), req({'op': 'addLevel', 'building': 'B9', 'elevation': 0, 'height': "8'"}), 'rejected',
  [('FS-OPS-003', [])])
T('composites', 'add-level-above-a-level-without-a-height', 'L1\'s height is unset earlier in the batch, so there is '
  'no top to sit on: FS-OPS-003 names L1.', ['4.8.1', '7.1.1'], box(),
  req({'op': 'unsetProperty', 'id': 'L1', 'path': '/height'},
      {'op': 'addLevel', 'building': 'B1', 'above': 'L1', 'height': "8'"}), 'rejected', [('FS-OPS-003', ['L1'])])

# ================================================================================== normalization
T('normalization', 'draw-a-wall-across-two-walls', 'A wall drawn straight across the room from (-2\', 6\') to '
  '(14\', 6\') crosses W1 and W3. Planarization inserts junctions at both crossings - J7 at (0, 6\') and J8 at '
  '(12\', 6\'), in order of x - and splits all three walls: each first piece keeps its ID, the others are minted in '
  'order along the edge, edges taken by ID (W1 -> W6, W3 -> W7, W5 -> W8, W9).', ['5.2.1', '5.4.1', '4.1.1'], box(),
  req({'op': 'drawWall', 'level': 'L1', 'from': ["-2'", "6'"], 'to': ["14'", "6'"], 'type': 'WT'}),
  check=lambda r, B: ensure(
      pos(B, 'J7') == [0, 6 * FT] and pos(B, 'J8') == [12 * FT, 6 * FT]
      and (B['walls']['W1']['end'], B['walls']['W6']['start'], B['walls']['W6']['end']) == ('J7', 'J7', 'J2')
      and (B['walls']['W3']['end'], B['walls']['W7']['start'], B['walls']['W7']['end']) == ('J8', 'J8', 'J4')
      and [B['walls'][w]['start'] + '>' + B['walls'][w]['end'] for w in ('W5', 'W8', 'W9')] == ['J5>J7', 'J7>J8', 'J8>J6'],
      B['walls']))
T('normalization', 'a-wall-ending-on-a-wall', 'A wall drawn from the middle of the south wall into the room: its '
  'start junction J5 lies inside W4, so W4 is split there (J4 -> J5 keeps W4, J5 -> J1 is W6). No junction is '
  'minted: the hot pixel\'s centre is J5\'s position.', ['5.2.1'], box(),
  req({'op': 'drawWall', 'level': 'L1', 'from': ["6'", 0], 'to': ["6'", "3'"], 'type': 'WT'}),
  check=lambda r, B: ensure(r['created'] == ['J5', 'J6', 'W5', 'W6'] and B['walls']['W4']['end'] == 'J5'
                            and B['walls']['W6'] == {'end': 'J1', 'level': 'L1', 'start': 'J5', 'type': 'WT'}, B['walls']))
T('normalization', 'crossing-rounded', 'A wall from (1000000, -300000) to (2000000, 400001) crosses the south wall at '
  'x = 1000000 + 1000000 * 300000 / 700001 = 1428570.82: the hot pixel is (1428571, 0), and both walls are routed '
  'through its centre - the drawn one moved by less than one base unit.', ['5.2.1', '1.3.2'], box(),
  req({'op': 'drawWall', 'level': 'L1', 'from': [1000000, -300000], 'to': [2000000, 400001], 'type': 'WT'}),
  check=lambda r, B: ensure(pos(B, 'J7') == [1428571, 0] and B['walls']['W5']['end'] == 'J7'
                            and B['walls']['W7'] == {'end': 'J6', 'level': 'L1', 'start': 'J7', 'type': 'WT'}, B['walls']))
T('normalization', 'crossing-at-a-half-even', 'A wall from (2000000, -300000) to (2000001, 300000) crosses y = 0 at '
  'x = 2000000.5 exactly. Rounding ties to even, so the hot pixel is (2000000, 0).', ['5.2.1'], box(),
  req({'op': 'drawWall', 'level': 'L1', 'from': [2000000, -300000], 'to': [2000001, 300000], 'type': 'WT'}),
  check=lambda r, B: ensure(pos(B, 'J7') == [2000000, 0], pos(B, 'J7')))
T('normalization', 'crossing-at-a-half-odd', 'The same wall one unit east crosses at x = 2000001.5, which rounds to '
  'the even 2000002.', ['5.2.1'], box(),
  req({'op': 'drawWall', 'level': 'L1', 'from': [2000001, -300000], 'to': [2000002, 300000], 'type': 'WT'}),
  check=lambda r, B: ensure(pos(B, 'J7') == [2000002, 0], pos(B, 'J7')))
T('normalization', 'pixel-corner-even', 'A post P at (2000000, 2000000) and a wall drawn along x + y = 4000001, out '
  'across the south wall - so the level breaks Core 5.3 and is planarized. The wall touches P\'s pixel only at its '
  'corner (2000000.5, 2000000.5); both coordinates of P are even, so its pixel includes its edges and corners: the '
  'wall passes through it and is routed through P and split there, as well as at the south wall.', ['5.2.1'],
  box(junctions={'P': J(2000000, 2000000)}),
  req({'op': 'drawWall', 'level': 'L1', 'from': [1500000, 2500001], 'to': [4500001, -500000], 'type': 'WT'}),
  check=lambda r, B: ensure(B['walls']['W5']['end'] == 'P' and B['walls']['W7']['start'] == 'P', B['walls']))
T('normalization', 'pixel-corner-odd', 'The same with P at (2000001, 2000000) and the wall along x + y = 4000002: P\'s '
  'x is odd, so its pixel excludes the corner (2000001.5, 2000000.5), which rounds to (2000002, 2000000). The wall '
  'misses the pixel: it is split at the south wall only.', ['5.2.1'], box(junctions={'P': J(2000001, 2000000)}),
  req({'op': 'drawWall', 'level': 'L1', 'from': [1500001, 2500001], 'to': [4500002, -500000], 'type': 'WT'}),
  check=lambda r, B: ensure(r['created'] == ['J5', 'J6', 'J7', 'W5', 'W6', 'W7'] and B['walls']['W5']['end'] == 'J7', r['created']))
T('normalization', 'drag-a-corner-onto-another', 'The courtyard wall\'s free end J7 dragged onto the box\'s corner J3. '
  'Both were in A, so the survivor is the one whose ID sorts first, J3: W7 now ends at J3 and J7 is removed, closing '
  'the courtyard.', ['5.1.1', '5.4.1'], courtyard(), req({'op': 'moveJunction', 'id': 'J7', 'to': 'J3'}),
  check=lambda r, B: ensure(r['removed'] == ['J7'] and B['walls']['W7']['end'] == 'J3', B['walls']['W7']))
T('normalization', 'drag-the-other-way', 'The box\'s corner J3 dragged onto J7: the survivor is still J3, the one that '
  'sorts first - now at J7\'s position - and J7 is removed.', ['5.1.1'], courtyard(),
  req({'op': 'moveJunction', 'id': 'J3', 'to': 'J7'}),
  check=lambda r, B: ensure(r['removed'] == ['J7'] and pos(B, 'J3') == [13 * FT, 10 * FT] and B['walls']['W7']['end'] == 'J3', B['junctions']))
T('normalization', 'survivor-was-in-a', 'A wall drawn in the courtyard, its new end J9 then moved onto the corner NE. '
  'Exactly one of the two was in A - NE - so NE survives, although J9 sorts first.', ['5.1.1'], courtyard(),
  req({'op': 'drawWall', 'level': 'L1', 'from': ["16'", "5'"], 'to': ["19'", "9'"], 'type': 'WT'},
      {'op': 'moveJunction', 'id': 'J9', 'to': 'NE'}),
  check=lambda r, B: ensure(r['created'] == ['J8', 'W8'] and B['walls']['W8']['end'] == 'NE', B['walls']['W8']))
T('normalization', 'merge-makes-a-wall-of-no-length', 'The box\'s corner J3 dragged onto J2: they merge, and W2 now '
  'starts and ends at J2. Normalization does not decide what was meant; validation rejects the result.',
  ['5.1.1', '1.2.3'], box(), req({'op': 'moveJunction', 'id': 'J3', 'to': 'J2'}), 'rejected', [('FS-INV-102', ['W2'])])
T('normalization', 'opening-stays-on-the-first-piece', 'A partition drawn across the room at x = 8\' splits the south '
  'wall W4 (J4 (12\', 0) -> J1) at 4\' from its start. The door at offset 1\' spans [1\', 4\'], inside the first piece '
  '[0, 4\'], so it stays on W4 with its offset.', ['5.2.1'], door_on_south(FT),
  req({'op': 'drawWall', 'level': 'L1', 'from': ["8'", 0], 'to': ["8'", "10'"], 'type': 'WT'}),
  check=lambda r, B: ensure(B['openings']['O1'] == {'fill': 'T-door-36', 'offset': FT, 'wall': 'W4'}, B['openings']))
T('normalization', 'opening-rehosted', 'The door at offset 6\' spans [6\', 9\'], inside the second piece [4\', 12\'] '
  '- the new wall W7 from J5 (8\', 0) to J1. It moves there, and its offset becomes 6\' - 4\' = 2\'.', ['5.2.1'],
  door_on_south(6 * FT), req({'op': 'drawWall', 'level': 'L1', 'from': ["8'", 0], 'to': ["8'", "10'"], 'type': 'WT'}),
  check=lambda r, B: ensure(B['openings']['O1'] == {'fill': 'T-door-36', 'offset': 2 * FT, 'wall': 'W7'}
                            and B['walls']['W7']['start'] == 'J5', (B['openings'], B['walls'])))
T('normalization', 'opening-straddles', 'The door at offset 3\' spans [3\', 6\'], across the new junction at 4\': '
  'no piece contains it, FS-OPS-009.', ['5.2.1', '7.1.1'], door_on_south(3 * FT),
  req({'op': 'drawWall', 'level': 'L1', 'from': ["8'", 0], 'to': ["8'", "10'"], 'type': 'WT'}), 'rejected',
  [('FS-OPS-009', ['O1'])])
T('normalization', 'two-openings-straddle', 'Two doors, each across a new junction: one FS-OPS-009 for each.',
  ['5.2.1', '7.1.1', '7.1.2'], box(openings={'O1': {'wall': 'W4', 'offset': 3 * FT, 'fill': 'T-door-36'},
                                    'O2': {'wall': 'W2', 'offset': 7 * FT, 'fill': 'T-door-36'}}),
  req({'op': 'drawWall', 'level': 'L1', 'from': ["8'", 0], 'to': ["8'", "10'"], 'type': 'WT'}), 'rejected',
  [('FS-OPS-009', ['O1']), ('FS-OPS-009', ['O2'])])
T('normalization', 'opening-rehosted-on-an-oblique-wall', 'A door at offset 8\' on an oblique wall W5 from (1\', 1\') '
  'to (11\', 9\'). A wall drawn across it at x = 6\' crosses W5 at (6\', 5\') - exactly, so the hot pixel\'s centre '
  'J9 is on W5\'s line - and W5 is split there: W5 keeps J5 -> J9, W7 is J9 -> J6. The first piece covers '
  '[0, sqrt(41) ft] = [0, 2498140.50] of the original line, so the door\'s interval [3121152, 4291584] lies in the '
  'second; it moves to W7, and its offset becomes 8 ft - sqrt(41) ft = 623011.50, rounded once to 623011.', ['5.2.1'],
  box(junctions={'J5': J(FT, FT), 'J6': J(11 * FT, 9 * FT)}, walls={'W5': W('J5', 'J6')},
      rooms={'R1': R(9 * FT, 3 * FT, 'Living')},
      openings={'O1': {'wall': 'W5', 'offset': 8 * FT, 'fill': 'T-door-36'}}),
  req({'op': 'drawWall', 'level': 'L1', 'from': ["6'", "2'"], 'to': ["6'", "8'"], 'type': 'WT'}),
  check=lambda r, B: ensure(B['openings']['O1'] == {'fill': 'T-door-36', 'offset': 623011, 'wall': 'W7'}
                            and B['walls']['W7'] == {'end': 'J6', 'level': 'L1', 'start': 'J9', 'type': 'WT'}, B['openings']))
T('normalization', 'join-cleanup-after-a-split', 'J3 is a butt join through the north wall W2. A wall drawn from the '
  'middle of W2 splits it, so W2 (J2 -> J5) no longer ends at J3 and J3\'s join is removed; the default join '
  'applies.', ['5.3.1', '5.4.1', '5.2.1'], box(junctions={'J3': J(12 * FT, 10 * FT, join={'kind': 'butt', 'through': ['W2']})}),
  req({'op': 'drawWall', 'level': 'L1', 'from': ["8'", "10'"], 'to': ["8'", "6'"], 'type': 'WT'}),
  check=lambda r, B: ensure('join' not in B['junctions']['J3'] and B['walls']['W2']['end'] == 'J5', B['junctions']['J3']))
T('normalization', 'join-cleanup-after-a-redirect', 'G2 is a butt join through W5. Setting W5\'s end to a new '
  'junction leaves the join naming a wall that does not end at G2: it is removed.', ['5.3.1'], garden(),
  req({'op': 'addJunction', 'level': 'L1', 'position': ["20'", "1'"]}, {'op': 'setProperty', 'id': 'W5', 'path': '/end', 'value': 'J5'}),
  check=lambda r, B: ensure('join' not in B['junctions']['G2'], B['junctions']['G2']))
T('normalization', 'join-kept-when-it-applies', 'A butt join whose through wall still ends at its junction is kept.',
  ['5.3.1'], garden(), req({'op': 'moveJunction', 'id': 'G3', 'to': ["20'", "8'"]}),
  check=lambda r, B: ensure(B['junctions']['G2']['join'] == {'kind': 'butt', 'through': ['W5']}, B['junctions']['G2']))
divided = level_doc(junctions={'J1': J(0, 0), 'J2': J(0, 10 * FT), 'J3': J(12 * FT, 10 * FT), 'J4': J(12 * FT, 0),
                               'J5': J(6 * FT, 0), 'J6': J(6 * FT, 10 * FT)},
                    walls={'W1': W('J1', 'J2'), 'W2': W('J2', 'J6'), 'W3': W('J6', 'J3'), 'W4': W('J3', 'J4'),
                           'W5': W('J4', 'J5'), 'W6': W('J5', 'J1')},
                    separators={'S1': S('J5', 'J6')},
                    rooms={'R1': R(3 * FT, 3 * FT, 'Kitchen'), 'R2': R(9 * FT, 3 * FT, 'Living')})
T('normalization', 'a-separator-split', 'A wall drawn across a room divided by a separator splits the separator too; '
  'its new piece is minted with the separator prefix.', ['5.2.1'], divided,
  req({'op': 'drawWall', 'level': 'L1', 'from': ["-1'", "7'"], 'to': ["13'", "7'"], 'type': 'WT'}),
  check=lambda r, B: ensure(B['separators']['S2'] == {'end': 'J6', 'level': 'L1', 'start': 'J10'}, B['separators']))
T('normalization', 'a-valid-document-is-left-alone', 'A batch that changes only a name: normalization of a planar '
  'level with no near misses changes nothing, and the inverse is the one setProperty.', ['5.4.1', '5.1.1', '5.2.1'],
  house(), req({'op': 'setProperty', 'id': 'R1', 'path': '/name', 'value': 'Kitchen & breakfast'}),
  check=lambda r, B: ensure(r['inverse'] == [{'op': 'setProperty', 'id': 'R1', 'path': '/name', 'value': 'Kitchen'}], r['inverse']))

near_miss = box(junctions={'P': J(2000000, 2000000), 'N1': J(1500000, 2500001), 'N2': J(2500001, 1500000)},
                walls={'W5': W('N1', 'N2')})
T('normalization', 'near-miss-left-alone', 'A wall W5 along x + y = 4000001 passes 0.7 base units from the post P - '
  'inside P\'s pixel, but not through P - in a valid A. A rename elsewhere leaves the level satisfying Core 5.3, so '
  'it is not planarized: W5 is not split, and B is A but for the name.', ['5.2.1', '5.4.1'], near_miss,
  req({'op': 'setProperty', 'id': 'R1', 'path': '/name', 'value': 'Sitting room'}),
  check=lambda r, B: ensure(r['created'] == [] and B['walls']['W5'] == {'end': 'N2', 'level': 'L1', 'start': 'N1', 'type': 'WT'}
                            and r['inverse'] == [{'op': 'setProperty', 'id': 'R1', 'path': '/name', 'value': 'Living'}], B['walls']))
T('normalization', 'near-miss-on-a-planarized-level', 'The same A, with a wall drawn across the south wall elsewhere: '
  'the level now breaks Core 5.3 and is snap-rounded as a whole, so W5, passing through P\'s pixel, is routed '
  'through P and split there.', ['5.2.1'], near_miss,
  req({'op': 'drawWall', 'level': 'L1', 'from': ["10'", "-1'"], 'to': ["10'", "1'"], 'type': 'WT'}),
  check=lambda r, B: ensure(B['walls']['W5']['end'] == 'P', B['walls']['W5']))

# ================================================================================== locks
KITCHEN_WIDER = {'op': 'resizeRoom', 'room': 'Kitchen', 'side': 'east', 'by': K}
T('locks', 'room-lock-holds', 'The Pantry is locked while the Kitchen is made 2\' wider: J8 stays (the jog), so the '
  'Pantry\'s content and every junction on its cycle are unchanged, and the batch commits.', ['6.1.2'], house(),
  req(KITCHEN_WIDER, locks=[{'element': 'R2'}]))
T('locks', 'room-lock-broken', 'The Dining room is locked: its anchor moves with the Kitchen\'s east wall, so its '
  'content changes. FS-OPS-011 names R3.', ['6.1.2', '7.1.1'], house(), req(KITCHEN_WIDER, locks=[{'element': 'R3'}]),
  'rejected', [('FS-OPS-011', ['R3'])])
T('locks', 'room-lock-junction-moved', 'The Pantry is locked and its corner J3 is moved: the room\'s own content is '
  'unchanged, but a junction on its cycle moved.', ['6.1.2'], house(),
  req({'op': 'moveJunction', 'id': 'J3', 'to': ["-1'", "12'"]}, locks=[{'element': 'R2'}]), 'rejected',
  [('FS-OPS-011', ['R2'])])
T('locks', 'wall-lock-junction-moved', 'The wall W6 is locked: its content does not change, but its end junction J7 '
  'moves 2\' east.', ['6.1.2'], house(), req(KITCHEN_WIDER, locks=[{'element': 'W6'}]), 'rejected',
  [('FS-OPS-011', ['W6'])])
T('locks', 'wall-lock-content-changed', 'The wall W8 is locked and renamed.', ['6.1.2'], house(),
  req({'op': 'setProperty', 'id': 'W8', 'path': '/name', 'value': 'Kitchen east'}, locks=[{'element': 'W8'}]),
  'rejected', [('FS-OPS-011', ['W8'])])
T('locks', 'element-lock-on-a-type', 'An element lock on a type holds while the type is unchanged.', ['6.1.2'], house(),
  req(KITCHEN_WIDER, locks=[{'element': 'WT'}, {'element': 'L1'}]))
T('locks', 'length-lock-holds', 'W8 is locked to its length: resizing the Kitchen moves W8 bodily (J7 east, its end '
  'reconnected to J9 at (14\', 8\')), so it stays 8\' long.', ['6.1.2'], house(), req(KITCHEN_WIDER, locks=[{'length': 'W8'}]))
T('locks', 'length-lock-broken', 'W7, the Kitchen\'s south wall, is locked to its length; it stretches from 12\' to '
  '14\'.', ['6.1.2'], house(), req(KITCHEN_WIDER, locks=[{'length': 'W7'}]), 'rejected', [('FS-OPS-011', ['W7'])])
T('locks', 'distance-lock-holds', 'The two exterior walls W1 and W5 are locked 24\' apart; resizing the Kitchen moves '
  'neither.', ['6.1.2'], house(), req(KITCHEN_WIDER, locks=[{'distance': ['W1', 'W5']}]))
T('locks', 'distance-lock-broken', 'The Dining room\'s east wall W5 and the Kitchen\'s east wall W8 are locked 12\' '
  'apart; the resize makes it 10\'.', ['6.1.2'], house(), req(KITCHEN_WIDER, locks=[{'distance': ['W5', 'W8']}]),
  'rejected', [('FS-OPS-011', ['W5', 'W8'])])
T('locks', 'distance-lock-oblique', 'Two parallel oblique walls locked apart, both moved by the same vector: the '
  'distance is unchanged (compared exactly, by squared cross products).', ['6.1.2'],
  box(junctions={'J5': J(2 * FT, 2 * FT), 'J6': J(5 * FT, 6 * FT), 'J7': J(4 * FT, 1 * FT), 'J8': J(7 * FT, 5 * FT)},
      walls={'W5': W('J5', 'J6'), 'W6': W('J7', 'J8')}),
  req({'op': 'moveWall', 'wall': 'W5', 'by': '6"'}, {'op': 'moveWall', 'wall': 'W6', 'by': '6"'},
      locks=[{'distance': ['W5', 'W6']}]))
T('locks', 'lock-names-a-missing-element', 'A lock on R9, which A does not have: FS-OPS-010.', ['6.1.1', '7.1.1'],
  house(), req(KITCHEN_WIDER, locks=[{'element': 'R9'}]), 'rejected', [('FS-OPS-010', ['R9'])])
T('locks', 'distance-lock-not-parallel', 'A distance lock between W1 and W3, which are perpendicular in A: '
  'FS-OPS-010.', ['6.1.1'], house(), req(KITCHEN_WIDER, locks=[{'distance': ['W1', 'W3']}]), 'rejected',
  [('FS-OPS-010', ['W1', 'W3'])])
T('locks', 'length-lock-not-a-wall', 'A length lock on R1, a room: it names no wall, FS-OPS-010.', ['6.1.1'], house(),
  req(KITCHEN_WIDER, locks=[{'length': 'R1'}]), 'rejected', [('FS-OPS-010', ['R1'])])
T('locks', 'every-broken-lock', 'Two locks broken at once: one FS-OPS-011 for each, sorted.', ['6.1.2', '7.1.1', '7.1.2'],
  house(), req(KITCHEN_WIDER, locks=[{'length': 'W7'}, {'element': 'R2'}, {'element': 'R3'}]), 'rejected',
  [('FS-OPS-011', ['R3']), ('FS-OPS-011', ['W7'])])
T('locks', 'locks-after-validation', 'An invalid result that also breaks a lock is rejected for what validation '
  'finds; locks are checked only on a valid result.', ['6.1.2', '1.2.3', '7.1.1', '7.1.2'], house(),
  req({'op': 'removeElement', 'id': 'W8'}, locks=[{'length': 'W8'}]), 'rejected', [('FS-INV-202', ['R1', 'R3'])])

# ================================================================================== diagnostics
T('diagnostics', 'first-failure-wins', 'The first operation names a room that does not exist (FS-OPS-003); the '
  'second has a malformed length (FS-OPS-012). Only the first failure is reported.', ['7.1.1', '7.1.2'], house(),
  req({'op': 'resizeRoom', 'room': 'Garage', 'side': 'east', 'by': K},
      {'op': 'resizeRoom', 'room': 'Kitchen', 'side': 'east', 'by': 'two feet'}), 'rejected', [('FS-OPS-003', [])])
T('diagnostics', 'first-failure-wins-in-order', 'The same two operations the other way round: FS-OPS-012 alone.',
  ['7.1.1', '3.1.1'], house(),
  req({'op': 'resizeRoom', 'room': 'Kitchen', 'side': 'east', 'by': 'two feet'},
      {'op': 'resizeRoom', 'room': 'Garage', 'side': 'east', 'by': K}), 'rejected', [('FS-OPS-012', [])])
T('diagnostics', 'every-match-listed', 'FS-OPS-004 lists every match: three rooms named "Bedroom".', ['7.1.1', '3.3.1'],
  house(rooms={'R1': R(6 * FT, 4 * FT, 'Bedroom'), 'R2': R(6 * FT, 10 * FT, 'BEDROOM'), 'R3': R(18 * FT, 6 * FT, 'bedroom')}),
  req({'op': 'moveRoom', 'room': 'Bedroom', 'by': "1' east"}), 'rejected', [('FS-OPS-004', ['R1', 'R2', 'R3'])])
T('diagnostics', 'blocked-element-and-dependents', 'FS-OPS-006 names the blocked element and every dependent: J8 and '
  'the three walls that end at it.', ['7.1.1', '2.2.1'], house(), req({'op': 'removeElement', 'id': 'J8'}), 'rejected',
  [('FS-OPS-006', ['J8', 'W10', 'W8', 'W9'])])
T('diagnostics', 'composite-names-its-room', 'FS-OPS-008 for resizeRoom names the room.', ['7.1.1', '4.4.1'], l_shaped(),
  req({'op': 'resizeRoom', 'room': 'Den', 'side': 'east', 'by': "-1'"}), 'rejected', [('FS-OPS-008', ['R1'])])
T('diagnostics', 'each-bad-lock', 'Two locks that cannot apply to A: one FS-OPS-010 for each.', ['7.1.1', '7.1.2', '6.1.1'],
  house(), req(KITCHEN_WIDER, locks=[{'element': 'R9'}, {'length': 'J1'}]), 'rejected',
  [('FS-OPS-010', ['J1']), ('FS-OPS-010', ['R9'])])
T('diagnostics', 'core-diagnostics-of-the-result', 'A rejected result carries the Core diagnostics with severity error '
  'that the result has, with their elements: a door wider than its wall.', ['7.1.1', '1.2.3'], house(),
  req({'op': 'addOpening', 'wall': 'W8', 'at': "6'", 'fill': 'T-door-36'}), 'rejected', [('FS-INV-302', ['O1'])])

# ================================================================================== inverse
T('inverse', 'inverse-of-a-cascade', 'The inverse of removing G2 with cascade re-adds what it took, in the reverse '
  'collection order - junctions, then walls, then openings - each exactly as it was in A.', ['1.6.1', '2.2.2'],
  garden(), req({'op': 'removeElement', 'id': 'G2', 'cascade': True}),
  check=lambda r, B: ensure([(p['op'], p['id']) for p in r['inverse']] == [('addElement', 'G2'), ('addElement', 'W5'),
                                                                          ('addElement', 'W6'), ('addElement', 'O1')], r['inverse']))
T('inverse', 'inverse-of-additions', 'The inverse of a drawn wall and a door in it removes them - openings, then walls, '
  'then junctions, by ID.', ['1.6.1'], box(),
  req({'op': 'drawWall', 'level': 'L1', 'from': ["2'", "7'"], 'to': ["8'", "7'"], 'type': 'WT'},
      {'op': 'addOpening', 'wall': 'W5', 'at': 'centered', 'fill': 'T-door-36'}),
  check=lambda r, B: ensure(r['inverse'] == [{'op': 'removeElement', 'id': i} for i in ('O1', 'W5', 'J5', 'J6')], r['inverse']))
T('inverse', 'inverse-of-property-changes', 'A member set, one changed and one removed: the inverse sets what A has '
  'and B lacks or has differently, and unsets what B has and A lacks, by member name.', ['1.6.1', '2.3.1'],
  box(rooms={'R1': R(6 * FT, 5 * FT, 'Living', function='living')}),
  req({'op': 'setProperty', 'id': 'R1', 'path': '/name', 'value': 'Lounge'},
      {'op': 'unsetProperty', 'id': 'R1', 'path': '/function'},
      {'op': 'setProperty', 'id': 'R1', 'path': '/extras', 'value': {'colour': 'teal'}}),
  check=lambda r, B: ensure(r['inverse'] == [{'op': 'unsetProperty', 'id': 'R1', 'path': '/extras'},
                                             {'op': 'setProperty', 'id': 'R1', 'path': '/function', 'value': 'living'},
                                             {'op': 'setProperty', 'id': 'R1', 'path': '/name', 'value': 'Living'}], r['inverse']))
T('inverse', 'inverse-of-a-split', 'The inverse of a split restores W4\'s end before removing the junction and the '
  'piece the split created - otherwise the removal of J5 would be blocked by W4. Property differences come first '
  '(1.6, step 1).', ['1.6.1', '5.2.1'], box(),
  req({'op': 'drawWall', 'level': 'L1', 'from': ["6'", 0], 'to': ["6'", "3'"], 'type': 'WT'}),
  check=lambda r, B: ensure(r['inverse'] == [{'op': 'setProperty', 'id': 'W4', 'path': '/end', 'value': 'J1'},
                                             {'op': 'removeElement', 'id': 'W5'}, {'op': 'removeElement', 'id': 'W6'},
                                             {'op': 'removeElement', 'id': 'J5'}, {'op': 'removeElement', 'id': 'J6'}], r['inverse']))
T('inverse', 'inverse-of-a-jog', 'The inverse of making the Kitchen wider: properties first (anchors, W8\'s end, J7), '
  'then the jog W11 and J9 removed.', ['1.6.1', '4.4.1'], house(), req(KITCHEN_WIDER),
  check=lambda r, B: ensure([p['op'] for p in r['inverse']] == ['setProperty'] * 4 + ['removeElement'] * 2, r['inverse']))
T('inverse', 'inverse-of-a-rehosting', 'The inverse of a split that re-hosted a door puts the door back on W4 with '
  'its old offset.', ['1.6.1'], door_on_south(6 * FT),
  req({'op': 'drawWall', 'level': 'L1', 'from': ["8'", 0], 'to': ["8'", "10'"], 'type': 'WT'}),
  check=lambda r, B: ensure(r['inverse'][0] == {'op': 'setProperty', 'id': 'O1', 'path': '/offset', 'value': 6 * FT}, r['inverse']))
T('inverse', 'inverse-of-document-members', 'Changes to $project, $site and $document are inverted on those targets.',
  ['1.6.1', '2.3.1'], box(site={'trueNorth': 1000000}, extras={'importer': 'dwg'}),
  req({'op': 'setProperty', 'id': '$project', 'path': '/name', 'value': 'Cottage'},
      {'op': 'setProperty', 'id': '$site', 'path': '/trueNorth', 'value': 2000000},
      {'op': 'unsetProperty', 'id': '$document', 'path': '/extras'}),
  check=lambda r, B: ensure(r['inverse'] == [{'op': 'setProperty', 'id': '$project', 'path': '/name', 'value': 'Conformance'},
                                             {'op': 'setProperty', 'id': '$site', 'path': '/trueNorth', 'value': 1000000},
                                             {'op': 'setProperty', 'id': '$document', 'path': '/extras', 'value': {'importer': 'dwg'}}], r['inverse']))
T('inverse', 'inverse-of-a-new-site', 'The batch creates the site; the site exists in B only, so the inverse unsets '
  'it as $document\'s /site (1.6, step 4).', ['1.6.1', '2.3.1'], box(),
  req({'op': 'setProperty', 'id': '$site', 'path': '/location', 'value': {'latitude': 42360100, 'longitude': -71058900}}),
  check=lambda r, B: ensure(r['inverse'] == [{'op': 'unsetProperty', 'id': '$document', 'path': '/site'}], r['inverse']))
T('inverse', 'inverse-of-a-removed-site', 'The batch removes the site; the inverse sets it back.', ['1.6.1'],
  box(site={'trueNorth': -500000}), req({'op': 'unsetProperty', 'id': '$document', 'path': '/site'}),
  check=lambda r, B: ensure(r['inverse'] == [{'op': 'setProperty', 'id': '$document', 'path': '/site', 'value': {'trueNorth': -500000}}], r['inverse']))
T('inverse', 'inverse-compares-canonical-forms', 'A writes "justification": "center" explicitly; the batch sets it to '
  '"center" again. The two are the same in canonical form, so nothing is inverted for it.', ['1.6.1'],
  box(walls={'W1': W('J1', 'J2', justification='center')}),
  req({'op': 'setProperty', 'id': 'W1', 'path': '/justification', 'value': 'center'},
      {'op': 'setProperty', 'id': 'W1', 'path': '/name', 'value': 'West'}),
  check=lambda r, B: ensure(r['inverse'] == [{'op': 'unsetProperty', 'id': 'W1', 'path': '/name'}], r['inverse']))

if __name__ == '__main__':
    run()

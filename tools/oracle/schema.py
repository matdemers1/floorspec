"""A hand-written structural check standing in for the schema tier (FS-SCH-001).

It is transcribed from the member tables of chapters 1-8 and from the statements the catalogue
assigns to FS-SCH-001: 1.1, 1.3, 1.4, 1.6.1, 1.8, 2.1, 2.4, 3.1.1, 4.1.1, 4.3.1, 5.9.1, 6.7.1,
7.1, 8.1, 8.3-8.6 - and, for Core 0.2, from chapters 11-13: 3.1.3 (pattern), 11.1.1, 11.1.2,
12.1.1, 12.1.2, 12.5.1, 12.5.2, 13.2.1, 13.3.1, 13.5.1. Objects are closed; required members are
required; lengths are JSON integers (no fraction, no exponent - the parser keeps 1.0 and 1e0 apart
from 1) within 2^53 - 1.

And, for Core 0.3, a door or window type's `operation` and `clearOpening` and an opening's
`clearOpening` (8.4.2, 8.4.3); a level's `floorThickness` and `ceilingHeight` (1.8.4), a room's
`floor` and `ceiling` (15.1.1, 15.2.1) and a slab's `purpose` (6.7.2); and the `roofs` collection
(16.1.1) and the `stairs` collection (17.1.1, 17.2.1); a material's `metallic` and `roughness`, a
texture's maps, `offset` and `rotation`, an asset's `byteLength` and a wall's `finishes` (18.1.1,
18.2.1, 18.4.1, 18.5.1); and design options: the `optionSets` and `options` collections and the
`option` member of the elements that may be in one (19.1.1, 19.2.1); and a type's or a material's
`source` (8.1.3).

And, for Core 0.4, a stair's `minHeadroom` (17.1.3) and a winder stair's `newel` (17.2.3), and the `arc` of a
wall or a separator (21.1.1).

``check(doc, version)`` returns a list of problems; any problem is FS-SCH-001. ``version`` is the
draft whose schema applies: "0.1", "0.2", "0.3" or "0.4" (1.2.8).
"""

from __future__ import annotations

import re

MAX_LEN = 2 ** 53 - 1
ID_RE = re.compile(r'[A-Za-z0-9][A-Za-z0-9._-]{0,63}')
EXT_NAME = r'(?:FS|EXT|[A-Z0-9]{2,8})_[A-Za-z0-9]+'
EXT_RE = re.compile(EXT_NAME)
EXT_TERM_RE = re.compile(EXT_NAME + r':[a-z][A-Za-z0-9]*')
COLOR_RE = re.compile(r'#[0-9a-f]{6}')
SHA_RE = re.compile(r'[0-9a-f]{64}')
MEDIA_RE = re.compile(r'[A-Za-z0-9][A-Za-z0-9!#$&^_.+-]{0,126}/[A-Za-z0-9][A-Za-z0-9!#$&^_.+-]{0,126}')
VERSION_RE = re.compile(r'[0-9]+\.[0-9]+(\.[0-9]+)?(-[0-9A-Za-z.-]+)?')                       # 1.6.7
URI_RE = re.compile(r"https://(?:[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=-]|%[0-9A-Fa-f]{2})+")  # 8.6
NAME_RE = re.compile(r'[a-z][A-Za-z0-9]*')                                                # 12.5, 13.5
EDGE_RE = re.compile(r'0|[1-9][0-9]*')                                                    # 16.1 (0.3)

ROOM_FUNCTIONS = {'unspecified', 'sleeping', 'bath', 'kitchen', 'living', 'dining', 'office',
                  'laundry', 'utility', 'storage', 'circulation', 'mechanical', 'garage', 'exterior'}
LAYER_FUNCTIONS = {'core', 'substrate', 'insulation', 'membrane', 'airGap', 'finish'}
TOP_LEVEL = {'floorspec', 'project', 'site', 'buildings', 'levels', 'junctions', 'walls',
             'separators', 'openings', 'rooms', 'slabs', 'types', 'materials', 'assets',
             'extensionsUsed', 'extensionsRequired', 'extensions', 'extras'}
PURPOSES = ('workingSpace', 'fixtureClearance', 'swing', 'access')
DOOR_OPERATIONS = ('swing', 'doubleSwing', 'doubleActing', 'bypassSlide', 'pocket', 'surfaceSlide', 'bifold',
                   'overhead', 'cased')                                                       # 8.4 (0.3)
SLAB_PURPOSES = ('patio', 'deck', 'porch', 'stoop', 'landing', 'balcony', 'garage', 'walkway', 'driveway',
                 'equipmentPad', 'other')                                                     # 6.7 (0.3)
WINDOW_OPERATIONS = ('fixed', 'casement', 'awning', 'hopper', 'singleHung', 'doubleHung', 'horizontalSlider',
                     'tiltTurn', 'pivot')


def is_int(v) -> bool:
    return type(v) is int


class _Checker:
    def __init__(self, version: str = '0.1'):
        self.problems: list[str] = []
        self.version = version
        self.v02 = version in ('0.2', '0.3', '0.4')
        self.v03 = version in ('0.3', '0.4')
        self.v04 = version == '0.4'                 # what 0.4 adds: a stair's minHeadroom, a winder's newel

    def bad(self, path: str, why: str) -> None:
        self.problems.append(f'{path}: {why}')

    # ---- primitives
    def obj(self, v, path) -> bool:
        if not isinstance(v, dict):
            self.bad(path, 'not an object')
            return False
        return True

    def members(self, v: dict, path: str, allowed: dict, required=()):
        for k in required:
            if k not in v:
                self.bad(path, f'missing "{k}"')
        for k, x in v.items():
            if k not in allowed:
                self.bad(path, f'unknown member "{k}"')
            else:
                allowed[k](x, f'{path}/{k}')

    def length(self, v, path, lo=None, lo_strict=False):
        if not is_int(v) or abs(v) > MAX_LEN:
            self.bad(path, 'not a length')
            return
        if lo is not None and (v <= lo if lo_strict else v < lo):
            self.bad(path, 'out of range')

    def positive(self, v, path):
        self.length(v, path, 0, True)

    def nonneg(self, v, path):
        self.length(v, path, 0, False)

    def angle(self, v, path):
        if not is_int(v):
            self.bad(path, 'not an angle')

    def string(self, v, path, lo=0, hi=None):
        if not isinstance(v, str) or len(v) < lo or (hi is not None and len(v) > hi):
            self.bad(path, 'bad string')

    def name(self, v, path):
        self.string(v, path, 1, 200)

    def ref(self, v, path):
        if not isinstance(v, str) or not ID_RE.fullmatch(v):
            self.bad(path, 'not an ID')

    def enum(self, *values):
        def f(v, path):
            if not isinstance(v, str) or v not in values:
                self.bad(path, f'not one of {values}')
        return f

    def any_obj(self, v, path):
        self.obj(v, path)

    def ext_data(self, v, path):
        if self.obj(v, path):
            for k in v:
                if not EXT_RE.fullmatch(k):
                    self.bad(path, f'bad extension name "{k}"')

    def point(self, v, path):
        if not isinstance(v, list) or len(v) != 2:
            self.bad(path, 'not a point')
            return
        for i, x in enumerate(v):
            self.length(x, f'{path}/{i}')

    def polygon(self, v, path):
        if not isinstance(v, list) or len(v) < 3:
            self.bad(path, 'not a polygon')
            return
        for i, p in enumerate(v):
            self.point(p, f'{path}/{i}')

    def common(self):
        return {'name': self.name, 'extensions': self.ext_data, 'extras': self.any_obj}

    def optional(self):
        """19.2 (0.3): the members of an element that may be in an option - `common()` and `option`."""
        return {**self.common(), **({'option': self.ref} if self.v03 else {})}

    # ---- kinds
    def project(self, v, path):
        if self.obj(v, path):
            self.members(v, path, {'name': self.name,
                                   'description': lambda x, p: self.string(x, p, 0, 2000),
                                   'extras': self.any_obj}, ('name',))

    def site(self, v, path):
        if not self.obj(v, path):
            return

        def true_north(x, p):
            if not is_int(x) or not (-180_000_000 < x <= 180_000_000):
                self.bad(p, 'trueNorth out of range')

        def location(x, p):
            if not self.obj(x, p):
                return

            def lat(y, q):
                if not is_int(y) or not (-90_000_000 <= y <= 90_000_000):
                    self.bad(q, 'latitude out of range')

            def lon(y, q):
                if not is_int(y) or not (-180_000_000 < y <= 180_000_000):
                    self.bad(q, 'longitude out of range')
            self.members(x, p, {'latitude': lat, 'longitude': lon}, ('latitude', 'longitude'))

        self.members(v, path, {'trueNorth': true_north, 'location': location,
                               'boundary': self.polygon, 'extras': self.any_obj})

    def collection(self, kind_check):
        def f(v, path):
            if not self.obj(v, path):
                return
            for k, e in v.items():
                if not ID_RE.fullmatch(k):
                    self.bad(path, f'bad element ID "{k}"')
                kind_check(e, f'{path}/{k}')
        return f

    def building(self, v, path):
        if self.obj(v, path):
            self.members(v, path, self.common())

    def level(self, v, path):
        if self.obj(v, path):
            allowed = {'building': self.ref, 'elevation': self.length, 'height': self.positive, **self.common()}
            if self.v03:
                allowed.update(floorThickness=self.positive, ceilingHeight=self.positive)
            self.members(v, path, allowed, ('building', 'elevation', 'height'))

    def join(self, v, path):
        if not self.obj(v, path):
            return
        kind = v.get('kind')
        if kind == 'mitre':
            self.members(v, path, {'kind': self.enum('mitre')}, ('kind',))
        elif kind == 'butt':
            def through(x, p):
                if not isinstance(x, list) or not 1 <= len(x) <= 2:
                    self.bad(p, 'through must list one or two walls')
                    return
                for i, w in enumerate(x):
                    self.ref(w, f'{p}/{i}')
            self.members(v, path, {'kind': self.enum('butt'), 'through': through}, ('kind', 'through'))
        else:
            self.bad(path, 'bad join kind')

    def junction(self, v, path):
        if self.obj(v, path):
            self.members(v, path, {'level': self.ref, 'position': self.point, 'join': self.join,
                                   **self.optional()}, ('level', 'position'))

    def layers(self, v, path):
        if not isinstance(v, list) or len(v) < 1:
            self.bad(path, 'layers must be a non-empty array')
            return
        for i, layer in enumerate(v):
            p = f'{path}/{i}'
            if self.obj(layer, p):
                self.members(layer, p, {'thickness': self.positive,
                                        'function': self.enum(*sorted(LAYER_FUNCTIONS)),
                                        'material': self.ref}, ('thickness', 'function'))

    def wall(self, v, path):
        if not self.obj(v, path):
            return

        def base(x, p):
            if self.obj(x, p):
                self.members(x, p, {'level': self.ref, 'offset': self.length})

        def top(x, p):
            if not self.obj(x, p):
                return
            if 'level' in x and 'height' in x:
                self.bad(p, 'top has both level and height')
            elif 'height' in x:
                self.members(x, p, {'height': self.length}, ('height',))
            else:
                self.members(x, p, {'level': self.ref, 'offset': self.length}, ('level',))

        allowed = {'level': self.ref, 'start': self.ref, 'end': self.ref,
                   'type': self.ref, 'layers': self.layers,
                   'justification': self.enum('center', 'exteriorFace', 'interiorFace', 'coreFace'),
                   'base': base, 'top': top, **self.optional()}
        if self.v03:
            allowed['finishes'] = self.wall_finishes                        # 18.5.1 (0.3)
        if self.v04:
            allowed['arc'] = self.arc                                       # 21.1.1 (0.4)
        self.members(v, path, allowed, ('level', 'start', 'end'))

    def separator(self, v, path):
        if self.obj(v, path):
            self.members(v, path, {'level': self.ref, 'start': self.ref, 'end': self.ref, **self.optional(),
                                   **({'arc': self.arc} if self.v04 else {})},
                         ('level', 'start', 'end'))

    def arc(self, v, path):
        """21.1.1 (0.4): exactly a sagitta, a length that is not zero."""
        if self.obj(v, path):
            self.members(v, path, {'sagitta': self.length}, ('sagitta',))
            if is_int(v.get('sagitta')) and v['sagitta'] == 0:
                self.bad(f'{path}/sagitta', 'zero')

    def opening(self, v, path):
        if self.obj(v, path):
            allowed = {'wall': self.ref, 'offset': self.nonneg, 'width': self.positive,
                       'height': self.positive, 'sill': self.nonneg, 'fill': self.ref,
                       'hinge': self.enum('start', 'end'), 'swing': self.enum('left', 'right'),
                       **self.optional()}
            if self.v03:
                allowed['clearOpening'] = self.clear_opening(True)
            self.members(v, path, allowed, ('wall', 'offset'))

    def clear_opening(self, with_area):
        """8.4 (0.3): width and height greater than zero; an area, where allowed, from 1 to 2^53 - 1."""
        def f(v, path):
            if self.obj(v, path):
                allowed = {'width': self.positive, 'height': self.positive}
                if with_area:
                    allowed['area'] = self.integer(1, MAX_LEN)
                self.members(v, path, allowed, ('width', 'height'))
        return f

    def function(self, x, p):
        if not isinstance(x, str) or not (x in ROOM_FUNCTIONS or EXT_TERM_RE.fullmatch(x)):
            self.bad(p, 'bad room function')

    def room(self, v, path):
        if not self.obj(v, path):
            return
        allowed = {'level': self.ref, 'anchor': self.point, 'function': self.function,
                   'wallFinish': self.ref, 'floorFinish': self.ref, 'ceilingFinish': self.ref,
                   **self.optional()}
        if self.v02:
            allowed['brief'] = self.ref
        if self.v03:
            allowed.update(floor=self.floor, ceiling=self.ceiling)
        self.members(v, path, allowed, ('level', 'anchor'))

    # ---- Core 0.3: chapter 15
    def floor(self, v, path):
        if self.obj(v, path):
            self.members(v, path, {'offset': self.length, 'thickness': self.positive})

    def pitch(self, v, path):
        if self.obj(v, path):
            self.members(v, path, {'rise': self.integer(1, MAX_LEN), 'run': self.integer(1, MAX_LEN)}, ('rise', 'run'))

    def ridge(self, v, path):
        if not isinstance(v, list) or len(v) != 2:
            self.bad(path, 'a ridge is two points')
            return
        for i, p in enumerate(v):
            self.point(p, f'{path}/{i}')

    def ceiling(self, v, path):
        if not self.obj(v, path):
            return
        kind = v.get('kind')
        if kind == 'flat':
            self.members(v, path, {'kind': self.any_value, 'height': self.positive}, ('kind',))
        elif kind == 'tray':
            self.members(v, path, {'kind': self.any_value, 'height': self.positive, 'border': self.positive,
                                   'depth': self.positive}, ('kind', 'border', 'depth'))
        elif kind == 'vaulted':
            self.members(v, path, {'kind': self.any_value, 'height': self.positive, 'ridge': self.ridge,
                                   'pitch': self.pitch, 'slopes': self.enum('both', 'left', 'right')},
                         ('kind', 'ridge', 'pitch'))
        else:
            self.bad(path, 'bad ceiling kind')

    # ---- Core 0.2: chapters 11-13
    def integer(self, lo, hi):
        def f(x, p):
            if not is_int(x) or not lo <= x <= hi:
                self.bad(p, 'integer out of range')
        return f

    def triple(self, v, path):
        if not isinstance(v, list) or len(v) != 3:
            self.bad(path, 'not three lengths')
            return
        for i, x in enumerate(v):
            self.length(x, f'{path}/{i}')

    def box(self, v, path):
        if self.obj(v, path):
            self.members(v, path, {'min': self.triple, 'max': self.triple}, ('min', 'max'))

    def clearances(self, v, path):
        if not self.obj(v, path):
            return
        for k, e in v.items():
            p = f'{path}/{k}'
            if not NAME_RE.fullmatch(k):
                self.bad(path, f'bad envelope name "{k}"')
            if self.obj(e, p):
                self.members(e, p, {'purpose': self.enum(*PURPOSES), 'shape': self.enum('box'),
                                    'min': self.triple, 'max': self.triple}, ('purpose', 'shape', 'min', 'max'))

    def rotation(self, x, p):
        if not is_int(x) or not (-180_000_000 < x <= 180_000_000):
            self.bad(p, 'rotation out of range')

    def host(self, v, path):
        if not self.obj(v, path):
            return
        mode = v.get('mode')
        if mode == 'wallFace':
            self.members(v, path, {'mode': self.any_value, 'wall': self.ref, 'side': self.enum('left', 'right'),
                                   'offset': self.nonneg, 'height': self.nonneg},
                         ('mode', 'wall', 'side', 'offset', 'height'))
        elif mode == 'surface':
            self.members(v, path, {'mode': self.any_value, 'room': self.ref, 'surface': self.enum('floor', 'ceiling'),
                                   'position': self.point, 'rotation': self.rotation},
                         ('mode', 'room', 'surface', 'position'))
        elif mode == 'free':
            self.members(v, path, {'mode': self.any_value, 'level': self.ref, 'position': self.point,
                                   'rotation': self.rotation}, ('mode', 'level', 'position'))
        else:
            self.bad(path, 'bad host mode')

    def fallback(self, v, path):
        if self.obj(v, path):
            self.members(v, path, {'level': self.ref, 'box': self.box, 'asset': self.ref, 'symbol': self.ref},
                         ('level', 'box'))

    def ext_element(self, v, path):
        if not self.obj(v, path):
            return
        if 'fallback' not in v:
            self.bad(path, 'an extension element has no fallback')
        core = {'fallback': self.fallback, 'host': self.host, 'clearances': self.clearances,
                'name': self.name, 'extras': self.any_obj,
                **({'option': self.ref} if self.v03 else {})}
        for k, x in v.items():
            if k in core:
                core[k](x, f'{path}/{k}')

    def top_extensions(self, v, path):
        """1.6, 12.5: top-level extension data; in a 0.2 document, `collections` holds elements."""
        self.ext_data(v, path)
        if not self.v02 or not isinstance(v, dict):
            return
        for name, data in v.items():
            if not isinstance(data, dict) or 'collections' not in data:
                continue
            cp = f'{path}/{name}/collections'
            cs = data['collections']
            if not self.obj(cs, cp):
                continue
            for cname, coll in cs.items():
                if not NAME_RE.fullmatch(cname):
                    self.bad(cp, f'bad collection name "{cname}"')
                if not self.obj(coll, f'{cp}/{cname}'):
                    continue
                for eid, el in coll.items():
                    if not ID_RE.fullmatch(eid):
                        self.bad(f'{cp}/{cname}', f'bad element ID "{eid}"')
                    self.ext_element(el, f'{cp}/{cname}/{eid}')

    def program(self, v, path):
        if not self.obj(v, path):
            return

        def items(x, p):
            if not self.obj(x, p):
                return
            for k, it in x.items():
                q = f'{p}/{k}'
                if not ID_RE.fullmatch(k):
                    self.bad(p, f'bad item ID "{k}"')
                if self.obj(it, q):
                    self.members(it, q, {'function': self.function, 'name': self.name,
                                         'count': self.integer(1, MAX_LEN),
                                         'targetArea': self.integer(1, MAX_LEN), 'minArea': self.integer(1, MAX_LEN),
                                         'level': self.ref, 'extensions': self.ext_data, 'extras': self.any_obj},
                                 ('function',))

        def adjacency(x, p):
            if not isinstance(x, list):
                self.bad(p, 'not an array')
                return
            for i, a in enumerate(x):
                q = f'{p}/{i}'
                if self.obj(a, q):
                    self.members(a, q, {'a': self.ref, 'b': self.ref,
                                        'kind': self.enum('required', 'preferred', 'forbidden'),
                                        'weight': self.integer(1, 10)}, ('a', 'b', 'kind'))

        self.members(v, path, {'items': items, 'adjacency': adjacency})

    def slab(self, v, path):
        if self.obj(v, path):
            allowed = {'level': self.ref, 'boundary': self.polygon, 'thickness': self.positive,
                       'offset': self.length, 'material': self.ref, **self.optional()}
            if self.v03:
                allowed['purpose'] = self.enum(*SLAB_PURPOSES)
            self.members(v, path, allowed, ('level', 'boundary', 'thickness'))

    # ---- Core 0.3: chapter 16
    def roof(self, v, path):
        if not self.obj(v, path):
            return

        def edges(x, p):
            if not self.obj(x, p):
                return
            for k, e in x.items():
                q = f'{p}/{k}'
                if not EDGE_RE.fullmatch(k):
                    self.bad(q, 'not an edge index')
                if not self.obj(e, q):
                    continue
                self.members(e, q, {'gable': self.boolean, 'pitch': self.pitch, 'overhang': self.nonneg})
                if e.get('gable') is True and 'pitch' in e:
                    self.bad(q, 'a gable has no pitch')
        self.members(v, path, {'level': self.ref, 'footprint': self.polygon, 'height': self.length,
                               'pitch': self.pitch, 'overhang': self.nonneg, 'edges': edges,
                               'thickness': self.positive, 'material': self.ref, **self.optional()},
                     ('level', 'footprint'))

    def boolean(self, v, path):
        if not isinstance(v, bool):
            self.bad(path, 'not a boolean')

    # ---- Core 0.3: chapter 17
    def stair(self, v, path):
        if not self.obj(v, path):
            return
        count = self.integer(1, MAX_LEN)
        self.members(v, path, {'level': self.ref, 'to': self.ref, 'position': self.point, 'rotation': self.rotation,
                               'width': self.positive, 'tread': self.positive, 'risers': count,
                               'maxRiser': self.positive, 'form': self.stair_form, 'handrail': self.handrail,
                               **({'minHeadroom': self.positive} if self.v04 else {}),
                               **self.optional()}, ('level', 'to', 'position', 'width', 'tread'))
        if ('risers' in v) == ('maxRiser' in v):
            self.bad(path, 'a stair has exactly one of risers and maxRiser')

    def stair_form(self, v, path):
        if not self.obj(v, path):
            return
        count = self.integer(1, MAX_LEN)
        turn = self.enum('left', 'right')
        kind = v.get('kind')
        if kind == 'straight':
            self.members(v, path, {'kind': self.any_value}, ('kind',))
        elif kind == 'lShaped':
            self.members(v, path, {'kind': self.any_value, 'turn': turn, 'risersBeforeTurn': count},
                         ('kind', 'turn', 'risersBeforeTurn'))
        elif kind == 'uShaped':
            self.members(v, path, {'kind': self.any_value, 'turn': turn, 'risersBeforeTurn': count, 'gap': self.nonneg},
                         ('kind', 'turn', 'risersBeforeTurn'))
        elif kind == 'winder':
            allowed = {'kind': self.any_value, 'turn': turn, 'angle': self.enum('quarter', 'half'),
                       'risersBeforeTurn': count, 'winders': count}
            if v.get('angle') == 'half':
                allowed['gap'] = self.nonneg
            if self.v04:
                allowed['newel'] = self.positive                         # 17.2.3 (0.4)
            self.members(v, path, allowed, ('kind', 'turn', 'angle', 'risersBeforeTurn', 'winders'))
        elif kind == 'spiral':
            self.members(v, path, {'kind': self.any_value, 'turn': turn, 'diameter': self.positive,
                                   'sweep': self.integer(1, MAX_LEN)}, ('kind', 'turn', 'diameter', 'sweep'))
        else:
            self.bad(path, 'bad stair form')

    # ---- Core 0.3: chapter 19
    def option_set(self, v, path):
        if self.obj(v, path):
            self.members(v, path, {'primary': self.ref, **self.common()}, ('primary',))

    def option(self, v, path):
        if self.obj(v, path):
            self.members(v, path, {'set': self.ref, **self.common()}, ('set',))

    def handrail(self, v, path):
        if self.obj(v, path):
            self.members(v, path, {'height': self.positive, 'sides': self.enum('left', 'right', 'both')}, ('height',))

    def type_(self, v, path):
        if not self.obj(v, path):
            return
        kind = v.get('kind')
        if kind == 'wallType':
            self.members(v, path, {'kind': self.any_value, 'layers': self.layers, **self.common(),
                                   **({'source': self.source} if self.v03 else {})}, ('kind', 'layers'))
        elif kind in ('doorType', 'windowType'):
            allowed = {'kind': self.any_value, 'width': self.positive, 'height': self.positive,
                       'sill': self.nonneg, **self.common()}
            if self.v02:
                allowed['clearances'] = self.clearances
            if self.v03:
                allowed['operation'] = self.enum(*(DOOR_OPERATIONS if kind == 'doorType' else WINDOW_OPERATIONS))
                allowed['clearOpening'] = self.clear_opening(kind == 'windowType')
                allowed['source'] = self.source
            self.members(v, path, allowed, ('kind',))
        else:
            self.bad(path, 'bad type kind')

    def any_value(self, v, path):
        pass

    def source(self, v, path):
        """8.1 (0.3): the library item a type or a material was copied from (8.1.3)."""
        if not self.obj(v, path):
            return

        def library(x, p):
            if not isinstance(x, str) or not URI_RE.fullmatch(x):
                self.bad(p, 'bad library uri')

        def version(x, p):
            if not isinstance(x, str) or not VERSION_RE.fullmatch(x):
                self.bad(p, 'bad library version')
        self.members(v, path, {'library': library, 'version': version, 'item': self.ref},
                     ('library', 'version', 'item'))

    def material(self, v, path):
        if not self.obj(v, path):
            return
        if self.v03:                                                        # 18.1, 18.2 (0.3)
            return self.material_03(v, path)

        def color(x, p):
            if not isinstance(x, str) or not COLOR_RE.fullmatch(x):
                self.bad(p, 'bad colour')

        def texture(x, p):
            if not self.obj(x, p):
                return

            def size(y, q):
                if not isinstance(y, list) or len(y) != 2:
                    self.bad(q, 'bad texture size')
                    return
                for i, s in enumerate(y):
                    self.positive(s, f'{q}/{i}')
            self.members(x, p, {'asset': self.ref, 'size': size}, ('asset', 'size'))

        self.members(v, path, {'color': color, 'texture': texture, **self.common()})

    # ---- Core 0.3: chapter 18
    def material_03(self, v, path):
        def color(x, p):
            if not isinstance(x, str) or not COLOR_RE.fullmatch(x):
                self.bad(p, 'bad colour')

        def texture(x, p):
            if not self.obj(x, p):
                return

            def size(y, q):
                if not isinstance(y, list) or len(y) != 2:
                    self.bad(q, 'bad texture size')
                    return
                for i, s in enumerate(y):
                    self.positive(s, f'{q}/{i}')
            self.members(x, p, {'asset': self.ref, 'normal': self.ref, 'metallicRoughness': self.ref,
                                'occlusion': self.ref, 'size': size, 'offset': self.point,
                                'rotation': self.rotation}, ('size',))
            if not any(k in x for k in ('asset', 'normal', 'metallicRoughness', 'occlusion')):
                self.bad(p, 'a texture has no map')

        thousandths = self.integer(0, 1000)
        self.members(v, path, {'color': color, 'metallic': thousandths, 'roughness': thousandths,
                               'texture': texture, 'source': self.source, **self.common()})

    def wall_finishes(self, v, path):
        if not self.obj(v, path):
            return

        def region(x, p):
            if self.obj(x, p):
                self.members(x, p, {'from': self.nonneg, 'to': self.nonneg, 'bottom': self.nonneg,
                                    'top': self.nonneg, 'material': self.ref},
                             ('from', 'to', 'bottom', 'top', 'material'))

        def regions(x, p):
            if not isinstance(x, list):
                self.bad(p, 'not an array')
                return
            for i, r in enumerate(x):
                region(r, f'{p}/{i}')

        def face(x, p):
            if self.obj(x, p):
                self.members(x, p, {'material': self.ref, 'regions': regions})
        self.members(v, path, {'left': face, 'right': face})

    def asset(self, v, path):
        if not self.obj(v, path):
            return

        def rel_path(x, p):
            if not isinstance(x, str) or not x or x.startswith('/') or '\\' in x:
                self.bad(p, 'bad path')
                return
            segs = x.split('/')
            if any(s in ('', '.', '..') for s in segs) or ':' in segs[0]:
                self.bad(p, 'bad path')

        def uri(x, p):
            if not isinstance(x, str) or not URI_RE.fullmatch(x):
                self.bad(p, 'bad uri')

        def sha(x, p):
            if not isinstance(x, str) or not SHA_RE.fullmatch(x):
                self.bad(p, 'bad sha256')

        def media(x, p):
            if not isinstance(x, str) or not MEDIA_RE.fullmatch(x):
                self.bad(p, 'bad media type')

        allowed = {'path': rel_path, 'uri': uri, 'sha256': sha, 'mediaType': media, **self.common()}
        if self.v03:
            allowed['byteLength'] = self.integer(0, MAX_LEN)                 # 18.4.1 (0.3)
        self.members(v, path, allowed, ('sha256', 'mediaType'))
        if ('path' in v) == ('uri' in v):
            self.bad(path, 'an asset has exactly one of path and uri')

    def document(self, d):
        if not isinstance(d, dict):
            self.bad('', 'the document is not an object')
            return

        want = self.version

        def floorspec(x, p):
            if not isinstance(x, str) or x != want:
                self.bad(p, f'floorspec must be "{want}"')

        def version(ver, p):
            if not isinstance(ver, str) or not VERSION_RE.fullmatch(ver):
                self.bad(p, 'bad extension version')

        def ext_used(x, p):
            if self.obj(x, p):
                for k, ver in x.items():
                    if not EXT_RE.fullmatch(k):
                        self.bad(p, f'bad extension name "{k}"')
                    if self.v02 and isinstance(ver, dict):          # 12.1: a declaration object
                        def uri(y, q):
                            if not isinstance(y, str) or not URI_RE.fullmatch(y):
                                self.bad(q, 'bad schema uri')
                        self.members(ver, f'{p}/{k}', {'version': version, 'schema': uri}, ('version',))
                    else:
                        version(ver, f'{p}/{k}')

        def ext_required(x, p):
            if not isinstance(x, list):
                self.bad(p, 'not an array')
                return
            for i, n in enumerate(x):
                if not isinstance(n, str) or not EXT_RE.fullmatch(n):
                    self.bad(f'{p}/{i}', 'bad extension name')
            if len(set(map(str, x))) != len(x):
                self.bad(p, 'duplicate names')

        self.members(d, '', {
            'floorspec': floorspec, 'project': self.project, 'site': self.site,
            'buildings': self.collection(self.building), 'levels': self.collection(self.level),
            'junctions': self.collection(self.junction), 'walls': self.collection(self.wall),
            'separators': self.collection(self.separator), 'openings': self.collection(self.opening),
            'rooms': self.collection(self.room), 'slabs': self.collection(self.slab),
            'types': self.collection(self.type_), 'materials': self.collection(self.material),
            'assets': self.collection(self.asset), 'extensionsUsed': ext_used,
            'extensionsRequired': ext_required, 'extensions': self.top_extensions, 'extras': self.any_obj,
            **({'program': self.program} if self.v02 else {}),
            **({'roofs': self.collection(self.roof)} if self.v03 else {}),
            **({'stairs': self.collection(self.stair)} if self.v03 else {}),
            **({'optionSets': self.collection(self.option_set),
                'options': self.collection(self.option)} if self.v03 else {}),
        }, ('floorspec', 'project'))


def check(doc, version: str = '0.1') -> list[str]:
    c = _Checker(version)
    c.document(doc)
    return c.problems

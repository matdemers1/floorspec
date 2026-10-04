"""A hand-written structural check standing in for the schema tier (FS-SCH-001).

It is transcribed from the member tables of chapters 1-8 and from the statements the catalogue
assigns to FS-SCH-001: 1.1, 1.3, 1.4, 1.6.1, 1.8, 2.1, 2.4, 3.1.1, 4.1.1, 4.3.1, 5.9.1, 6.7.1,
7.1, 8.1, 8.3-8.6. Objects are closed; required members are required; lengths are JSON integers
(no fraction, no exponent - the parser keeps 1.0 and 1e0 apart from 1) within 2^53 - 1.

``check(doc)`` returns a list of problems; any problem is FS-SCH-001.
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

ROOM_FUNCTIONS = {'unspecified', 'sleeping', 'bath', 'kitchen', 'living', 'dining', 'office',
                  'laundry', 'utility', 'storage', 'circulation', 'mechanical', 'garage', 'exterior'}
LAYER_FUNCTIONS = {'core', 'substrate', 'insulation', 'membrane', 'airGap', 'finish'}
TOP_LEVEL = {'floorspec', 'project', 'site', 'buildings', 'levels', 'junctions', 'walls',
             'separators', 'openings', 'rooms', 'slabs', 'types', 'materials', 'assets',
             'extensionsUsed', 'extensionsRequired', 'extensions', 'extras'}


def is_int(v) -> bool:
    return type(v) is int


class _Checker:
    def __init__(self):
        self.problems: list[str] = []

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
            self.members(v, path, {'building': self.ref, 'elevation': self.length,
                                   'height': self.positive, **self.common()},
                         ('building', 'elevation', 'height'))

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
                                   **self.common()}, ('level', 'position'))

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

        self.members(v, path, {'level': self.ref, 'start': self.ref, 'end': self.ref,
                               'type': self.ref, 'layers': self.layers,
                               'justification': self.enum('center', 'exteriorFace', 'interiorFace', 'coreFace'),
                               'base': base, 'top': top, **self.common()},
                     ('level', 'start', 'end'))

    def separator(self, v, path):
        if self.obj(v, path):
            self.members(v, path, {'level': self.ref, 'start': self.ref, 'end': self.ref, **self.common()},
                         ('level', 'start', 'end'))

    def opening(self, v, path):
        if self.obj(v, path):
            self.members(v, path, {'wall': self.ref, 'offset': self.nonneg, 'width': self.positive,
                                   'height': self.positive, 'sill': self.nonneg, 'fill': self.ref,
                                   'hinge': self.enum('start', 'end'), 'swing': self.enum('left', 'right'),
                                   **self.common()}, ('wall', 'offset'))

    def room(self, v, path):
        if not self.obj(v, path):
            return

        def function(x, p):
            if not isinstance(x, str) or not (x in ROOM_FUNCTIONS or EXT_TERM_RE.fullmatch(x)):
                self.bad(p, 'bad room function')

        self.members(v, path, {'level': self.ref, 'anchor': self.point, 'function': function,
                               'wallFinish': self.ref, 'floorFinish': self.ref, 'ceilingFinish': self.ref,
                               **self.common()}, ('level', 'anchor'))

    def slab(self, v, path):
        if self.obj(v, path):
            self.members(v, path, {'level': self.ref, 'boundary': self.polygon, 'thickness': self.positive,
                                   'offset': self.length, 'material': self.ref, **self.common()},
                         ('level', 'boundary', 'thickness'))

    def type_(self, v, path):
        if not self.obj(v, path):
            return
        kind = v.get('kind')
        if kind == 'wallType':
            self.members(v, path, {'kind': self.any_value, 'layers': self.layers, **self.common()},
                         ('kind', 'layers'))
        elif kind in ('doorType', 'windowType'):
            self.members(v, path, {'kind': self.any_value, 'width': self.positive, 'height': self.positive,
                                   'sill': self.nonneg, **self.common()}, ('kind',))
        else:
            self.bad(path, 'bad type kind')

    def any_value(self, v, path):
        pass

    def material(self, v, path):
        if not self.obj(v, path):
            return

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

        self.members(v, path, {'path': rel_path, 'uri': uri, 'sha256': sha, 'mediaType': media,
                               **self.common()}, ('sha256', 'mediaType'))
        if ('path' in v) == ('uri' in v):
            self.bad(path, 'an asset has exactly one of path and uri')

    def document(self, d):
        if not isinstance(d, dict):
            self.bad('', 'the document is not an object')
            return

        def floorspec(x, p):
            if x != '0.1' or not isinstance(x, str):
                self.bad(p, 'floorspec must be "0.1"')

        def ext_used(x, p):
            if self.obj(x, p):
                for k, ver in x.items():
                    if not EXT_RE.fullmatch(k):
                        self.bad(p, f'bad extension name "{k}"')
                    if not isinstance(ver, str) or not VERSION_RE.fullmatch(ver):
                        self.bad(p, 'bad extension version')

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
            'extensionsRequired': ext_required, 'extensions': self.ext_data, 'extras': self.any_obj,
        }, ('floorspec', 'project'))


def check(doc) -> list[str]:
    c = _Checker()
    c.document(doc)
    return c.problems

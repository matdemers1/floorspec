"""Canonical form (9.2) and content hash (9.3).

Step 1 omits constant defaults, innermost first. The table of constant defaults below is
transcribed from the member tables of chapters 1, 5, 6, 7, 8, 11, 15, 17 and 19; typed properties (8.2) and
members whose default is derived are never omitted, and the content of extension data - including
Core 0.2's extension elements - and extras is never touched. Core 0.2 also writes a declaration
object without `schema` as its version string (12.1). None of the 0.2 rules can apply to a 0.1
document, nor the 0.3 rules (a room's `floor` and `ceiling`) to a 0.1 or 0.2 one, so one
canonicalizer serves every draft.

Step 2 writes ``JSON.stringify(sorted, null, 2)`` plus a line feed. The content hash is SHA-256
over the RFC 8785 (JCS) serialization of the step-1 document.
"""

from __future__ import annotations

import hashlib
import math

COLLECTIONS = ('buildings', 'levels', 'junctions', 'walls', 'separators', 'openings', 'rooms',
               'slabs', 'types', 'materials', 'assets', 'roofs', 'stairs')   # roofs, stairs: Core 0.3, chapters 16, 17
COLLECTIONS += ('optionSets', 'options')                                     # Core 0.3, chapter 19


def _is_int(v, n=None) -> bool:
    return type(v) is int and (n is None or v == n)


def _is_empty_obj(v) -> bool:
    return isinstance(v, dict) and not v


def _drop_common(e: dict) -> None:
    """`extensions` and `extras` default to {} on every element (1.4); only `{}` is removed."""
    for k in ('extensions', 'extras'):
        if k in e and _is_empty_obj(e[k]):
            del e[k]


def _copy(v):
    if isinstance(v, dict):
        return {k: _copy(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_copy(x) for x in v]
    return v


def omit_defaults(doc: dict) -> dict:
    """Step 1 of 9.2 on a valid document. Returns a new document."""
    d = _copy(doc)
    for e in d.get('junctions', {}).values():
        _drop_common(e)
        if e.get('join') == {'kind': 'mitre'}:          # constant default { "kind": "mitre" }
            del e['join']
    for e in d.get('walls', {}).values():
        _drop_common(e)
        if e.get('justification') == 'center':          # constant default "center"
            del e['justification']
        base = e.get('base')
        if isinstance(base, dict):
            if _is_int(base.get('offset'), 0):          # base.offset: constant 0
                del base['offset']
            # base.level defaults to the wall's own level: a derived default, never omitted
            if not base:                                # base: constant {}
                del e['base']
        top = e.get('top')
        if isinstance(top, dict) and 'level' in top and _is_int(top.get('offset'), 0):
            del top['offset']                           # top.offset: constant 0
        # `top` itself defaults to "absent: follows the level's height" - derived, never omitted
    for e in d.get('openings', {}).values():
        _drop_common(e)
        if e.get('hinge') == 'start':
            del e['hinge']
        if e.get('swing') == 'right':
            del e['swing']
        # width, height and sill are typed properties (8.2): never omitted, even "sill": 0
    for e in d.get('rooms', {}).values():
        _drop_common(e)
        if e.get('function') == 'unspecified':
            del e['function']
        floor = e.get('floor')                          # 15.1 (Core 0.3)
        if isinstance(floor, dict):
            if _is_int(floor.get('offset'), 0):         # floor.offset: constant 0
                del floor['offset']
            # floor.thickness defaults to its level's floorThickness: derived, never omitted
            if not floor:                               # floor: constant {}
                del e['floor']
        ceiling = e.get('ceiling')                      # 15.2 (Core 0.3)
        if isinstance(ceiling, dict):
            if ceiling.get('kind') == 'vaulted' and ceiling.get('slopes') == 'both':
                del ceiling['slopes']                   # slopes: constant "both"
            # height defaults to its level's ceilingHeight or height: derived, never omitted
            if ceiling == {'kind': 'flat'}:             # ceiling: constant { "kind": "flat" }
                del e['ceiling']
    for e in d.get('slabs', {}).values():
        _drop_common(e)
        if _is_int(e.get('offset'), 0):
            del e['offset']
    for e in d.get('roofs', {}).values():                # 16.1 (Core 0.3)
        _drop_common(e)
        if _is_int(e.get('overhang'), 0):               # overhang: constant 0
            del e['overhang']
        edges = e.get('edges')
        if isinstance(edges, dict):
            for k in list(edges):
                x = edges[k]
                if isinstance(x, dict):
                    if x.get('gable') is False:         # gable: constant false
                        del x['gable']
                    # an edge's pitch and overhang default to the roof's: derived, never omitted
                    if not x:                           # an edge: constant {}
                        del edges[k]
            if not edges:                               # edges: constant {}
                del e['edges']
    for c in ('buildings', 'levels', 'separators', 'types', 'materials', 'assets'):
        for e in d.get(c, {}).values():
            _drop_common(e)
    for c in ('optionSets', 'options'):                 # 19.1 (Core 0.3): only the common members
        for e in d.get(c, {}).values():
            _drop_common(e)
    for e in d.get('stairs', {}).values():              # 17.1, 17.2 (Core 0.3)
        _drop_common(e)
        if _is_int(e.get('rotation'), 0):               # rotation: constant 0
            del e['rotation']
        form = e.get('form')
        if isinstance(form, dict):
            if form.get('kind') in ('uShaped', 'winder') and _is_int(form.get('gap'), 0):
                del form['gap']                         # gap: constant 0
            if form == {'kind': 'straight'}:            # form: constant { "kind": "straight" }
                del e['form']
        rail = e.get('handrail')
        if isinstance(rail, dict) and rail.get('sides') == 'both':
            del rail['sides']                           # handrail.sides: constant "both"
    for e in d.get('types', {}).values():
        if _is_empty_obj(e.get('clearances')):         # 8.4: clearances {} (Core 0.2)
            del e['clearances']
    program = d.get('program')
    if isinstance(program, dict):                       # 11.1, 11.2 (Core 0.2)
        for it in program.get('items', {}).values():
            _drop_common(it)
            if _is_int(it.get('count'), 1):
                del it['count']
        for a in program.get('adjacency', []):
            if _is_int(a.get('weight'), 5):
                del a['weight']
        if _is_empty_obj(program.get('items')):
            del program['items']
        if program.get('adjacency') == []:
            del program['adjacency']
        if not program:
            del d['program']
    used = d.get('extensionsUsed')
    if isinstance(used, dict):                          # 12.1: { "version": v } is written v
        for k, v in list(used.items()):
            if isinstance(v, dict) and set(v) == {'version'}:
                used[k] = v['version']
    if isinstance(d.get('project'), dict) and _is_empty_obj(d['project'].get('extras')):
        del d['project']['extras']
    site = d.get('site')
    if isinstance(site, dict):
        if _is_int(site.get('trueNorth'), 0):
            del site['trueNorth']
        if _is_empty_obj(site.get('extras')):
            del site['extras']
        # `site` defaults to absent, not {}: an empty site is kept (the project has a site)
    for c in COLLECTIONS + ('extensionsUsed', 'extensions', 'extras'):
        if c in d and _is_empty_obj(d[c]):
            del d[c]
    if d.get('extensionsRequired') == []:
        del d['extensionsRequired']
    return d


# ---------------------------------------------------------------- RFC 8785 / ECMAScript writing

def es_number(v) -> str:
    """ECMAScript Number::toString of the IEEE 754 double nearest v (RFC 8785 3.2.2.3)."""
    if type(v) is int:
        if abs(v) <= 2 ** 53:
            return str(v)
        v = float(v)
    if math.isnan(v) or math.isinf(v):
        raise ValueError('RFC 8785 cannot serialize NaN or Infinity')
    if v == 0:
        return '0'
    if v < 0:
        return '-' + es_number(-v)
    r = repr(v)                                   # shortest round-trip digits
    mant, _, exp = r.partition('e')
    e10 = int(exp) if exp else 0
    if '.' in mant:
        ip, fp = mant.split('.')
    else:
        ip, fp = mant, ''
    digits = (ip + fp).lstrip('0')
    # value = 0.<ip fp> scaled: position of the decimal point relative to the digit string
    point = len(ip) + e10                         # digits before the point in ip+fp
    lead = len(ip + fp) - len((ip + fp).lstrip('0'))
    n = point - lead                              # x = 0.digits * 10^n
    digits = digits.rstrip('0')
    k = len(digits)
    if k <= n <= 21:
        return digits + '0' * (n - k)
    if 0 < n <= 21:
        return digits[:n] + '.' + digits[n:]
    if -6 < n <= 0:
        return '0.' + '0' * (-n) + digits
    e = n - 1
    sign = '+' if e >= 0 else '-'
    if k == 1:
        return digits + 'e' + sign + str(abs(e))
    return digits[0] + '.' + digits[1:] + 'e' + sign + str(abs(e))


def es_string(s: str) -> str:
    """JSON.stringify / RFC 8785 3.2.2.2 string serialization."""
    out = ['"']
    for ch in s:
        o = ord(ch)
        if ch == '"':
            out.append('\\"')
        elif ch == '\\':
            out.append('\\\\')
        elif ch == '\b':
            out.append('\\b')
        elif ch == '\f':
            out.append('\\f')
        elif ch == '\n':
            out.append('\\n')
        elif ch == '\r':
            out.append('\\r')
        elif ch == '\t':
            out.append('\\t')
        elif o < 0x20 or 0xD800 <= o <= 0xDFFF:
            out.append('\\u%04x' % o)
        else:
            out.append(ch)
    out.append('"')
    return ''.join(out)


def utf16_key(s: str) -> bytes:
    """Sort key comparing strings as sequences of UTF-16 code units (RFC 8785 3.2.3)."""
    return s.encode('utf-16-be', 'surrogatepass')


def _scalar(v) -> str:
    if v is True:
        return 'true'
    if v is False:
        return 'false'
    if v is None:
        return 'null'
    if isinstance(v, str):
        return es_string(v)
    return es_number(v)


def jcs(v) -> str:
    """RFC 8785 serialization."""
    if isinstance(v, dict):
        return '{' + ','.join(es_string(k) + ':' + jcs(v[k]) for k in sorted(v, key=utf16_key)) + '}'
    if isinstance(v, list):
        return '[' + ','.join(jcs(x) for x in v) + ']'
    return _scalar(v)


def pretty(v, depth: int = 0) -> str:
    """JSON.stringify(v, null, 2) of v with its object members sorted."""
    ind = '  ' * depth
    inner = '  ' * (depth + 1)
    if isinstance(v, dict):
        if not v:
            return '{}'
        items = [inner + es_string(k) + ': ' + pretty(v[k], depth + 1) for k in sorted(v, key=utf16_key)]
        return '{\n' + ',\n'.join(items) + '\n' + ind + '}'
    if isinstance(v, list):
        if not v:
            return '[]'
        return '[\n' + ',\n'.join(inner + pretty(x, depth + 1) for x in v) + '\n' + ind + ']'
    return _scalar(v)


def canonical_bytes(doc: dict) -> bytes:
    """The canonical form (9.2) of a valid document."""
    return (pretty(omit_defaults(doc)) + '\n').encode('utf-8')


def content_hash(doc: dict) -> str:
    """The content hash (9.3) of a valid document."""
    return hashlib.sha256(jcs(omit_defaults(doc)).encode('utf-8')).hexdigest()

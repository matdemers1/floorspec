"""The shapes of the request, a pack, a rule and a profile (spec/rules 1.1, 2.1, 3, 10.1), checked
by hand - independently of schema/rules/0.1/, which `pnpm schema:check` holds to the same verdicts
on every test of the suite - and the assurance pattern (2.5)."""

from __future__ import annotations

import re

MAXI = 2 ** 53 - 1
SEMVER = r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(-(0|[1-9][0-9]*|[0-9]*[A-Za-z-][0-9A-Za-z-]*)(\.(0|[1-9][0-9]*|[0-9]*[A-Za-z-][0-9A-Za-z-]*))*)?"
_CMP = r"(>=|>|<=|<|=|\^|~)?" + SEMVER
_SET = _CMP + r"( +" + _CMP + r")*"
RANGE = _SET + r"( +\|\| +" + _SET + r")*"
ID = r'[A-Za-z0-9][A-Za-z0-9._-]{0,63}'
PACK_NAME = r'[a-z0-9]+(-[a-z0-9]+)*'
EXT_NAME = r'(FS|EXT|[A-Z0-9]{2,8})_[A-Za-z0-9]+'
COLLECTION = r'[a-z][A-Za-z0-9]*'
CODE = r'[A-Z][A-Z0-9]*(-[A-Z0-9]+)*'
EDITION = r'[0-9A-Za-z][0-9A-Za-z.-]{0,15}'
SECTION = r'[^\u0000- \u007f-\u009f](?:[^\u0000-\u001f\u007f-\u009f]*[^\u0000- \u007f-\u009f])?'
DATE = r'[0-9]{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])'
HTTPS = r"https://(?:[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=-]|%[0-9A-Fa-f]{2})+"
MEASURE = r'[a-z][A-Za-z0-9]*'
OPS = ('<', '<=', '=', '!=', '>=', '>', 'in', 'has')
NOTICE = 'Floorspec findings are advisory. They are not a plan review, and the authority having jurisdiction decides.'

# 2.5: ECMAScript with the flag i; without the u flag, \b and case folding are ASCII's.
ASSURANCE = re.compile(r'\b(non-?)?compl(y|ies|ied|ying|iant|iance)\b|\b(meets?|pass(es|ed)?) (the )?codes?\b'
                       r'|\bup to codes?\b|\bcode[- ]approved\b', re.I | re.A)


def assures(text: str) -> bool:
    return ASSURANCE.search(text) is not None


def is_int(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _str(v, pattern=None, lo=None, hi=None) -> bool:
    if not isinstance(v, str):
        return False
    if lo is not None and len(v) < lo:
        return False
    if hi is not None and len(v) > hi:
        return False
    return pattern is None or re.fullmatch(pattern, v) is not None


def _obj(v, required, allowed) -> bool:
    return isinstance(v, dict) and all(k in v for k in required) and all(k in allowed for k in v)


def title(v):
    return _str(v, lo=1, hi=200)


def text(v):
    return _str(v, lo=1, hi=2000)


def citation(v) -> bool:
    return (_obj(v, ('code', 'edition', 'section'), ('code', 'edition', 'section', 'link'))
            and _str(v['code'], CODE, hi=32) and _str(v['edition'], EDITION) and _str(v['section'], SECTION, 1, 64)
            and ('link' not in v or _str(v['link'], HTTPS)))


def _value(v) -> bool:
    if is_int(v):
        return -MAXI <= v <= MAXI
    if isinstance(v, (str, bool)):
        return True
    return (isinstance(v, list) and len(v) >= 1
            and all((is_int(x) and -MAXI <= x <= MAXI) or isinstance(x, str) for x in v))


def test(v) -> bool:
    """3.8: exactly one of the four forms (the schema's oneOf; the forms' required members differ)."""
    if not isinstance(v, dict):
        return False
    if 'measure' in v or 'op' in v or 'value' in v:
        if not _obj(v, ('measure', 'op', 'value'), ('measure', 'args', 'op', 'value')):
            return False
        return (_str(v['measure'], MEASURE) and ('args' not in v or isinstance(v['args'], dict))
                and isinstance(v['op'], str) and v['op'] in OPS and _value(v['value']))
    for k in ('all', 'any'):
        if k in v:
            return (_obj(v, (k,), (k,)) and isinstance(v[k], list) and len(v[k]) >= 1
                    and all(test(t) for t in v[k]))
    if 'not' in v:
        return _obj(v, ('not',), ('not',)) and test(v['not'])
    return False


def rule(v) -> bool:
    if not _obj(v, ('title', 'citation', 'paraphrase', 'applies', 'requirement', 'severity', 'provenance'),
                ('title', 'citation', 'paraphrase', 'applies', 'select', 'requirement', 'exceptions', 'severity',
                 'provenance', 'extras')):
        return False
    a = v['applies']
    if not (_obj(a, ('to',), ('to', 'extension', 'collection', 'where')) and a['to'] in ('room', 'opening', 'element', 'level', 'stair')
            and ('extension' not in a or _str(a['extension'], EXT_NAME))
            and ('collection' not in a or _str(a['collection'], COLLECTION))
            and ('where' not in a or test(a['where']))):
        return False
    if 'select' in v:
        s = v['select']
        if not (_obj(s, ('from', 'need'), ('from', 'args', 'where', 'need'))
                and s['from'] in ('openings', 'elements', 'envelopes', 'rooms') and s['need'] in ('any', 'all')
                and ('args' not in s or isinstance(s['args'], dict)) and ('where' not in s or test(s['where']))):
            return False
    if 'exceptions' in v:
        ex = v['exceptions']
        if not (isinstance(ex, list) and all(_obj(e, ('when', 'note'), ('when', 'note')) and test(e['when']) and text(e['note'])
                                             for e in ex)):
            return False
    p = v['provenance']
    if not (_obj(p, ('verifiedBy', 'verifiedOn', 'edition'), ('verifiedBy', 'verifiedOn', 'edition', 'reviewed', 'note'))
            and title(p['verifiedBy']) and _str(p['verifiedOn'], DATE) and _str(p['edition'], EDITION)
            and ('note' not in p or text(p['note']))):
        return False
    if 'reviewed' in p:
        r = p['reviewed']
        if not (_obj(r, ('by', 'on'), ('by', 'on', 'credential')) and title(r['by']) and _str(r['on'], DATE)
                and ('credential' not in r or title(r['credential']))):
            return False
    return (title(v['title']) and citation(v['citation']) and text(v['paraphrase']) and test(v['requirement'])
            and v['severity'] in ('mayNotMeet', 'check', 'note') and ('extras' not in v or isinstance(v['extras'], dict)))


def coverage_entry(v) -> bool:
    return (_obj(v, ('code', 'edition', 'section', 'status'), ('code', 'edition', 'section', 'status', 'note'))
            and _str(v['code'], CODE, hi=32) and _str(v['edition'], EDITION) and _str(v['section'], SECTION, 1, 64)
            and v['status'] in ('addressed', 'partial', 'notAddressed') and ('note' not in v or text(v['note'])))


def pack(v) -> bool:
    if not _obj(v, ('floorspecRules', 'name', 'version', 'title', 'license', 'rules'),
                ('floorspecRules', 'name', 'version', 'title', 'license', 'description', 'rules', 'coverage', 'extras')):
        return False
    return (v['floorspecRules'] == '0.1' and _str(v['name'], PACK_NAME, hi=64) and _str(v['version'], SEMVER)
            and title(v['title']) and v['license'] == 'CC-BY-4.0' and ('description' not in v or text(v['description']))
            and isinstance(v['rules'], dict) and all(_str(k, ID) and rule(r) for k, r in v['rules'].items())
            and ('coverage' not in v or (isinstance(v['coverage'], list) and all(coverage_entry(c) for c in v['coverage'])))
            and ('extras' not in v or isinstance(v['extras'], dict)))


def pack_text(v):
    """2.5: the text of a pack."""
    out = [v['title']] + ([v['description']] if 'description' in v else [])
    for r in v['rules'].values():
        out += [r['title'], r['paraphrase']] + [e['note'] for e in r.get('exceptions', [])]
        if 'note' in r['provenance']:
            out.append(r['provenance']['note'])
    out += [c['note'] for c in v.get('coverage', []) if 'note' in c]
    return out


def profile(v) -> bool:
    if not _obj(v, ('floorspecRules', 'name', 'adopts'),
                ('floorspecRules', 'name', 'jurisdiction', 'adopts', 'asOf', 'packs', 'amendments', 'extras')):
        return False
    if not (v['floorspecRules'] == '0.1' and title(v['name']) and ('jurisdiction' not in v or title(v['jurisdiction']))
            and ('asOf' not in v or _str(v['asOf'], DATE)) and ('extras' not in v or isinstance(v['extras'], dict))):
        return False
    if not (isinstance(v['adopts'], list) and all(
            _obj(a, ('code', 'edition'), ('code', 'edition', 'effective')) and _str(a['code'], CODE, hi=32)
            and _str(a['edition'], EDITION) and ('effective' not in a or _str(a['effective'], DATE)) for a in v['adopts'])):
        return False
    if 'packs' in v and not (isinstance(v['packs'], list) and all(
            _obj(p, ('name', 'version'), ('name', 'version')) and _str(p['name'], PACK_NAME, hi=64) and _str(p['version'], RANGE)
            for p in v['packs'])):
        return False
    if 'amendments' in v:
        if not isinstance(v['amendments'], list):
            return False
        for a in v['amendments']:
            if not _obj(a, ('citation', 'withdraws'), ('citation', 'effective', 'withdraws', 'note')):
                return False
            c = a['citation']
            if not (_obj(c, ('authority', 'reference'), ('authority', 'reference', 'link')) and title(c['authority'])
                    and title(c['reference']) and ('link' not in c or _str(c['link'], HTTPS))):
                return False
            if not (('effective' not in a or _str(a['effective'], DATE)) and ('note' not in a or text(a['note']))
                    and isinstance(a['withdraws'], list) and len(a['withdraws']) >= 1
                    and all(_obj(w, ('pack', 'rule'), ('pack', 'rule')) and _str(w['pack'], PACK_NAME, hi=64) and _str(w['rule'], ID)
                            for w in a['withdraws'])):
                return False
    return True


def profile_ok(v) -> bool:
    """10.1.1: the schema, one date per code, one entry per pack, and no assurance in its text."""
    if not profile(v):
        return False
    seen = set()
    for a in v['adopts']:
        key = (a['code'], a.get('effective'))
        if key in seen:
            return False
        seen.add(key)
    names = [p['name'] for p in v.get('packs', [])]
    if len(set(names)) != len(names):
        return False
    texts = [v['name']] + ([v['jurisdiction']] if 'jurisdiction' in v else []) + [a['note'] for a in v.get('amendments', []) if 'note' in a]
    return not any(assures(t) for t in texts)


def request(v) -> bool:
    return (_obj(v, ('floorspecRules', 'packs'), ('floorspecRules', 'packs', 'profile', 'units'))
            and v['floorspecRules'] == '0.1' and isinstance(v['packs'], list)
            and ('units' not in v or v['units'] in ('imperial', 'metric')))

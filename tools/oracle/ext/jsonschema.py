"""The subset of JSON Schema 2020-12 the official extension schemas use, interpreted exactly.

The Core schema tier is transcribed by hand (tools/oracle/schema.py). An extension's schema is a
published file of its own (registry/<NAME>/*.schema.json), and the oracle reads that file: this is
a small, independent interpreter of the keywords those files use - `$ref` (local `#/$defs/...`),
`type`, `properties`, `required`, `additionalProperties`, `propertyNames`, `enum`, `minimum`,
`maximum`, `minLength`, `maxLength`, `pattern`, `items`, `minItems`, `uniqueItems` - and it refuses
a schema that uses any other keyword, so that a schema can never silently mean more than it checks.

A JSON integer is a Python int that is not a bool (jsonparse keeps `1.0` a float, 2.1.1); a string's
length is counted in code points.
"""

from __future__ import annotations

import json
import re

ANNOTATIONS = {'$schema', '$id', '$comment', '$defs', 'title', 'description', 'default'}
KEYWORDS = {'$ref', 'type', 'properties', 'required', 'additionalProperties', 'propertyNames', 'enum',
            'minimum', 'maximum', 'minLength', 'maxLength', 'pattern', 'items', 'minItems', 'uniqueItems'}


def _type_ok(v, t: str) -> bool:
    if t == 'object':
        return isinstance(v, dict)
    if t == 'array':
        return isinstance(v, list)
    if t == 'string':
        return isinstance(v, str)
    if t == 'integer':
        return isinstance(v, int) and not isinstance(v, bool)
    if t == 'boolean':
        return isinstance(v, bool)
    raise ValueError(f'type {t!r} is not in the subset')


def _same(a, b) -> bool:
    return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True) and type(a) is type(b)


class Schema:
    def __init__(self, root: dict):
        self.root = root
        self._check(root)

    def _check(self, node, where='#'):
        if not isinstance(node, dict):
            raise ValueError(f'{where}: not a schema')
        unknown = set(node) - ANNOTATIONS - KEYWORDS
        if unknown:
            raise ValueError(f'{where}: keywords outside the subset: {sorted(unknown)}')
        for k, sub in node.get('$defs', {}).items():
            self._check(sub, f'{where}/$defs/{k}')
        for k, sub in node.get('properties', {}).items():
            self._check(sub, f'{where}/properties/{k}')
        for k in ('additionalProperties', 'propertyNames', 'items'):
            if isinstance(node.get(k), dict):
                self._check(node[k], f'{where}/{k}')

    def _resolve(self, ref: str) -> dict:
        if not ref.startswith('#/$defs/'):
            raise ValueError(f'$ref {ref} is not local')
        return self.root['$defs'][ref[len('#/$defs/'):]]

    def errors(self, v, node=None, path='') -> list[str]:
        """Every violation, as 'pointer: why'; [] when v matches."""
        node = self.root if node is None else node
        out = []
        if '$ref' in node:
            out.extend(self.errors(v, self._resolve(node['$ref']), path))
        if 'type' in node and not _type_ok(v, node['type']):
            return out + [f'{path or "/"}: not of type {node["type"]}']
        if 'enum' in node and not any(_same(v, e) for e in node['enum']):
            out.append(f'{path or "/"}: not one of {node["enum"]}')
        if isinstance(v, int) and not isinstance(v, bool):
            if 'minimum' in node and v < node['minimum']:
                out.append(f'{path}: below {node["minimum"]}')
            if 'maximum' in node and v > node['maximum']:
                out.append(f'{path}: above {node["maximum"]}')
        if isinstance(v, str):
            n = len(v)
            if 'minLength' in node and n < node['minLength']:
                out.append(f'{path}: shorter than {node["minLength"]}')
            if 'maxLength' in node and n > node['maxLength']:
                out.append(f'{path}: longer than {node["maxLength"]}')
            if 'pattern' in node and not re.search(node['pattern'], v):
                out.append(f'{path}: does not match {node["pattern"]}')
        if isinstance(v, list):
            if 'minItems' in node and len(v) < node['minItems']:
                out.append(f'{path}: fewer than {node["minItems"]} items')
            if node.get('uniqueItems') and any(_same(a, b) for i, a in enumerate(v) for b in v[i + 1:]):
                out.append(f'{path}: items are not unique')
            if 'items' in node:
                for i, x in enumerate(v):
                    out.extend(self.errors(x, node['items'], f'{path}/{i}'))
        if isinstance(v, dict):
            for r in node.get('required', []):
                if r not in v:
                    out.append(f'{path or "/"}: missing {r}')
            props = node.get('properties', {})
            for k, x in v.items():
                p = f'{path}/{k.replace("~", "~0").replace("/", "~1")}'
                if 'propertyNames' in node:
                    out.extend(self.errors(k, node['propertyNames'], p))
                if k in props:
                    out.extend(self.errors(x, props[k], p))
                elif node.get('additionalProperties') is False:
                    out.append(f'{p}: not allowed')
                elif isinstance(node.get('additionalProperties'), dict):
                    out.extend(self.errors(x, node['additionalProperties'], p))
        return out

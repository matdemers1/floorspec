"""The US starter type library (library/us-starter/, Core 0.3 8.1), as the suites' author scripts read it.

The library is written by tools/us-library.ts; this module only reads its published index, so that
the conformance samples embed exactly the elements the library publishes, byte for byte.
"""
import copy
import json
import os

from tools.oracle.author_lib import REPO

VERSION = '0.1.0'
INDEX_PATH = os.path.join(REPO, 'library', 'us-starter', VERSION, 'index.json')

with open(INDEX_PATH, encoding='utf-8') as f:
    INDEX = json.load(f)
ITEMS = INDEX['items']


def element(item):
    """The item's element, exactly as it is embedded."""
    return copy.deepcopy(ITEMS[item]['element'])


def embed_ops(item):
    """The item's published Ops batch: addElement of each of its materials, then of the item."""
    return copy.deepcopy(ITEMS[item]['embed'])


def embed(doc, *items):
    """`doc` with `items` embedded under their library IDs, as their batches would add them, skipping an
    element the document already holds with the same content (re-embedding is idempotent)."""
    d = copy.deepcopy(doc)
    for item in items:
        for op in embed_ops(item):
            coll = d.setdefault(op['collection'], {})
            if op['id'] in coll:
                assert coll[op['id']] == op['element'], f'{op["id"]} is another element: embed it under another ID'
                continue
            coll[op['id']] = op['element']
    return d

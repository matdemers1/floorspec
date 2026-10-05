"""The document's one space of IDs, as Floorspec Ops 0.2 addresses it (Ops 0.2, Core 3.1.3).

In Ops 0.2 an **element** is an element of one of Core's eleven collections, a program item
(Core 11.1) or an extension element (Core 12.5). Program items and extension elements exist only
in a document that declares "0.2": in one that declares "0.1" the program is not a member and
top-level extension data is opaque (Core 1.2.4). Under Ops 0.1 only the eleven collections exist.

A place is where an element lives:

- ``(c,)`` for one of the eleven collections;
- ``('items',)`` for the program's items;
- ``('ext', extension, collection)`` for an extension's collection.

Only well-formed containers are read: a collection that is not an object holds nothing.
"""

from __future__ import annotations

from .faces import coll
from .request import COLLECTIONS
from .version import Profile

ITEMS = 'items'
EXT = 'ext'


def isd(v) -> bool:
    return isinstance(v, dict)


def declares_02(doc: dict) -> bool:
    return doc.get('floorspec') == '0.2'


def items(doc: dict, profile: Profile) -> dict:
    """The program's items, or {} where there are none to address."""
    if not (profile.v02 and declares_02(doc)):
        return {}
    program = doc.get('program')
    its = program.get('items') if isd(program) else None
    return its if isd(its) else {}


def ext_collections(doc: dict, profile: Profile):
    """(extension, collection name, collection) for every extension collection, by extension name and
    then collection name."""
    if not (profile.v02 and declares_02(doc)):
        return []
    out = []
    exts = doc.get('extensions')
    for x in sorted(exts) if isd(exts) else []:
        data = exts[x]
        cs = data.get('collections') if isd(data) else None
        for cname in sorted(cs) if isd(cs) else []:
            if isd(cs[cname]):
                out.append((x, cname, cs[cname]))
    return out


def ext_elements(doc: dict, profile: Profile):
    """(extension, collection name, ID, element) for every extension element."""
    return [(x, c, eid, el) for x, c, coll_ in ext_collections(doc, profile) for eid, el in sorted(coll_.items())]


def places(doc: dict, profile: Profile):
    """(place, container) for every place an element can be, in a fixed order: the eleven
    collections, the program's items, then the extension collections."""
    out = [((c,), coll(doc, c)) for c in COLLECTIONS]
    if profile.v02 and declares_02(doc):
        out.append(((ITEMS,), items(doc, profile)))
        out.extend(((EXT, x, c), coll_) for x, c, coll_ in ext_collections(doc, profile))
    return out


def locate(doc: dict, eid: str, profile: Profile):
    """(place, container) of the element `eid`, or None."""
    for place, container in places(doc, profile):
        if eid in container:
            return place, container
    return None


def kind(place) -> str:
    """The kind a selector restricts to: a collection name, 'items' or 'ext'."""
    return place[0]


def all_ids(doc: dict, profile: Profile) -> set:
    return {eid for _, container in places(doc, profile) for eid in container}


def host_of(el):
    h = el.get('host') if isd(el) else None
    return h if isd(h) else None

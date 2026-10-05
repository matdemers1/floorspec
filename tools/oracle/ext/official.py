"""The official extensions the oracle implements: FS_electrical, FS_plumbing, FS_mechanical,
FS_lowvoltage, FS_furniture and FS_structural 0.1.0 (registry/). Each is a module with NAME, VERSION, CODE, CORE (the
Core drafts it lists, 1.1), SCHEMA, SEVERITY and
invariants / lints / derive; validate.check takes a mapping of the ones a run implements. A module whose
data is also on core elements (FS_structural) has schema_errors(doc, data), its whole schema tier.

``evaluate(doc, known, implemented)`` is the extension tier of each specification's 1.2: for every
implemented extension the document uses at a version at which it is known, its schema
(FS-<CODE>-SCH-001), then - when that passed - its invariants. ``finish`` adds its lints and its
derived values for a valid document.
"""

from __future__ import annotations

from .. import registry as reg
from . import electrical, furniture, lowvoltage, mechanical, plumbing, structural
from .common import Context

OFFICIAL = {m.NAME: m for m in (electrical, plumbing, mechanical, lowvoltage, furniture, structural)}
SEVERITY = {code: sev for m in OFFICIAL.values() for code, sev in m.SEVERITY.items()}


def implemented(*names):
    return {n: OFFICIAL[n] for n in names}


def active(doc, known, implemented_):
    """The implemented extensions this document is evaluated against (each spec, 1.2)."""
    d = doc.d
    out = []
    for name, decl in sorted(d.get('extensionsUsed', {}).items()):
        m = implemented_.get(name)
        if m is None or d.get('floorspec') not in m.CORE:
            continue
        v = decl['version'] if isinstance(decl, dict) else decl
        if reg.entry_for(known, name, v) is not None and reg.compare(v, m.VERSION) == 0:
            out.append(m)
    return out


def evaluate(doc, known, implemented_):
    """(diagnostics, [(module, Context)]) of the extension tier."""
    ds, ctxs = [], []
    for m in active(doc, known, implemented_):
        ctx = Context(doc, m.NAME, m.SEVERITY)
        data = doc.d.get('extensions', {}).get(m.NAME, {})
        errors = m.schema_errors(doc, data) if hasattr(m, 'schema_errors') else m.SCHEMA.errors(data)
        if errors:
            ds.append(ctx.diag(f'FS-{m.CODE}-SCH-001'))
            continue
        ds.extend(m.invariants(ctx))
        ctxs.append((m, ctx))
    return ds, ctxs


def finish(ctxs):
    """(lints, derived extensions) for a valid document."""
    ds, derived = [], {}
    for m, ctx in ctxs:
        ds.extend(m.lints(ctx))
        derived[m.NAME] = m.derive(ctx)
    return ds, derived

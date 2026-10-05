# 6. Locks

A **lock** says something must not change: "the bathroom is final", "keep this wall nine feet
long", "keep the stair hall three feet wide". Locks are not part of the document — they are a
decision the person editing has made about it — so they arrive in the apply request's
`context.locks`, from whatever store keeps them, and they are checked after normalization against
the committed result.

## 6.1 Kinds of lock

| Lock | Holds while |
|---|---|
| `{ "element": ID }` | the element exists, in the same collection, with exactly its content in A; for a wall or separator, its start and end junctions are also unmoved; for a room, every junction on its face's outer cycle is also unmoved; for an extension element on a wall face, its wall's start and end junctions are also unmoved |
| `{ "length": wallID }` | the wall exists and its location line has the same length as in A |
| `{ "distance": [wallID, wallID] }` | both walls exist, are parallel, and the distance between their location lines is as in A |

An element lock on a program item or an extension element holds its content; on an outlet, it
also holds the wall the outlet is on, since an outlet follows its wall (2.7) — "this outlet is
final" means it does not move. Comparisons are exact: content in canonical form (constant defaults omitted, Core §9.2, values
equal when their RFC 8785 serializations are), positions as integers, lengths by their squares,
distances by squared cross products. Locks are checked only on a valid result: a result that is
both invalid and breaks a lock is rejected with its Core diagnostics alone (1.2, step 6).

A lock whose elements do not exist in A, a length or distance lock that names an element that is not a wall in A, or a distance lock between walls not parallel in A, MUST be rejected with `FS-OPS-010`. {#FS-OPS-6.1.1 MUST}

When the result breaks a lock in force, the applier MUST reject the batch with `FS-OPS-011`, naming the lock's elements. {#FS-OPS-6.1.2 MUST}

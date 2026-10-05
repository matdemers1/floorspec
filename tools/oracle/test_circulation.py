import itertools
import random
import unittest

from tools.oracle.circulation import _reach


def simple_paths(links, start, goal):
    """Every simple path from start to goal, by brute force."""
    out = []

    def walk(path):
        r = path[-1]
        if r == goal:
            out.append(list(path))
            return
        for s in sorted(links.get(r, ())):
            if s not in path:
                walk(path + [s])
    walk([start])
    return out


class ThroughSleeping(unittest.TestCase):
    def test_removal_matches_every_path_definition(self):
        # 14.3: "reachable only through another sleeping room" is defined as unreachable once every other
        # sleeping room is removed; it must agree with "every path from every entry passes through one".
        rnd = random.Random(14)
        for _ in range(400):
            n = rnd.randint(2, 7)
            nodes = [f'R{i}' for i in range(n)]
            links = {r: set() for r in nodes}
            for a, b in itertools.combinations(nodes, 2):
                if rnd.random() < 0.35:
                    links[a].add(b)
                    links[b].add(a)
            entries = {r for r in nodes if rnd.random() < 0.3}
            sleeping = {r for r in nodes if rnd.random() < 0.5}
            reach = _reach(set(nodes), links, entries)
            for r in sleeping:
                fast = r in reach and r not in _reach(set(nodes), links, entries, sleeping - {r})
                paths = [p for e in entries for p in simple_paths(links, e, r)]
                slow = bool(paths) and all(any(x in sleeping and x != r for x in p) for p in paths)
                self.assertEqual(fast, slow, (links, entries, sleeping, r))

    def test_reach_is_from_entries_only(self):
        links = {'A': {'B'}, 'B': {'A'}, 'C': set()}
        self.assertEqual(_reach({'A', 'B', 'C'}, links, {'A'}), {'A', 'B'})
        self.assertEqual(_reach({'A', 'B', 'C'}, links, set()), set())
        self.assertEqual(_reach({'A', 'B', 'C'}, links, {'A'}, frozenset({'A'})), set())


if __name__ == '__main__':
    unittest.main()

import random
import unittest

from kea2 import rtree


class TestBuiltinRTreeIndex(unittest.TestCase):

    def test_contains_returns_inserted_ids_inside_query_bounds(self):
        idx = rtree.index.Index()
        idx.insert(1, (5, 5, 5, 5))
        idx.insert(2, (15, 15, 15, 15))

        assert list(idx.contains((0, 0, 10, 10))) == [1]

    def test_contains_includes_boundary_points(self):
        idx = rtree.index.Index()
        idx.insert(1, (0, 0, 0, 0))
        idx.insert(2, (10, 10, 10, 10))

        assert list(idx.contains((0, 0, 10, 10))) == [1, 2]

    def test_delete_requires_matching_bounds(self):
        idx = rtree.index.Index()
        idx.insert(1, (5, 5, 5, 5))

        idx.delete(1, (0, 0, 10, 10))
        assert list(idx.contains((0, 0, 10, 10))) == [1]

        idx.delete(1, (5, 5, 5, 5))
        assert list(idx.contains((0, 0, 10, 10))) == []

    def test_contains_after_multiple_splits(self):
        idx = rtree.index.Index(max_entries=4)
        for i in range(40):
            idx.insert(i, (i, i, i, i))

        # R-tree query order is not part of the API contract; compare as a set.
        assert set(idx.contains((10, 10, 19, 19))) == set(range(10, 20))

    def test_matches_brute_force_randomized(self):
        # Compare against a linear-scan reference over a long random sequence of
        # inserts, deletes and point-in-rectangle queries.
        random.seed(99)
        idx = rtree.index.Index(max_entries=6)
        live = {}
        next_id = 0
        for _ in range(500):
            op = random.random()
            if op < 0.6:
                x, y = random.randint(0, 100), random.randint(0, 100)
                i = next_id
                next_id += 1
                b = (x, y, x, y)
                idx.insert(i, b)
                live[i] = b
            elif op < 0.85 and live:
                i = random.choice(list(live))
                idx.delete(i, live[i])
                del live[i]
            else:
                x1, x2 = sorted((random.randint(0, 100), random.randint(0, 100)))
                y1, y2 = sorted((random.randint(0, 100), random.randint(0, 100)))
                q = (x1, y1, x2, y2)
                expected = {
                    i
                    for i, (px, py, _, _) in live.items()
                    if x1 <= px <= x2 and y1 <= py <= y2
                }
                assert set(idx.contains(q)) == expected

    def test_matches_external_rtree_on_random_operations(self):
        # Differential test against the real rtree/libspatialindex if available.
        try:
            import rtree as external_rtree
        except ImportError:
            self.skipTest("external rtree package is not installed")

        random.seed(1234)
        for trial in range(20):
            cap = random.choice([4, 6, 10, 100])
            ext = external_rtree.index.Index(max_entries=cap)
            brt = rtree.index.Index(max_entries=cap)
            live = {}
            next_id = 0
            for _ in range(200):
                op = random.random()
                if op < 0.6:
                    x, y = random.randint(0, 100), random.randint(0, 100)
                    i = next_id
                    next_id += 1
                    b = (x, y, x, y)
                    ext.insert(i, b)
                    brt.insert(i, b)
                    live[i] = b
                elif op < 0.85 and live:
                    i = random.choice(list(live))
                    ext.delete(i, live[i])
                    brt.delete(i, live[i])
                    del live[i]
                else:
                    x1, x2 = sorted((random.randint(0, 100), random.randint(0, 100)))
                    y1, y2 = sorted((random.randint(0, 100), random.randint(0, 100)))
                    q = (x1, y1, x2, y2)
                    assert set(ext.contains(q)) == set(brt.contains(q))


if __name__ == "__main__":
    unittest.main()

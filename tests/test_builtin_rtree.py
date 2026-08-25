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

        assert list(idx.contains((10, 10, 19, 19))) == list(range(10, 20))


if __name__ == "__main__":
    unittest.main()

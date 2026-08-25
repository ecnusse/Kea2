"""
Pure-Python R-tree, a faithful port of libspatialindex's R*-tree algorithm.

This module replaces the external ``rtree`` package (a ctypes wrapper around
libspatialindex) so that Kea2 no longer depends on that native library. The
algorithm mirrors the R*-tree implementation in libspatialindex's
``src/rtree/RTree.cc``, ``Index.cc``, ``Node.cc`` and ``Leaf.cc`` as closely as
possible, so that query results (e.g. the widget-coverage checks in
``u2Driver.py``) are unchanged.

Only the subset of the ``rtree.index.Index`` API used by Kea2 is provided:
``Index()``, ``insert``, ``contains`` and ``delete``.

Default parameters match libspatialindex (RTree.cc constructor):

* leaf/index capacity: 100 (unified as ``max_entries``)
* fill factor: 0.7  ->  minimum load ``floor(capacity * 0.7)``
* tree variant: R*-tree
* reinsert factor: 0.3
* split distribution factor: 0.4
* near-minimum overlap factor: 32
* tight MBRs: True
* dimension: 2
"""

import sys
from typing import Iterator, List, Optional, Tuple

Bounds = Tuple[float, float, float, float]

# libspatialindex compares doubles with std::numeric_limits<double>::epsilon().
_EPSILON = sys.float_info.epsilon

# R*-tree constants (defaults in libspatialindex's RTree constructor).
_REINSERT_FACTOR = 0.3
_SPLIT_DISTRIBUTION_FACTOR = 0.4
_NEAR_MINIMUM_OVERLAP_FACTOR = 32
_TIGHT_MBRS = True


def _normalize_bounds(bounds) -> Bounds:
    if len(bounds) != 4:
        raise ValueError("Bounds must contain four coordinates")
    left, bottom, right, top = (float(v) for v in bounds)
    if left > right or bottom > top:
        raise ValueError("Bounds coordinates must not cross")
    return left, bottom, right, top


class _Region:
    """2D axis-aligned region, mirroring libspatialindex's ``Region``.

    ``low`` and ``high`` are (x, y) tuples. An entry with zero width/height
    (low == high) represents a point.
    """

    __slots__ = ("low", "high")

    def __init__(self, low: Tuple[float, float], high: Tuple[float, float]):
        self.low = (low[0], low[1])
        self.high = (high[0], high[1])

    @classmethod
    def from_bounds(cls, bounds) -> "_Region":
        left, bottom, right, top = _normalize_bounds(bounds)
        return cls((left, bottom), (right, top))

    def area(self) -> float:
        return (self.high[0] - self.low[0]) * (self.high[1] - self.low[1])

    def margin(self) -> float:
        # Region::getMargin: sum((high-low) * 2^(dim-1)); for 2D that is (w+h)*2.
        return ((self.high[0] - self.low[0]) + (self.high[1] - self.low[1])) * 2.0

    def intersects_region(self, other: "_Region") -> bool:
        return not (
            self.low[0] > other.high[0]
            or self.high[0] < other.low[0]
            or self.low[1] > other.high[1]
            or self.high[1] < other.low[1]
        )

    def contains_region(self, other: "_Region") -> bool:
        # Region::containsRegion: inclusive on all boundaries.
        return (
            self.low[0] <= other.low[0]
            and self.low[1] <= other.low[1]
            and self.high[0] >= other.high[0]
            and self.high[1] >= other.high[1]
        )

    def touches_region(self, other: "_Region") -> bool:
        # Region::touchesRegion: any boundary within epsilon counts as touching.
        for dim in range(2):
            if (
                abs(self.low[dim] - other.low[dim]) <= _EPSILON
                or abs(self.high[dim] - other.high[dim]) <= _EPSILON
            ):
                return True
        return False

    def intersecting_area(self, other: "_Region") -> float:
        # Region::getIntersectingArea: 0 if disjoint, else product of overlap lengths.
        ret = 1.0
        for dim in range(2):
            if self.low[dim] > other.high[dim] or self.high[dim] < other.low[dim]:
                return 0.0
            f1 = max(self.low[dim], other.low[dim])
            f2 = min(self.high[dim], other.high[dim])
            ret *= f2 - f1
        return ret

    def combine(self, other: "_Region") -> "_Region":
        # Region::combineRegion: min lows, max highs.
        return _Region(
            (min(self.low[0], other.low[0]), min(self.low[1], other.low[1])),
            (max(self.high[0], other.high[0]), max(self.high[1], other.high[1])),
        )

    def center(self) -> Tuple[float, float]:
        # Region::getCenter.
        return (
            (self.low[0] + self.high[0]) / 2.0,
            (self.low[1] + self.high[1]) / 2.0,
        )

    def __eq__(self, other: "_Region") -> bool:
        # Region::operator== uses an epsilon comparison per coordinate.
        for dim in range(2):
            if (
                self.low[dim] < other.low[dim] - _EPSILON
                or self.low[dim] > other.low[dim] + _EPSILON
                or self.high[dim] < other.high[dim] - _EPSILON
                or self.high[dim] > other.high[dim] + _EPSILON
            ):
                return False
        return True

    def __hash__(self) -> int:  # pragma: no cover - not used for hashing
        return hash((self.low, self.high))


class _Entry:
    """A single entry in a node.

    For a leaf node ``child`` is None and ``id`` is the data identifier. For an
    index node ``child`` is the subtree node it points to and ``mbr`` is that
    subtree's bounding region (``id`` is unused).
    """

    __slots__ = ("id", "mbr", "child")

    def __init__(self, id: int, mbr: _Region, child: Optional["_Node"] = None):
        self.id = id
        self.mbr = mbr
        self.child = child


class _Node:
    """An R-tree node, mirroring libspatialindex's ``Node``/``Leaf``/``Index``.

    ``children`` holds ``_Entry`` objects (leaf data entries or index child
    pointers). ``mbr`` is the node's bounding region; ``None`` means an empty
    node (libspatialindex's "infinite region").
    """

    __slots__ = ("level", "children", "mbr")

    def __init__(self, level: int):
        self.level = level
        self.children: List[_Entry] = []
        self.mbr: Optional[_Region] = None


class _Index:
    """An R*-tree index, mirroring libspatialindex's ``RTree`` facade.

    ``max_entries`` is the node capacity (libspatialindex's leaf and index
    capacities, both 100 by default); ``min_entries`` defaults to
    ``floor(max_entries * 0.7)`` (the fill factor).
    """

    def __init__(self, max_entries: int = 100, min_entries: Optional[int] = None):
        if max_entries < 4:
            raise ValueError("max_entries must be at least 4")
        self.capacity = max_entries
        self.minimum_load = min_entries if min_entries is not None else int(max_entries * 0.7)
        self.root = _Node(0)

    # ------------------------------------------------------------------
    # Public API (subset of rtree.index.Index used by Kea2)
    # ------------------------------------------------------------------

    def insert(self, id: int, bounds, obj=None) -> None:
        """Insert an entry with the given identifier and bounding region.

        ``bounds`` is ``(minx, miny, maxx, maxy)`` (rtree's interleaved order).
        """
        entry = _Entry(id, _Region.from_bounds(bounds))
        overflow_table = [0] * self.root.level
        path_buffer: List[_Node] = []
        node = self._choose_subtree(self.root, entry.mbr, 0, path_buffer)
        self._insert_into(node, entry, path_buffer, overflow_table)

    add = insert

    def contains(self, bounds, objects=False) -> Iterator[int]:
        """Yield ids of entries whose bounding regions are contained by ``bounds``.

        Mirrors libspatialindex's ``containsWhatQuery`` (the C API
        ``Index_Contains_id``); containment is inclusive of boundaries.
        """
        if objects:
            raise NotImplementedError("Object queries are not supported")
        query = _Region.from_bounds(bounds)
        yield from self._contains_query(query)

    def delete(self, id: int, bounds) -> None:
        """Delete the entry with the given id whose bounding region matches ``bounds``.

        Mirrors libspatialindex: the deletion only succeeds when both the id and
        the (epsilon-equal) bounding region match.
        """
        mbr = _Region.from_bounds(bounds)
        path_buffer: List[_Node] = []
        leaf = self._find_leaf(self.root, mbr, id, path_buffer)
        if leaf is not None:
            self._delete_from_leaf(leaf, id, mbr, path_buffer)

    # ------------------------------------------------------------------
    # Insertion (RTree::insertData_impl / Node::insertData)
    # ------------------------------------------------------------------

    def _insert_data_impl(self, entry: _Entry, level: int, overflow_table) -> None:
        path_buffer: List[_Node] = []
        node = self._choose_subtree(self.root, entry.mbr, level, path_buffer)
        self._insert_into(node, entry, path_buffer, overflow_table)

    def _choose_subtree(self, node: _Node, mbr: _Region, level: int, path_buffer: List[_Node]) -> _Node:
        # Index::chooseSubtree.
        if node.level == level:
            return node
        path_buffer.append(node)
        if node.level == 1:
            # Children are leaves: R*-tree uses least overlap.
            entry = self._find_least_overlap(node, mbr)
        else:
            entry = self._find_least_enlargement(node, mbr)
        return self._choose_subtree(entry.child, mbr, level, path_buffer)

    def _find_least_enlargement(self, node: _Node, r: _Region) -> _Entry:
        # Index::findLeastEnlargement.
        best = None
        area = float("inf")
        for e in node.children:
            combined = e.mbr.combine(r)
            a = e.mbr.area()
            enl = combined.area() - a
            if enl < area:
                area = enl
                best = e
            elif enl == area and (enl == float("inf") or a < best.mbr.area()):
                best = e
        return best

    def _find_least_overlap(self, node: _Node, r: _Region) -> _Entry:
        # Index::findLeastOverlap.
        entries = []
        for e in node.children:
            combined = e.mbr.combine(r)
            oa = e.mbr.area()
            ca = combined.area()
            entries.append((e, combined, oa, ca - oa))

        # Prefer the entry with minimum enlargement (area on tie).
        best = None
        me = float("inf")
        for e, combined, oa, enl in entries:
            if enl < me:
                me = enl
                best = (e, combined, oa, enl)
            elif enl == me and oa < best[2]:
                best = (e, combined, oa, enl)

        if me < -_EPSILON or me > _EPSILON:
            if len(entries) > _NEAR_MINIMUM_OVERLAP_FACTOR:
                entries.sort(key=lambda t: t[3])
                iterations = _NEAR_MINIMUM_OVERLAP_FACTOR
            else:
                iterations = len(entries)

            least_overlap = float("inf")
            for t in entries[:iterations]:
                e, combined, oa, enl = t
                dif = 0.0
                for other in node.children:
                    if e is not other:
                        f = combined.intersecting_area(other.mbr)
                        if f != 0.0:
                            dif += f - e.mbr.intersecting_area(other.mbr)
                if dif < least_overlap:
                    least_overlap = dif
                    best = t
                elif dif == least_overlap:
                    if enl == best[3]:
                        if oa < best[2]:
                            best = t
                    elif enl < best[3]:
                        best = t

        return best[0]

    def _insert_into(self, node: _Node, entry: _Entry, path_buffer: List[_Node], overflow_table) -> bool:
        """Node::insertData. Returns True if the tree above was adjusted."""
        if len(node.children) < self.capacity:
            adjusted = False
            # captured before insertEntry modifies node.mbr.
            contained = node.mbr is not None and node.mbr.contains_region(entry.mbr)
            self._insert_entry(node, entry)
            if (not contained) and path_buffer:
                parent = path_buffer.pop()
                self._adjust_tree(parent, node, path_buffer, force=False)
                adjusted = True
            return adjusted
        elif path_buffer and overflow_table[node.level] == 0:
            # R*-tree forced reinsertion.
            overflow_table[node.level] = 1
            keep, reinsert = self._reinsert_data(node, entry)
            node.children = keep
            node.mbr = self._recompute_mbr(node)
            parent = path_buffer.pop()
            self._adjust_tree(parent, node, path_buffer, force=True)
            for e in reinsert:
                self._insert_data_impl(e, node.level, overflow_table)
            return True
        else:
            left, right = self._split(node, entry)
            if not path_buffer:
                # The root split: grow a new root one level higher.
                new_root = _Node(node.level + 1)
                new_root.children = [
                    _Entry(-1, left.mbr, left),
                    _Entry(-1, right.mbr, right),
                ]
                new_root.mbr = self._recompute_mbr(new_root)
                self.root = new_root
            else:
                parent = path_buffer.pop()
                self._adjust_tree_two(parent, left, right, path_buffer, overflow_table)
            return True

    def _insert_entry(self, node: _Node, entry: _Entry) -> None:
        # Node::insertEntry: append and grow the node MBR.
        node.children.append(entry)
        if node.mbr is None:
            node.mbr = entry.mbr
        else:
            node.mbr = node.mbr.combine(entry.mbr)

    def _reinsert_data(self, node: _Node, entry: _Entry):
        """Node::reinsertData.

        Returns (keep, reinsert) -- the entry lists to keep in this node and to
        reinsert into the tree, chosen by distance from the node center.
        """
        entries = list(node.children) + [entry]  # capacity + 1
        center = node.mbr.center()
        n = len(entries)
        c_reinsert = int(n * _REINSERT_FACTOR)  # floor

        dists = []
        for e in entries:
            c = e.mbr.center()
            d = (center[0] - c[0]) ** 2 + (center[1] - c[1]) ** 2
            dists.append((d, e))
        dists.sort(key=lambda t: t[0])

        keep = [e for _, e in dists[: n - c_reinsert]]
        reinsert = [e for _, e in dists[n - c_reinsert:]]
        return keep, reinsert

    def _split(self, node: _Node, entry: _Entry):
        """Node::split -- R*-tree split (rstarSplit); returns (left, right) nodes.

        ``node`` is reused as the left node (mirroring how libspatialindex assigns
        ``n->m_identifier = m_identifier``), so the parent's entry pointing at the
        old node continues to identify the left half.
        """
        entries = list(node.children) + [entry]  # capacity + 1
        group1, group2 = self._rstar_split(entries)

        left = node
        right = _Node(node.level)
        left.children = []
        for i in group1:
            left.children.append(entries[i])
        for i in group2:
            right.children.append(entries[i])
        left.mbr = self._recompute_mbr(left)
        right.mbr = self._recompute_mbr(right)
        return left, right

    def _rstar_split(self, entries: List[_Entry]):
        """Node::rstarSplit -- choose split axis, then split point.

        ``entries`` is a list of ``capacity + 1`` entries (the last being the new
        one). Returns the two index lists (group1, group2).
        """
        capacity = self.capacity
        node_spf = int((capacity + 1) * _SPLIT_DISTRIBUTION_FACTOR)  # floor
        split_distribution = (capacity + 1) - 2 * node_spf + 2

        # chooseSplitAxis: minimize total margin over all distributions.
        minimum_margin = float("inf")
        split_axis = 0
        sort_order = 0  # 0 -> sort by low, 1 -> sort by high
        for dim in range(2):
            data_low = sorted(range(capacity + 1), key=lambda i: entries[i].mbr.low[dim])
            data_high = sorted(range(capacity + 1), key=lambda i: entries[i].mbr.high[dim])

            marginl = 0.0
            marginh = 0.0
            for u32 in range(1, split_distribution + 1):
                l = node_spf - 1 + u32
                bbl1 = entries[data_low[0]].mbr
                for idx in range(1, l):
                    bbl1 = bbl1.combine(entries[data_low[idx]].mbr)
                bbl2 = entries[data_low[l]].mbr
                for idx in range(l + 1, capacity + 1):
                    bbl2 = bbl2.combine(entries[data_low[idx]].mbr)

                bbh1 = entries[data_high[0]].mbr
                for idx in range(1, l):
                    bbh1 = bbh1.combine(entries[data_high[idx]].mbr)
                bbh2 = entries[data_high[l]].mbr
                for idx in range(l + 1, capacity + 1):
                    bbh2 = bbh2.combine(entries[data_high[idx]].mbr)

                marginl += bbl1.margin() + bbl2.margin()
                marginh += bbh1.margin() + bbh2.margin()

            margin = min(marginl, marginh)
            if margin < minimum_margin:
                minimum_margin = margin
                split_axis = dim
                sort_order = 0 if marginl < marginh else 1

        # chooseSplitIndex: on the chosen axis, minimize overlap (then area).
        if sort_order == 0:
            data = sorted(range(capacity + 1), key=lambda i: entries[i].mbr.low[split_axis])
        else:
            data = sorted(range(capacity + 1), key=lambda i: entries[i].mbr.high[split_axis])

        ma = float("inf")
        mo = float("inf")
        split_point = None
        for u32 in range(1, split_distribution + 1):
            l = node_spf - 1 + u32
            bb1 = entries[data[0]].mbr
            for idx in range(1, l):
                bb1 = bb1.combine(entries[data[idx]].mbr)
            bb2 = entries[data[l]].mbr
            for idx in range(l + 1, capacity + 1):
                bb2 = bb2.combine(entries[data[idx]].mbr)

            o = bb1.intersecting_area(bb2)
            if o < mo:
                split_point = u32
                mo = o
                ma = bb1.area() + bb2.area()
            elif o == mo:
                a = bb1.area() + bb2.area()
                if a < ma:
                    split_point = u32
                    ma = a

        l1 = node_spf - 1 + split_point
        return data[:l1], data[l1:]

    # ------------------------------------------------------------------
    # Tree adjustment after insertion (Index::adjustTree)
    # ------------------------------------------------------------------

    def _adjust_tree(self, parent: _Node, n: _Node, path_buffer: List[_Node], force: bool) -> None:
        # Index::adjustTree -- one modified child (n) whose MBR may have changed.
        child_entry = None
        for e in parent.children:
            if e.child is n:
                child_entry = e
                break

        b_contained = parent.mbr is not None and parent.mbr.contains_region(n.mbr)
        b_touches = parent.mbr is not None and parent.mbr.touches_region(child_entry.mbr)
        b_recompute = (not b_contained) or (b_touches and _TIGHT_MBRS)

        child_entry.mbr = n.mbr
        if b_recompute or force:
            parent.mbr = self._recompute_mbr(parent)

        if (b_recompute or force) and path_buffer:
            grandparent = path_buffer.pop()
            self._adjust_tree(grandparent, parent, path_buffer, force)

    def _adjust_tree_two(self, parent: _Node, n1: _Node, n2: _Node, path_buffer: List[_Node], overflow_table) -> None:
        # Index::adjustTree -- a split produced two children (n1, n2).
        child_entry = None
        for e in parent.children:
            if e.child is n1:
                child_entry = e
                break

        b_contained1 = parent.mbr is not None and parent.mbr.contains_region(n1.mbr)
        b_contained2 = parent.mbr is not None and parent.mbr.contains_region(n2.mbr)
        b_contained = b_contained1 and b_contained2
        b_touches = parent.mbr is not None and parent.mbr.touches_region(child_entry.mbr)
        b_recompute = (not b_contained) or (b_touches and _TIGHT_MBRS)

        child_entry.mbr = n1.mbr
        if b_recompute:
            parent.mbr = self._recompute_mbr(parent)

        # Insert n2 into the parent (may itself overflow -> reinsert/split).
        b_adjusted = self._insert_into(parent, _Entry(-1, n2.mbr, n2), path_buffer, overflow_table)

        if (not b_adjusted) and b_recompute and path_buffer:
            grandparent = path_buffer.pop()
            self._adjust_tree(grandparent, parent, path_buffer, force=False)

    # ------------------------------------------------------------------
    # Deletion (RTree::deleteData_impl / Leaf::deleteData / Node::condenseTree)
    # ------------------------------------------------------------------

    def _find_leaf(self, node: _Node, mbr: _Region, id: int, path_buffer: List[_Node]) -> Optional[_Node]:
        # Index/Leaf::findLeaf.
        if node.level == 0:
            for e in node.children:
                if e.id == id and e.mbr == mbr:
                    return node
            return None
        path_buffer.append(node)
        for e in node.children:
            if e.mbr.contains_region(mbr):
                leaf = self._find_leaf(e.child, mbr, id, path_buffer)
                if leaf is not None:
                    return leaf
        path_buffer.pop()
        return None

    def _delete_from_leaf(self, leaf: _Node, id: int, mbr: _Region, path_buffer: List[_Node]) -> None:
        # Leaf::deleteData.
        child = None
        for i, e in enumerate(leaf.children):
            if e.id == id and e.mbr == mbr:
                child = i
                break
        if child is None:
            return

        self._delete_entry(leaf, child)
        to_reinsert: List[_Node] = []
        self._condense_tree(leaf, to_reinsert, path_buffer)

        # Re-insert entries of eliminated (underflowed) nodes, each at its own level.
        while to_reinsert:
            n = to_reinsert.pop()
            for e in n.children:
                # The tree height may change during insertions.
                overflow_table = [0] * (self.root.level + 1)
                self._insert_data_impl(e, n.level, overflow_table)

    def _delete_entry(self, node: _Node, index: int) -> None:
        # Node::deleteEntry: swap with the last entry, shrink the MBR if needed.
        removed = node.children[index]
        if len(node.children) > 1 and index != len(node.children) - 1:
            node.children[index] = node.children[-1]
        node.children.pop()

        if len(node.children) == 0:
            node.mbr = None
        elif _TIGHT_MBRS and node.mbr.touches_region(removed.mbr):
            node.mbr = self._recompute_mbr(node)

    def _condense_tree(self, node: _Node, to_reinsert: List[_Node], path_buffer: List[_Node]) -> None:
        # Node::condenseTree.
        if not path_buffer:
            # Eliminate the root if it has only one child.
            if node.level != 0 and len(node.children) == 1:
                self.root = node.children[0].child
            elif _TIGHT_MBRS:
                node.mbr = self._recompute_mbr(node)
            return

        parent = path_buffer.pop()
        child_index = None
        for i, e in enumerate(parent.children):
            if e.child is node:
                child_index = i
                break

        if len(node.children) < self.minimum_load:
            # Underflow: remove the entry from the parent, reinsert this node's entries.
            self._delete_entry(parent, child_index)
            to_reinsert.append(node)
        else:
            parent.children[child_index].mbr = node.mbr
            if _TIGHT_MBRS:
                parent.mbr = self._recompute_mbr(parent)

        self._condense_tree(parent, to_reinsert, path_buffer)

    # ------------------------------------------------------------------
    # Queries (RTree::containsWhatQuery)
    # ------------------------------------------------------------------

    def _contains_query(self, query: _Region) -> Iterator[int]:
        stack = [self.root]
        while stack:
            n = stack.pop()
            if n.level == 0:
                for e in n.children:
                    if query.contains_region(e.mbr):
                        yield e.id
            elif n.mbr is not None and query.contains_region(n.mbr):
                # Whole subtree is contained: emit everything below it.
                yield from self._visit_subtree(n)
            elif n.mbr is not None and query.intersects_region(n.mbr):
                stack.extend(e.child for e in n.children)

    def _visit_subtree(self, node: _Node) -> Iterator[int]:
        # RTree::visitSubTree -- yield the ids of all data entries in the subtree.
        stack = [node]
        while stack:
            n = stack.pop()
            if n.level == 0:
                for e in n.children:
                    yield e.id
            else:
                stack.extend(e.child for e in n.children)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _recompute_mbr(self, node: _Node) -> Optional[_Region]:
        if not node.children:
            return None
        lows0 = [e.mbr.low[0] for e in node.children]
        lows1 = [e.mbr.low[1] for e in node.children]
        highs0 = [e.mbr.high[0] for e in node.children]
        highs1 = [e.mbr.high[1] for e in node.children]
        return _Region(
            (min(lows0), min(lows1)),
            (max(highs0), max(highs1)),
        )


class index:
    """Namespace mirroring the external ``rtree.index`` module."""

    Index = _Index
    Rtree = _Index

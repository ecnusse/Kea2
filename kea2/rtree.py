from dataclasses import dataclass, field
from typing import Iterator, List, Optional, Tuple, Union


Bounds = Tuple[float, float, float, float]


def _normalize_bounds(bounds) -> Bounds:
    if len(bounds) != 4:
        raise ValueError("Bounds must contain four coordinates")
    left, bottom, right, top = (float(v) for v in bounds)
    if left > right or bottom > top:
        raise ValueError("Bounds coordinates must not cross")
    return left, bottom, right, top


def _area(bounds: Bounds) -> float:
    return max(0.0, bounds[2] - bounds[0]) * max(0.0, bounds[3] - bounds[1])


def _union(a: Bounds, b: Bounds) -> Bounds:
    return (
        min(a[0], b[0]),
        min(a[1], b[1]),
        max(a[2], b[2]),
        max(a[3], b[3]),
    )


def _contains(outer: Bounds, inner: Bounds) -> bool:
    return (
        outer[0] <= inner[0]
        and outer[1] <= inner[1]
        and outer[2] >= inner[2]
        and outer[3] >= inner[3]
    )


def _intersects(a: Bounds, b: Bounds) -> bool:
    return not (a[2] < b[0] or a[0] > b[2] or a[3] < b[1] or a[1] > b[3])


def _enlargement(bounds: Bounds, extra: Bounds) -> float:
    return _area(_union(bounds, extra)) - _area(bounds)


@dataclass
class _Entry:
    item_id: int
    bounds: Bounds


@dataclass
class _Node:
    leaf: bool
    entries: List[Union[_Entry, "_Node"]] = field(default_factory=list)
    parent: Optional["_Node"] = None
    bounds: Optional[Bounds] = None

    def recalculate_bounds(self) -> None:
        if not self.entries:
            self.bounds = None
            return
        bounds = self.entries[0].bounds
        for entry in self.entries[1:]:
            bounds = _union(bounds, entry.bounds)
        self.bounds = bounds


class _Index:
    def __init__(self, max_entries: int = 16, min_entries: Optional[int] = None):
        if max_entries < 2:
            raise ValueError("max_entries must be at least 2")
        self.max_entries = max_entries
        self.min_entries = min_entries if min_entries is not None else max_entries // 2
        self.root = _Node(leaf=True)

    def insert(self, item_id: int, bounds, obj=None) -> None:
        entry = _Entry(item_id, _normalize_bounds(bounds))
        leaf = self._choose_leaf(self.root, entry.bounds)
        leaf.entries.append(entry)
        self._adjust_tree(leaf)

    def contains(self, bounds, objects=False) -> Iterator[int]:
        if objects:
            raise NotImplementedError("Object queries are not supported")
        query_bounds = _normalize_bounds(bounds)
        yield from self._contains_node(self.root, query_bounds)

    def delete(self, item_id: int, bounds) -> None:
        entry_bounds = _normalize_bounds(bounds)
        leaf = self._find_leaf(self.root, item_id, entry_bounds)
        if leaf is None:
            return
        for i, entry in enumerate(leaf.entries):
            if isinstance(entry, _Entry) and entry.item_id == item_id and entry.bounds == entry_bounds:
                del leaf.entries[i]
                self._adjust_after_delete(leaf)
                return

    def _choose_leaf(self, node: _Node, bounds: Bounds) -> _Node:
        if node.leaf:
            return node
        child = min(
            node.entries,
            key=lambda entry: (
                _enlargement(entry.bounds, bounds),
                _area(entry.bounds),
                len(entry.entries),
            ),
        )
        return self._choose_leaf(child, bounds)

    def _contains_node(self, node: _Node, bounds: Bounds) -> Iterator[int]:
        if node.bounds is None or not _intersects(bounds, node.bounds):
            return
        if node.leaf:
            for entry in node.entries:
                if _contains(bounds, entry.bounds):
                    yield entry.item_id
            return
        for child in node.entries:
            if child.bounds is not None and _intersects(bounds, child.bounds):
                yield from self._contains_node(child, bounds)

    def _find_leaf(self, node: _Node, item_id: int, bounds: Bounds) -> Optional[_Node]:
        if node.bounds is None or not _contains(node.bounds, bounds):
            return None
        if node.leaf:
            for entry in node.entries:
                if isinstance(entry, _Entry) and entry.item_id == item_id and entry.bounds == bounds:
                    return node
            return None
        for child in node.entries:
            leaf = self._find_leaf(child, item_id, bounds)
            if leaf is not None:
                return leaf
        return None

    def _adjust_tree(self, node: _Node) -> None:
        while True:
            node.recalculate_bounds()
            if len(node.entries) <= self.max_entries:
                if node.parent is None:
                    return
                node = node.parent
                continue

            sibling = self._split_node(node)
            if node.parent is None:
                self.root = _Node(leaf=False, entries=[node, sibling])
                node.parent = self.root
                sibling.parent = self.root
                self.root.recalculate_bounds()
                return

            node.parent.entries.append(sibling)
            sibling.parent = node.parent
            node = node.parent

    def _adjust_after_delete(self, node: _Node) -> None:
        while node is not None:
            node.recalculate_bounds()
            if node is self.root:
                if not node.leaf and len(node.entries) == 1:
                    self.root = node.entries[0]
                    self.root.parent = None
                return
            node = node.parent

    def _split_node(self, node: _Node) -> _Node:
        entries = node.entries
        seed1, seed2 = self._pick_seeds(entries)
        group1 = [entries[seed1]]
        group2 = [entries[seed2]]
        remaining = [entry for i, entry in enumerate(entries) if i not in {seed1, seed2}]

        bounds1 = group1[0].bounds
        bounds2 = group2[0].bounds

        while remaining:
            if len(group1) + len(remaining) == self.min_entries:
                group1.extend(remaining)
                break
            if len(group2) + len(remaining) == self.min_entries:
                group2.extend(remaining)
                break

            entry = self._pick_next(remaining, bounds1, bounds2)
            remaining.remove(entry)
            enlargement1 = _enlargement(bounds1, entry.bounds)
            enlargement2 = _enlargement(bounds2, entry.bounds)
            if enlargement1 < enlargement2:
                group1.append(entry)
                bounds1 = _union(bounds1, entry.bounds)
            elif enlargement2 < enlargement1:
                group2.append(entry)
                bounds2 = _union(bounds2, entry.bounds)
            elif _area(bounds1) < _area(bounds2):
                group1.append(entry)
                bounds1 = _union(bounds1, entry.bounds)
            elif _area(bounds2) < _area(bounds1):
                group2.append(entry)
                bounds2 = _union(bounds2, entry.bounds)
            elif len(group1) <= len(group2):
                group1.append(entry)
                bounds1 = _union(bounds1, entry.bounds)
            else:
                group2.append(entry)
                bounds2 = _union(bounds2, entry.bounds)

        node.entries = group1
        sibling = _Node(leaf=node.leaf, entries=group2, parent=node.parent)
        for entry in node.entries:
            if isinstance(entry, _Node):
                entry.parent = node
        for entry in sibling.entries:
            if isinstance(entry, _Node):
                entry.parent = sibling
        node.recalculate_bounds()
        sibling.recalculate_bounds()
        return sibling

    def _pick_seeds(self, entries) -> Tuple[int, int]:
        worst_waste = None
        seeds = (0, 1)
        for i, entry1 in enumerate(entries[:-1]):
            for j in range(i + 1, len(entries)):
                entry2 = entries[j]
                waste = _area(_union(entry1.bounds, entry2.bounds)) - _area(entry1.bounds) - _area(entry2.bounds)
                if worst_waste is None or waste > worst_waste:
                    worst_waste = waste
                    seeds = (i, j)
        return seeds

    def _pick_next(self, entries, bounds1: Bounds, bounds2: Bounds):
        return max(entries, key=lambda entry: abs(_enlargement(bounds1, entry.bounds) - _enlargement(bounds2, entry.bounds)))


class index:
    Index = _Index

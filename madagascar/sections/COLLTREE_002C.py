import io
import struct
from dataclasses import dataclass, field
from typing import Any, BinaryIO, override
from collections.abc import Sequence

from madagascar.lib.parser import Parser
from madagascar.lib.rwConstants import RWSectionType
from madagascar.lib.rw_basics import (
    RW_Section,
    RW_Triangle,
    RWHeader,
    expect_chunk_type_or_raise,
    Vector3,
)


@dataclass
class RW_CollTreeFlags:
    rpCOLLTREE_USEMAP: bool = False

    @staticmethod
    def decode(value: int) -> "RW_CollTreeFlags":
        f = RW_CollTreeFlags()
        f.rpCOLLTREE_USEMAP = bool(value & 0x01)
        return f

    def encode(self) -> int:
        v = 0
        if self.rpCOLLTREE_USEMAP:
            v |= 0x01
        return v


rpCOLLSECTOR_TYPE_NEG = 0x01
rpCOLLSECTOR_TYPE_AXISMASK = 0x08 | 0x04  # = 0x0C
rpCOLLSECTOR_TYPE_X = 0x00
rpCOLLSECTOR_TYPE_Y = 0x04
rpCOLLSECTOR_TYPE_Z = 0x08

# Allow 16 special contents values
rpCOLLSECTOR_CONTENTS_MAXCOUNT = 0xEF
rpCOLLSECTOR_CONTENTS_SPLIT = 0xFF

rpCOLLTREE_MAXDEPTH = 32
_MIN_POLYGONS_FOR_SPLIT = 4
_MAXCLOSESTCHECK = 50
_RANGEEPS = 0.0001

_AXIS_TYPE = (rpCOLLSECTOR_TYPE_X, rpCOLLSECTOR_TYPE_Y, rpCOLLSECTOR_TYPE_Z)


@dataclass
class RpCollSector:
    collsec_type: int = field(default=0)
    contents: int = field(default=0)
    index: int = field(default=0)
    value: float = field(default=0.0)

    @property
    def axis(self) -> int:
        """0 = X, 1 = Y, 2 = Z."""
        return (self.collsec_type & rpCOLLSECTOR_TYPE_AXISMASK) >> 2

    @property
    def is_negative(self) -> bool:
        """True for the left child: `value` is an upper bound, not a lower one."""
        return bool(self.collsec_type & rpCOLLSECTOR_TYPE_NEG)

    @property
    def is_split(self) -> bool:
        return self.contents == rpCOLLSECTOR_CONTENTS_SPLIT

    @classmethod
    def read(cls, parser: Parser) -> "RpCollSector":
        sec = cls()
        sec.collsec_type = parser.readUint8()
        sec.contents = parser.readUint8()
        sec.index = parser.readUint16()
        sec.value = parser.readFloat()
        return sec

    def pack(self) -> bytes:
        return struct.pack(
            "<BBHf", self.collsec_type, self.contents, self.index, self.value
        )


@dataclass
class RpCollSplit:
    leftSector: RpCollSector = field(default_factory=RpCollSector)
    rightSector: RpCollSector = field(default_factory=RpCollSector)

    @classmethod
    def read(cls, parser: Parser) -> "RpCollSplit":
        split = cls()
        split.leftSector = RpCollSector.read(parser)
        split.rightSector = RpCollSector.read(parser)
        return split

    def pack(self) -> bytes:
        return self.leftSector.pack() + self.rightSector.pack()


# ---------------------------------------------------------------------------
#  Port of rwsrc-v3.7.0.2/collis/ctbuild.c
# ---------------------------------------------------------------------------


def _average_tree_depth(n: int) -> float:
    """AverageTreeDepth() - mean leaf depth of an ideally balanced tree."""
    d = n.bit_length() - 1
    return (d + 2) - float(1 << (d + 1)) / n


def _fuzzy_extent_score(extent: float, max_extent: float) -> float:
    """FuzzyExtentScore() - bias against cutting the short axis (cubes > slabs)."""
    v = extent / max_extent
    v = 1.0 if v > 0.5 else 0.5 + v
    return 1.0 / v


class _CollTreeBuilder:
    """Recursive BIH build. Mirrors BuildTreeGenerate() / FindDividingPlane()."""

    __slots__ = ("polys", "tris", "verts", "vflag")

    def __init__(
        self,
        verts: Sequence[tuple[float, float, float]],
        tris: Sequence[tuple[int, int, int]],
    ) -> None:
        self.verts = verts
        self.tris = tris
        self.polys = list(range(len(tris)))  # polys[i] -> original triangle index
        self.vflag = [0] * len(verts)

    # -- SetSortVertices --------------------------------------------------
    def _sort_vertices(self, off: int, cnt: int) -> list[int]:
        seen: set[int] = set()
        for k in range(off, off + cnt):
            seen.update(self.tris[self.polys[k]])
        return sorted(seen)

    # -- SetClipCodes -----------------------------------------------------
    def _set_clip_codes(self, sortv: Sequence[int], axis: int, value: float) -> None:
        verts = self.verts
        vflag = self.vflag
        for vi in sortv:
            t = verts[vi][axis] - value
            f = 0
            # A vertex exactly on the plane counts as being on BOTH sides.
            if t <= 0.0:
                f |= 1
            if t >= 0.0:
                f |= 2
            vflag[vi] = f

    # -- GetClipStats -----------------------------------------------------
    def _clip_stats(
        self, off: int, cnt: int, axis: int, value: float
    ) -> tuple[int, int, float, float, list[int]]:
        verts = self.verts
        vflag = self.vflag
        n_left = n_right = 0
        overlap_left = overlap_right = 0.0
        sides: list[int] = []

        for k in range(off, off + cnt):
            clip = 3
            dist_left = dist_right = 0.0
            for vi in self.tris[self.polys[k]]:
                d = verts[vi][axis] - value
                md = -d
                clip &= vflag[vi]
                if md > dist_left:
                    dist_left = md
                elif d > dist_right:
                    dist_right = d

            c = clip & 3
            if c == 1:  # entirely left
                sides.append(1)
                n_left += 1
            elif c in (2, 3):  # entirely right (3 == fully coplanar)
                sides.append(2)
                n_right += 1
            else:  # straddles: goes to the side it reaches further into
                if dist_right > dist_left:
                    sides.append(2)
                    n_right += 1
                    overlap_right = max(overlap_right, dist_left)
                else:
                    sides.append(1)
                    n_left += 1
                    overlap_left = max(overlap_left, dist_right)

        return n_left, n_right, value + overlap_left, value - overlap_right, sides

    # -- SortPolygons -----------------------------------------------------
    def _partition(self, off: int, cnt: int, sides: Sequence[int]) -> None:
        left_count = 0
        polys = self.polys
        for i in range(cnt):
            if sides[i] == 1:
                if i > left_count:
                    polys[off + left_count], polys[off + i] = (
                        polys[off + i],
                        polys[off + left_count],
                    )
                left_count += 1

    # -- FindDividingPlane ------------------------------------------------
    def _find_dividing_plane(
        self,
        sortv: list[int],
        off: int,
        cnt: int,
        inf: Sequence[float],
        sup: Sequence[float],
    ) -> tuple[int, float] | None:
        verts = self.verts
        vsize = [sup[a] - inf[a] for a in range(3)]
        max_axis = max(range(3), key=lambda a: vsize[a])
        n = len(sortv)

        best: tuple[int, float] | None = None
        best_score = float("inf")

        for axis in range(3):
            if vsize[axis] <= 0.0:
                continue
            extent_score = _fuzzy_extent_score(vsize[axis], vsize[max_axis])

            order = sorted(sortv, key=lambda vi: verts[vi][axis])
            median = verts[order[n >> 1]][axis]
            lo_q = n >> 2
            hi_q = (n >> 1) + (n >> 2)
            iqr = verts[order[hi_q]][axis] - verts[order[lo_q]][axis]

            if iqr < _RANGEEPS * vsize[max_axis]:
                # Degenerate spread - only test the median.
                lo_q = hi_q = n >> 1
                quant = 0.0
            else:
                quant = _MAXCLOSESTCHECK / iqr
                band = order[lo_q : hi_q + 1]
                band.sort(key=lambda vi: abs(median - verts[vi][axis]))
                order[lo_q : hi_q + 1] = band

            last_quant = -1
            uniq = _MAXCLOSESTCHECK
            i = lo_q
            while i <= hi_q and uniq > 0:
                try_value = verts[order[i]][axis]
                quant_value = int(try_value * quant)  # truncate toward zero
                if quant_value != last_quant:
                    self._set_clip_codes(sortv, axis, try_value)
                    n_l, n_r, l_val, r_val, _ = self._clip_stats(
                        off, cnt, axis, try_value
                    )
                    if n_l and n_r:
                        score = (
                            (
                                (l_val - inf[axis]) * _average_tree_depth(n_l)
                                + (sup[axis] - r_val) * _average_tree_depth(n_r)
                            )
                            / vsize[axis]
                            * extent_score
                        )
                        if score < best_score:
                            best_score = score
                            best = (axis, try_value)
                    last_quant = quant_value
                    uniq -= 1
                i += 1

        return best

    # -- BuildTreeGenerate ------------------------------------------------
    def generate( # type: ignore
        self,
        off: int,
        cnt: int,
        inf: Sequence[float],
        sup: Sequence[float],
        depth: int,
    ) -> tuple:
        if cnt < _MIN_POLYGONS_FOR_SPLIT:
            return ("L", cnt, off)

        if depth < rpCOLLTREE_MAXDEPTH:
            sortv = self._sort_vertices(off, cnt)
            found = self._find_dividing_plane(sortv, off, cnt, inf, sup)
            if found is not None:
                axis, value = found
                self._set_clip_codes(sortv, axis, value)
                n_l, n_r, l_val, r_val, sides = self._clip_stats(off, cnt, axis, value)
                self._partition(off, cnt, sides)
            elif cnt <= rpCOLLSECTOR_CONTENTS_MAXCOUNT:
                # Coincident triangles - just make a leaf.
                return ("L", cnt, off)
            else:
                # Too many for a leaf: fake a 100% overlapping split.
                axis = 0
                l_val = sup[0]
                r_val = inf[0]
                n_l = cnt >> 1
                n_r = cnt - n_l
        elif cnt <= rpCOLLSECTOR_CONTENTS_MAXCOUNT:
            return ("L", cnt, off)
        else:
            raise ValueError(
                f"rpCOLLTREE_MAXDEPTH reached with {cnt} triangles remaining "
                + f"(max {rpCOLLSECTOR_CONTENTS_MAXCOUNT} per leaf)"
            )

        left_sup = list(sup)
        left_sup[axis] = l_val
        right_inf = list(inf)
        right_inf[axis] = r_val

        return (
            "B",
            axis,
            l_val,
            r_val,
            self.generate(off, n_l, inf, left_sup, depth + 1), # type: ignore
            self.generate(off + n_l, n_r, right_inf, sup, depth + 1), # type: ignore
        )


def _flatten(root: tuple) -> list[RpCollSplit]: # type: ignore
    """CreateCollTreeFromBuildTree() - pre-order, left subtree before right."""
    splits: list[RpCollSplit] = []

    def emit(node: tuple) -> int: # type: ignore
        idx = len(splits)
        splits.append(RpCollSplit())
        _, axis, l_val, r_val, left, right = node

        if left[0] == "L":
            l_contents, l_index = left[1], left[2]
        else:
            l_contents, l_index = rpCOLLSECTOR_CONTENTS_SPLIT, None
        if right[0] == "L":
            r_contents, r_index = right[1], right[2]
        else:
            r_contents, r_index = rpCOLLSECTOR_CONTENTS_SPLIT, None

        if l_index is None:
            l_index = emit(left) # type: ignore
        if r_index is None:
            r_index = emit(right) # type: ignore

        splits[idx] = RpCollSplit(
            leftSector=RpCollSector(
                collsec_type=_AXIS_TYPE[axis] | rpCOLLSECTOR_TYPE_NEG, # type: ignore
                contents=l_contents, # type: ignore
                index=l_index, # type: ignore
                value=l_val, # type: ignore
            ),
            rightSector=RpCollSector(
                collsec_type=_AXIS_TYPE[axis], # type: ignore
                contents=r_contents, # type: ignore
                index=r_index, # type: ignore
                value=r_val, # type: ignore
            ),
        )
        return idx

    if root[0] != "L":
        emit(root)
    return splits


# rwsrc-v3.7.0.2/collis/ctdata.c line 265
# rwsrc-v3.7.0.2/collis/ctdata.c line 101
@dataclass
class RW_CollTreeStruct(RW_Section):
    header: RWHeader = field(default_factory=RWHeader)

    flags: RW_CollTreeFlags = field(default_factory=RW_CollTreeFlags)

    boxInf: Vector3 = field(default_factory=Vector3)
    boxSup: Vector3 = field(default_factory=Vector3)

    numEntries: int = field(default=0)
    numSplits: int = field(default=0)

    splits: list[RpCollSplit] = field(default_factory=list)
    map: list[int] = field(default_factory=list)

    # Not part of the on-disk format. Always holds the permutation produced by
    # build(): sort_map[i] is the ORIGINAL triangle index belonging at sorted
    # position i. Identical to `map` when rpCOLLTREE_USEMAP is set.
    sort_map: list[int] = field(default_factory=list, repr=False)

    # -- generation -------------------------------------------------------
    @classmethod
    def build(
        cls,
        vertices: Sequence[Vector3],
        triangles: Sequence[RW_Triangle],
        sort_triangles: bool = True,
    ) -> "RW_CollTreeStruct":
        """Generate a collision tree from a triangle list.

        vertices  -- Vector3 / (x, y, z) sequence, in the same space the tree
                     will be queried in (geometry: model space, world sector:
                     world space).
        triangles -- index triples, or objects with vertex1/2/3.

        sort_triangles=True mirrors rpCOLLISIONBUILD_SORTTRIANGLES: no map is
        stored, and the caller MUST reorder its triangle array (and any
        parallel per-triangle data) with apply_sort() before writing.

        sort_triangles=False keeps your triangle order and stores the mapping
        in the tree, setting rpCOLLTREE_USEMAP.
        """
        verts = [(v.x, v.y, v.z) for v in vertices]
        tris = [(t.vertex1, t.vertex2, t.vertex3) for t in triangles]

        if not verts:
            raise ValueError("no vertices")
        if not (0 < len(tris) <= 0xFFFF):
            raise ValueError(f"numEntries must be 1..65535, got {len(tris)}")

        inf = [min(v[a] for v in verts) for a in range(3)]
        sup = [max(v[a] for v in verts) for a in range(3)]

        builder = _CollTreeBuilder(verts, tris)
        root = builder.generate(0, len(tris), inf, sup, 0) # type: ignore
        splits = _flatten(root)

        if len(splits) > 0xFFFF:
            raise ValueError(f"numSplits exceeds RwUInt16 ({len(splits)})")

        s = cls()
        s.flags = RW_CollTreeFlags(rpCOLLTREE_USEMAP=not sort_triangles)
        s.boxInf = Vector3(x=inf[0], y=inf[1], z=inf[2])
        s.boxSup = Vector3(x=sup[0], y=sup[1], z=sup[2])
        s.numEntries = len(tris)
        s.numSplits = len(splits)
        s.splits = splits
        s.sort_map = builder.polys
        s.map = list(builder.polys) if s.flags.rpCOLLTREE_USEMAP else []
        return s

    def apply_sort(self, items: Sequence[Any]) -> list[Any]:
        """Reorder a per-triangle array to match the tree."""
        if len(items) != self.numEntries:
            raise ValueError(f"expected {self.numEntries} items, got {len(items)}")
        return [items[i] for i in self.sort_map]

    # -- io ---------------------------------------------------------------
    @classmethod
    @override
    def read(
        cls, parser: Parser, parent: RW_Section | None = None
    ) -> "RW_CollTreeStruct":
        colltree_s = cls()
        colltree_s.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            colltree_s.header,
            RWSectionType.rwID_STRUCT.value,
            "RW_CollTreeStruct chunk type",
        )

        colltree_s.flags = RW_CollTreeFlags.decode(parser.readUint32())  # flags
        colltree_s.boxInf = Vector3.read(parser)  # bbox inf
        colltree_s.boxSup = Vector3.read(parser)  # bbox sup
        colltree_s.numEntries = parser.readUint32()  # numEntries
        colltree_s.numSplits = parser.readUint32()  # numSplits

        # Splits
        colltree_s.splits = []
        if colltree_s.numSplits > 0:
            for _ in range(colltree_s.numSplits):
                colltree_s.splits.append(RpCollSplit.read(parser))

        # Map
        colltree_s.map = []
        if colltree_s.flags.rpCOLLTREE_USEMAP:
            for _ in range(colltree_s.numEntries):
                colltree_s.map.append(parser.readUint16())
        colltree_s.sort_map = list(colltree_s.map)

        return colltree_s

    def pack_body(self) -> bytes:
        if len(self.splits) != self.numSplits:
            raise ValueError(
                f"numSplits ({self.numSplits}) != len(splits) ({len(self.splits)})"
            )
        if self.flags.rpCOLLTREE_USEMAP and len(self.map) != self.numEntries:
            raise ValueError(
                f"rpCOLLTREE_USEMAP set but map has {len(self.map)} entries, "
                + f"expected {self.numEntries}"
            )

        buf = io.BytesIO()
        buf.write(struct.pack("<I", self.flags.encode()))
        buf.write(
            struct.pack(
                "<6f",
                self.boxInf.x,
                self.boxInf.y,
                self.boxInf.z,
                self.boxSup.x,
                self.boxSup.y,
                self.boxSup.z,
            )
        )
        buf.write(struct.pack("<II", self.numEntries, self.numSplits))

        for split in self.splits:
            buf.write(split.pack())

        if self.flags.rpCOLLTREE_USEMAP:
            buf.write(struct.pack(f"<{self.numEntries}H", *self.map))

        return buf.getvalue()

    @override
    def write(self, f: BinaryIO, stamp: int, parent: RW_Section | None = None) -> None:
        buf = self.pack_body()

        rw_header = RWHeader(
            type=RWSectionType.rwID_STRUCT.value,
            size=len(buf),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf)


@dataclass
class RW_CollTree(RW_Section):
    header: RWHeader = field(default_factory=RWHeader)

    struct: RW_CollTreeStruct = field(default_factory=RW_CollTreeStruct)

    @classmethod
    def build(
        cls,
        vertices: Sequence[Vector3],
        triangles: Sequence[RW_Triangle],
        sort_triangles: bool = True,
    ) -> "RW_CollTree":
        colltree = cls()
        colltree.struct = RW_CollTreeStruct.build(
            vertices, triangles, sort_triangles=sort_triangles
        )
        return colltree

    @classmethod
    @override
    def read(cls, parser: Parser, parent: RW_Section | None = None) -> "RW_CollTree":
        colltree = cls()
        colltree.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            colltree.header,
            RWSectionType.rwID_COLLTREE.value,
            "RW_CollTree chunk type",
        )

        colltree.struct = RW_CollTreeStruct.read(parser)

        return colltree

    def pack_body(self, stamp: int) -> bytes:
        body = self.struct.pack_body()
        inner_header = RWHeader(
            type=RWSectionType.rwID_STRUCT.value,
            size=len(body),
            library_id_stamp=stamp,
        )
        return inner_header.pack() + body

    @override
    def write(self, f: BinaryIO, stamp: int, parent: RW_Section | None = None) -> None:
        buf = self.pack_body(stamp)

        rw_header = RWHeader(
            type=RWSectionType.rwID_COLLTREE.value,
            size=len(buf),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf)

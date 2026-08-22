from collections.abc import Sequence
import io
from dataclasses import dataclass, field
from typing import BinaryIO, override

from madagascar.lib.parser import Parser
from madagascar.lib.rwConstants import RWSectionType
from madagascar.lib.rw_basics import (
    RW_Section,
    RWHeader,
    expect_chunk_type_or_raise,
    library_id_unpack,
    RW_Triangle,
    Vector3,
)
from madagascar.lib.writer import write_u32
from madagascar.sections.COLLTREE_002C import RW_CollTree


@dataclass
class RW_CollisionPlugin(RW_Section):
    header: RWHeader = field(default_factory=RWHeader)

    version: int = field(default=0x37002)

    colltree: RW_CollTree = field(default_factory=RW_CollTree)

    @classmethod
    @override
    def read(
        cls, parser: Parser, parent: RW_Section | None = None
    ) -> "RW_CollisionPlugin":
        collplg = cls()
        collplg.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            collplg.header,
            RWSectionType.rwID_COLLISPLUGIN.value,
            "RW_CollisionPlugin chunk type",
        )

        collplg.version = parser.readUint32()
        if collplg.version < 0x36001:
            raise NotImplementedError(
                "Collision plugin reading not implemented for written BEFORE version 0x36001"
            )
        else:
            collplg.colltree = RW_CollTree.read(parser, collplg)

        return collplg

    @override
    def write(self, f: BinaryIO, stamp: int, parent: RW_Section | None = None):
        version = library_id_unpack(stamp)[0]
        if version < 0x36001:
            raise NotImplementedError(
                "Collision plugin writing not implemented for version BEFORE 0x36001"
            )

        buf = io.BytesIO()

        # CollisionDataStreamWrite(): RwEngineGetVersion() then the COLLTREE
        # chunk. The reader uses this leading word to tell new-format data from
        # pre-3.6.0.1 data (where it was really a leaf count), so it must be
        # written even though the chunk header already carries a stamp.
        write_u32(buf, version)
        self.colltree.write(buf, stamp, self)

        rw_header = RWHeader(
            type=RWSectionType.rwID_COLLISPLUGIN.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())

    @classmethod
    def build_from_geo(
        cls,
        vertices: Sequence[Vector3],
        triangles: Sequence[RW_Triangle],
        sort_triangles: bool = True,
    ):
        colltree = RW_CollTree.build(vertices, triangles, sort_triangles)
        return cls(colltree=colltree)

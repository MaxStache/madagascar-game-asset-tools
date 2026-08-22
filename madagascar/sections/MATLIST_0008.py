import io
from dataclasses import dataclass, field
from typing import BinaryIO, override

from madagascar.lib.writer import write_u32, write_s32
from madagascar.lib.parser import Parser
from madagascar.lib.rwConstants import RWSectionType
from madagascar.lib.rw_basics import RW_Section, RWHeader, expect_chunk_type_or_raise

from madagascar.sections.MATERIAL_0007 import RW_Material

@dataclass
class RW_MaterialList_Struct(RW_Section):
    header: RWHeader = field(default_factory=RWHeader)

    material_count: int = 0

    # A material index equals -1 if it ^++^+is a material.
    # If the material is an instance of a previously defined material,
    # the index equals the base materials one.
    #    ~ gtamods.com/wiki/Material_List_(RW_Section)
    materialIndices: list[int] = field(
        default_factory=list
    )  # uint32 each material_count

    @classmethod
    @override
    def read(cls, parser: Parser, parent: RW_Section | None = None) -> "RW_MaterialList_Struct":
        matlist_s = RW_MaterialList_Struct()
        matlist_s.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            matlist_s.header,
            RWSectionType.rwID_STRUCT.value,
            "RW_MaterialList_Struct chunk type",
        )

        matlist_s.material_count = parser.readUint32()

        matlist_s.materialIndices = []
        for _ in range(matlist_s.material_count):
            val = parser.readInt32()
            matlist_s.materialIndices.append(val)

        return matlist_s

    @override
    def write(self, f: BinaryIO, stamp: int, parent: RW_Section | None = None):
        buf = io.BytesIO()

        write_u32(buf,  len(self.materialIndices))

        for idx in self.materialIndices:
            write_s32(buf, idx)

        rw_header = RWHeader(
            type=RWSectionType.rwID_STRUCT.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())

@dataclass
class RW_MaterialList(RW_Section):
    header: RWHeader = field(default_factory=RWHeader)
    
    struct: RW_MaterialList_Struct = field(default_factory=RW_MaterialList_Struct)

    materials: list[RW_Material] = field(
        default_factory=list
    )  # RW_Material each material_count

    @classmethod
    @override
    def read(cls, parser: Parser, parent: RW_Section | None = None) -> "RW_MaterialList":
        matlist = cls()
        matlist.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            matlist.header,
            RWSectionType.rwID_MATLIST.value,
            "RW_MaterialList chunk type",
        )

        matlist.struct = RW_MaterialList_Struct.read(parser)

        matlist.materials = []
        for _ in range(matlist.struct.material_count):
            matlist.materials.append(RW_Material.read(parser))

        return matlist

    @override
    def write(self, f: BinaryIO, stamp: int, parent: RW_Section | None = None):
        buf = io.BytesIO()

        self.struct.write(buf, stamp)

        if len(self.struct.materialIndices) != len(self.materials):
            raise ValueError(
                f"Failed to write MATLIST! {len(self.materials)} materials but materialIndices has {len(self.struct.materialIndices)} entries"
            )

        for mat in self.materials:
            mat.write(buf, stamp, parent=self)

        rw_header = RWHeader(
            type=RWSectionType.rwID_MATLIST.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())
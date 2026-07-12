import io
from dataclasses import dataclass, field

from formats.lib.writer import _write_u32, _write_s32
from formats.lib.parser import Parser
from formats.lib.rwConstants import RWSectionType
from formats.lib.rw_basics import RW_Section, RWHeader, expect_chunk_type_or_raise

from formats.sections.MATERIAL_0007 import RW_Material

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

    @staticmethod
    def read(parser: Parser) -> "RW_MaterialList_Struct":
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

    def write(this, f, stamp, parent=None):
        buf = io.BytesIO()

        _write_u32(buf,  len(this.materialIndices))

        for idx in this.materialIndices:
            _write_s32(buf, idx)

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

    @staticmethod
    def read(parser: Parser, parent=None) -> "RW_MaterialList":
        matlist = RW_MaterialList()
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

    def write(this, f, stamp, parent=None):
        buf = io.BytesIO()

        this.struct.write(buf, stamp)

        if len(this.struct.materialIndices) != len(this.materials):
            raise ValueError(
                f"Failed to write MATLIST! {len(this.materials)} materials but materialIndices has {len(this.struct.materialIndices)} entries"
            )

        for mat in this.materials:
            mat.write(buf, stamp, parent=this)

        rw_header = RWHeader(
            type=RWSectionType.rwID_MATLIST.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())
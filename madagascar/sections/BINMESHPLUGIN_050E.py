from enum import Enum
import io
from dataclasses import dataclass, field
from typing import override

from madagascar.lib.writer import write_u32
from madagascar.lib.parser import Parser
from madagascar.lib.rwConstants import RWSectionType
from madagascar.lib.rw_basics import RW_Section, RWHeader, expect_chunk_type_or_raise

class RW_BinMeshPlugin_Flags(Enum):
    TRIANGLE_LIST = 0
    TRIANGLE_STRIP = 1
    
@dataclass
class RW_BinMeshPlugin_Mesh:
    """
    container class for a mesh in RW_BinMeshPlugin
    """
    
    numIndices: int = field(default=0)  # uint32
    materialIndex: int = field(
        default=0
    )  # uint32 - Material Index in the Geometry's Material List

    indices: list[int] = field(
        default_factory=list, init=False
    )  # uint32[numIndices] - Vertex indices for this mesh

@dataclass
class RW_BinMeshPlugin(RW_Section):
    """
    The Bin Mesh plugin holds an optimized representation of the model topology.
    Triangles are grouped together into Meshes by their Material and stored as triangle strips
    when the rpGEOMETRYTRISTRIP flag (0x1) is set in the Geometry, otherwise as triangle lists.
    In pre-instanced files, the chunk looks different according to platform.
    ~ https://gtamods.com/wiki/Bin_Mesh_PLG_(RW_Section)

    This is a NON pre-instanced bin mesh plg!
    """

    header: RWHeader = field(default_factory=RWHeader)

    flags: RW_BinMeshPlugin_Flags = field(
        default=RW_BinMeshPlugin_Flags.TRIANGLE_LIST
    )  # uint32
    numMeshes: int = 0  # uint32
    numIndices: int = 0  # uint32 - Total number of indices across all meshes

    meshes: list[RW_BinMeshPlugin_Mesh] = field(
        default_factory=list, init=False
    )  # RW_BinMeshPLG_Mesh[numMeshes]


    @classmethod
    @override
    def read(cls, parser: Parser, parent: RW_Section | None = None) -> "RW_BinMeshPlugin":
        binmesh = cls()
        binmesh.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            binmesh.header,
            RWSectionType.rwID_BINMESHPLUGIN.value,
            "RW_BinMeshPlugin chunk type",
        )

        binmesh.flags = RW_BinMeshPlugin_Flags(parser.readUint32())
        binmesh.numMeshes = parser.readUint32()
        binmesh.numIndices = parser.readUint32()

        binmesh.meshes = []
        for _meshIndex in range(binmesh.numMeshes):
            mesh = RW_BinMeshPlugin_Mesh()
            mesh.numIndices = parser.readUint32()
            mesh.materialIndex = parser.readUint32()
            mesh.indices = [parser.readUint32() for _ in range(mesh.numIndices)]
            binmesh.meshes.append(mesh)

        return binmesh

    @override
    def write(self, f, stamp, parent: RW_Section | None = None):
        buf = io.BytesIO()

        write_u32(buf, self.flags.value)
        write_u32(buf, self.numMeshes)
        write_u32(buf, self.numIndices)
        for mesh in self.meshes:
            write_u32(buf, mesh.numIndices)
            write_u32(buf, mesh.materialIndex)
            for idx in mesh.indices:
                write_u32(buf, idx)

        rw_header = RWHeader(
            type=RWSectionType.rwID_BINMESHPLUGIN.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())
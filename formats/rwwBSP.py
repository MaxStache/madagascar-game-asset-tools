"""
rwwBSP.py — RenderWare World (.BSP) Library
========================================================

Read, write, export, and import Renderware World BSP files.

"""

from enum import Enum
import io
import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import Union, Optional

from sections import RW_Extension, RW_BinMeshPlugin
from sections.BINMESHPLUGIN_050E import RW_BinMeshPlugin_Flags

from lib.parser import Parser
from rwConstants import RWSectionType, RWSectionType_TFB, DEFAULT_VERSION_STAMP
from rw_basics import RWColor32, Vector3, RWHeader, RW_Triangle

__version__ = "1.0.0"


# ═══════════════════════════════════════════════════════
#  Data Structures
# ═══════════════════════════════════════════════════════


def bytes_pad4(data: bytes) -> bytes:
    padding = (4 - (len(data) % 4)) % 4
    return data + b"\x00" * padding


@dataclass
class RW_Texture:
    header: RWHeader = field(default_factory=RWHeader)
    struct_header: RWHeader = field(default_factory=RWHeader)

    filterMode: int = 0  # u8
    addressModes: int = 0  # u8
    useMipLevels: int = 0  # u16

    diffuse_header: RWHeader = field(default_factory=RWHeader)
    diffuseTextureName: str = ""  # diffuse_header.payload_size

    alpha_header: RWHeader = field(default_factory=RWHeader)
    alphaTextureName: str = ""  # alpha_header.payload_size

    ext_header: RWHeader = field(default_factory=RWHeader)
    extData: bytes = b""  # ext_header.payload_size

    @staticmethod
    def read(parser: Parser) -> "RW_Texture":
        texture = RW_Texture()
        texture.header = RWHeader.read(parser)
        texture.struct_header = RWHeader.read(parser)

        texture.filterMode = parser.readUint8()
        texture.addressModes = parser.readUint8()
        texture.useMipLevels = parser.readUint16()

        texture.diffuse_header = RWHeader.read(parser)
        texture.diffuseTextureName = parser.readBytes(
            texture.diffuse_header.size
        ).decode("latin-1", errors="replace")

        texture.alpha_header = RWHeader.read(parser)
        texture.alphaTextureName = parser.readBytes(texture.alpha_header.size).decode(
            "latin-1", errors="replace"
        )

        texture.ext_header = RWHeader.read(parser)
        texture.extData = parser.readBytes(texture.ext_header.size)

        return texture

    def write(this, f, stamp):
        buf = io.BytesIO()

        sbuf = io.BytesIO()

        # region struct data
        _write_u8(sbuf, this.filterMode)
        _write_u8(sbuf, this.addressModes)
        _write_u16(sbuf, this.useMipLevels)
        # endregion

        buf.write(sbuf.getvalue())

        # region diffuse texture name
        enc_diffuse_name = bytes_pad4(
            this.diffuseTextureName.encode("latin-1", errors="replace")
        )
        diffuse_header = RWHeader(
            type=RWSectionType.rwID_STRING.value,
            size=len(enc_diffuse_name),
            library_id_stamp=stamp,
        )
        buf.write(diffuse_header.pack())
        buf.write(enc_diffuse_name)
        # endregion

        # region alpha texture name
        enc_alpha_name = bytes_pad4(
            this.alphaTextureName.encode("latin-1", errors="replace")
        )
        alpha_header = RWHeader(
            type=RWSectionType.rwID_STRING.value,
            size=len(enc_alpha_name),
            library_id_stamp=stamp,
        )
        buf.write(alpha_header.pack())
        buf.write(enc_alpha_name)

        # endregion

        ext_header = RWHeader(
            type=RWSectionType.rwID_EXTENSION.value,
            size=len(this.extData),
            library_id_stamp=stamp,
        )
        buf.write(ext_header.pack())
        buf.write(this.extData)

        rw_header = RWHeader(
            type=RWSectionType.rwID_TEXTURE.value,
            size=len(buf.getvalue()) + RWHeader().binSize,
            library_id_stamp=stamp,
        )
        rw_struct_header = RWHeader(
            type=RWSectionType.rwID_STRUCT.value,
            size=len(sbuf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(rw_struct_header.pack())
        f.write(buf.getvalue())


@dataclass
class RW_UV:
    u: float = 0.0
    v: float = 0.0


@dataclass
class RW_Matrix2x3:
    row1: Vector3 = field(default_factory=Vector3)
    row2: Vector3 = field(default_factory=Vector3)

    def write(this, f):
        this.row1.write(f)
        this.row2.write(f)

    def read(parser: Parser) -> "RW_Matrix2x3":
        return RW_Matrix2x3(
            row1=Vector3.read(parser),
            row2=Vector3.read(parser),
        )


@dataclass
class RW_TFB_rwMATFXEFFECTUVTRANSFORM:
    header: RWHeader = field(default_factory=RWHeader)
    unk1: int = 0  # uint32
    unk2: int = 0  # uint32
    unk3: int = 0  # uint32
    unk4: int = 0  # uint32
    unk5: int = 0  # uint32
    unk6: int = 0  # uint32
    unk7: int = 0  # uint32
    uv_transform_matrix: RW_Matrix2x3 = field(default_factory=lambda: RW_Matrix2x3())
    unk8: int = 0  # uint32
    unk9: int = 0  # uint32
    unk10: int = 0  # uint32
    unk11: int = 0  # uint8

    def read(parser: Parser) -> "RW_TFB_rwMATFXEFFECTUVTRANSFORM":
        uv_transform = RW_TFB_rwMATFXEFFECTUVTRANSFORM()
        uv_transform.header = RWHeader.read(parser)
        print(uv_transform.header.size)
        p = Parser(parser.readBytes(uv_transform.header.size))
        uv_transform.unk1 = p.readUint32()
        uv_transform.unk2 = p.readUint32()
        uv_transform.unk3 = p.readUint32()
        uv_transform.unk4 = p.readUint32()
        uv_transform.unk5 = p.readUint32()
        uv_transform.unk6 = p.readUint32()
        uv_transform.unk7 = p.readUint32()
        uv_transform.uv_transform_matrix = RW_Matrix2x3.read(p)
        uv_transform.unk8 = p.readUint32()
        uv_transform.unk9 = p.readUint32()
        uv_transform.unk10 = p.readUint32()
        uv_transform.unk11 = p.readUint8()
        return uv_transform


class RW_MaterialEffectsPLG_Type(Enum):
    rwMATFXEFFECTNULL = 0x00  # No Effect
    rwMATFXEFFECTBUMPMAP = 0x01  # Bump Map
    rwMATFXEFFECTENVMAP = 0x02  # Environment Map (Reflections)
    rwMATFXEFFECTBUMPENVMAP = 0x03  # Bump Map/Environment Map
    rwMATFXEFFECTDUAL = 0x04  # Dual Textures
    rwMATFXEFFECTUVTRANSFORM = 0x05  # UV-Tranformation
    rwMATFXEFFECTDUALUVTRANSFORM = 0x06  # Dual Textures/UV-Transformation


@dataclass
class RW_MaterialEffectsPLG:
    header: RWHeader = field(default_factory=RWHeader)
    effectId: int = 0  # uint32
    effect1_type: int = 0x00
    effect2_type: int = 0x00

    @staticmethod
    def read(parser: Parser) -> "RW_MaterialEffectsPLG":
        mat_effect = RW_MaterialEffectsPLG()
        mat_effect.header = RWHeader.read(parser)
        mat_effect.effectId = parser.readUint32()
        mat_effect.effect1_type = parser.readUint32()
        mat_effect.effect2_type = parser.readUint32()
        return mat_effect


@dataclass
class RW_Material:
    header: RWHeader = field(default_factory=RWHeader)
    struct_header: RWHeader = field(default_factory=RWHeader)

    flags: int = 0
    color: RWColor32 = field(default_factory=RWColor32)
    unused: int = 367978292  # always 367978292 in tested files
    isTextured: int = 0

    ambient: float = 0.0
    specular: float = 0.0
    diffuse: float = 0.0

    texture: Optional[RW_Texture] = None

    ext_header: RWHeader = field(default_factory=RWHeader)
    extData: bytes = b""  # ext_header.payload_size

    extension: RW_Extension = field(default_factory=RW_Extension)

    def parse_extensions(this):
        buf = Parser(this.extData)
        extensions = []

        while buf.canRead(12):
            header = RWHeader.read(buf)
            buf.offset -= 12  # Rewind to include header in the extension data

            if header.type == RWSectionType.rwID_MATERIALEFFECTSPLUGIN.value:
                mat_effect = RW_MaterialEffectsPLG.read(buf)
                extensions.append(mat_effect)
            elif header.type == RWSectionType_TFB.rwID_tfbMATFXEFFECTUVTRANSFORM.value:
                # uv_transform = RW_TFB_rwMATFXEFFECTUVTRANSFORM.read(buf)
                # extensions.append(uv_transform)
                _header = RWHeader.read(buf)
                print(_header.size)
                print(buf.readBytes(_header.size).hex())
                # buf.skip(header.size)
            else:
                _header = RWHeader.read(buf)
                buf.skip(header.size)
                extensions.append("UNKNOWN")
                print(hex(header.type), header.type)

        return extensions

    @staticmethod
    def read(parser: Parser) -> "RW_Material":
        mat = RW_Material()
        mat.header = RWHeader.read(parser)
        mat.struct_header = RWHeader.read(parser)

        mat.flags = parser.readUint32()  # always 0 in tested files
        mat.color = RWColor32.read(parser)
        mat.unused = parser.readUint32()  # always 367978292 in tested files
        mat.isTextured = parser.readUint32()

        mat.ambient = parser.readFloat()
        mat.specular = parser.readFloat()
        mat.diffuse = parser.readFloat()

        if mat.isTextured:
            mat.texture = RW_Texture.read(parser)

        #mat.ext_header = RWHeader.read(parser)
        #mat.extData = parser.readBytes(mat.ext_header.size)

        mat.extension = RW_Extension.read(parser, parent_type=RWSectionType.rwID_MATERIAL.value)

        return mat

    def write(this, f, stamp):
        buf = io.BytesIO()

        struct_buf = io.BytesIO()

        # region struct data
        _write_u32(struct_buf, this.flags)
        this.color.write(struct_buf)
        _write_u32(struct_buf, this.unused)
        _write_u32(struct_buf, this.isTextured)

        _write_f32(struct_buf, this.ambient)
        _write_f32(struct_buf, this.specular)
        _write_f32(struct_buf, this.diffuse)
        # endregion

        buf.write(struct_buf.getvalue())

        if this.isTextured and this.texture is not None:
            this.texture.write(buf, stamp)

        ext_header = RWHeader(
            type=RWSectionType.rwID_EXTENSION.value,
            size=len(this.extData),
            library_id_stamp=stamp,
        )
        buf.write(ext_header.pack())
        buf.write(this.extData)

        rw_header = RWHeader(
            type=RWSectionType.rwID_MATERIAL.value,
            size=len(buf.getvalue()) + RWHeader().binSize,
            library_id_stamp=stamp,
        )
        rw_struct_header = RWHeader(
            type=RWSectionType.rwID_STRUCT.value,
            size=len(struct_buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(rw_struct_header.pack())
        f.write(buf.getvalue())


@dataclass
class RW_MaterialList:
    header: RWHeader = field(default_factory=RWHeader)
    struct_header: RWHeader = field(default_factory=RWHeader)

    material_count: int = 0

    # A material index equals -1 if it is a material.
    # If the material is an instance of a previously defined material,
    # the index equals the base materials one.
    #    ~ gtamods.com/wiki/Material_List_(RW_Section)
    materialIndices: list[int] = field(
        default_factory=list
    )  # uint32 each material_count

    materials: list[RW_Material] = field(
        default_factory=list
    )  # RW_Material each material_count

    @staticmethod
    def read(parser: Parser) -> "RW_MaterialList":
        matlist = RW_MaterialList()
        matlist.header = RWHeader.read(parser)
        matlist.struct_header = RWHeader.read(parser)

        matlist.material_count = parser.readUint32()

        matlist.materialIndices = []
        for _ in range(matlist.material_count):
            val = parser.readInt32()
            matlist.materialIndices.append(val)

        matlist.materials = []
        for _ in range(matlist.material_count):
            matlist.materials.append(RW_Material.read(parser))

        return matlist

    def write(this, f, stamp):
        buf = io.BytesIO()
        sbuf = io.BytesIO()

        # region struct data
        matcount = len(this.materials)

        _write_u32(sbuf, matcount)

        if len(this.materialIndices) != matcount:
            raise ValueError(
                f"Failed to write MATLIST! {matcount} materials but materialIndices has {len(this.materialIndices)} entries"
            )
        for idx in this.materialIndices:
            _write_s32(sbuf, idx)
        # endregion

        buf.write(sbuf.getvalue())

        for mat in this.materials:
            mat.write(buf, stamp)

        rw_header = RWHeader(
            type=RWSectionType.rwID_MATLIST.value,
            size=len(buf.getvalue()) + RWHeader().binSize,
            library_id_stamp=stamp,
        )
        rw_struct_header = RWHeader(
            type=RWSectionType.rwID_STRUCT.value,
            size=len(sbuf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(rw_struct_header.pack())
        f.write(buf.getvalue())


@dataclass
class RpWorldFlags:
    triStrip: bool = False  # 0x00000001 — geometry uses triangle strips
    positions: bool = False  # 0x00000002 — has positions (should always be set)
    textured: bool = False  # 0x00000004 — has one set of texture coordinates
    preLit: bool = False  # 0x00000008 — has pre-lit vertex colors
    normals: bool = False  # 0x00000010 — has normals
    light: bool = False  # 0x00000020 — is lit
    modulateMaterialColor: bool = (
        False  # 0x00000040 — vertex colors modulate material color
    )
    textured2: bool = False  # 0x00000080 — has a second set of texture coordinates
    numTexCoordSets: int = (
        0  # bits 16–19 — number of UV sets (0 = auto-detect from other flags)
    )
    native: bool = False  # 0x01000000 — world is in native (platform-specific) format
    nativeInstance: bool = False  # 0x02000000 — world is a native instance
    sectorsOverlap: bool = False  # 0x40000000 — BSP sectors are allowed to overlap

    @staticmethod
    def decode(value: int) -> "RpWorldFlags":
        f = RpWorldFlags()
        f.triStrip = bool(value & 0x00000001)
        f.positions = bool(value & 0x00000002)
        f.textured = bool(value & 0x00000004)
        f.preLit = bool(value & 0x00000008)
        f.normals = bool(value & 0x00000010)
        f.light = bool(value & 0x00000020)
        f.modulateMaterialColor = bool(value & 0x00000040)
        f.textured2 = bool(value & 0x00000080)
        f.numTexCoordSets = (value >> 16) & 0xF
        f.native = bool(value & 0x01000000)
        f.nativeInstance = bool(value & 0x02000000)
        f.sectorsOverlap = bool(value & 0x40000000)
        return f

    def encode(self) -> int:
        v = 0
        if self.triStrip:
            v |= 0x00000001
        if self.positions:
            v |= 0x00000002
        if self.textured:
            v |= 0x00000004
        if self.preLit:
            v |= 0x00000008
        if self.normals:
            v |= 0x00000010
        if self.light:
            v |= 0x00000020
        if self.modulateMaterialColor:
            v |= 0x00000040
        if self.textured2:
            v |= 0x00000080
        v |= (self.numTexCoordSets & 0xF) << 16
        if self.native:
            v |= 0x01000000
        if self.nativeInstance:
            v |= 0x02000000
        if self.sectorsOverlap:
            v |= 0x40000000
        return v
    
    def print(self):
        print("RpWorldFlags:")
        print(f"  triStrip: {self.triStrip}")
        print(f"  positions: {self.positions}")
        print(f"  textured: {self.textured}")
        print(f"  preLit: {self.preLit}")
        print(f"  normals: {self.normals}")
        print(f"  light: {self.light}")
        print(f"  modulateMaterialColor: {self.modulateMaterialColor}")
        print(f"  textured2: {self.textured2}")
        print(f"  numTexCoordSets: {self.numTexCoordSets}")
        print(f"  native: {self.native}")
        print(f"  nativeInstance: {self.nativeInstance}")
        print(f"  sectorsOverlap: {self.sectorsOverlap}")


@dataclass
class WorldStructData_A:
    numTriangles: int = 0  # uint32
    numVertices: int = 0  # uint32
    numPlaneSectors: int = 0  # uint32
    numAtomicSectors: int = 0  # uint32
    colSectorSize: int = 0  # uint32, often 0
    worldFlags: RpWorldFlags = field(default_factory=RpWorldFlags)

    boxMax: Vector3 = field(default_factory=Vector3)
    boxMin: Vector3 = field(default_factory=Vector3)

    def write(this, f, stamp):
        _write_u32(f, this.numTriangles)
        _write_u32(f, this.numVertices)
        _write_u32(f, this.numPlaneSectors)
        _write_u32(f, this.numAtomicSectors)
        _write_u32(f, this.colSectorSize)
        _write_u32(f, this.worldFlags.encode())

        this.boxMax.write(f)
        this.boxMin.write(f)


@dataclass
class WorldStructData_B:
    boxMax: Vector3 = field(default_factory=Vector3)

    numTriangles: int = 0  # uint32
    numVertices: int = 0  # uint32
    numPlaneSectors: int = 0  # uint32
    numAtomicSectors: int = 0  # uint32
    colSectorSize: int = 0  # uint32
    worldFlags: RpWorldFlags = field(default_factory=RpWorldFlags)

    def write(this, f, stamp):
        this.boxMax.write(f)

        _write_u32(f, this.numTriangles)
        _write_u32(f, this.numVertices)
        _write_u32(f, this.numPlaneSectors)
        _write_u32(f, this.numAtomicSectors)
        _write_u32(f, this.colSectorSize)
        _write_u32(f, this.worldFlags.encode())


@dataclass
class RW_World_AtomicSector:
    hdr_payload_size: int = 0
    hdr_version: int = 0

    struct_header: "RWHeader" = field(default_factory=lambda: RWHeader())

    matListWindowBase: int = 0  # u32
    numTriangles: int = 0  # u32
    numVertices: int = 0  # u32

    boxMax: Vector3 = field(default_factory=Vector3)
    boxMin: Vector3 = field(default_factory=Vector3)

    collSectorPresent: int = 0  # u32
    unused: int = 0  # u32 always 0 in tested files

    vertices: list[Vector3] = field(default_factory=list, init=False)  # num_vertices

    # if not handled as collision bsp in TFB games
    colors: Optional[list[RWColor32]] = field(
        default_factory=list, init=False
    )  # num_vertices
    uvs: Optional[list[RW_UV]] = field(default_factory=list, init=False)  # num_vertices
    # endif

    triangles: list[RW_Triangle] = field(
        default_factory=list, init=False
    )  # num_triangles

    extension_sector: RW_Extension = field(
        default_factory=RW_Extension, init=False
    )

    @staticmethod
    def read(parser: Parser, collision_only_map=False) -> "RW_World_AtomicSector":
        atomic = RW_World_AtomicSector()
        atomic.hdr_payload_size = parser.readUint32()
        atomic.hdr_version = parser.readUint32()

        atomic.struct_header = RWHeader.read(parser)

        atomic.matListWindowBase = parser.readUint32()
        atomic.numTriangles = parser.readUint32()
        atomic.numVertices = parser.readUint32()

        atomic.boxMax = Vector3.read(parser)
        atomic.boxMin = Vector3.read(parser)

        atomic.collSectorPresent = parser.readUint32()
        atomic.unused = parser.readUint32()

        atomic.vertices = []
        for _ in range(atomic.numVertices):
            atomic.vertices.append(Vector3.read(parser))

        atomic.colors = []
        atomic.uvs = []

        if not collision_only_map:  # If not handled as collision bsp in TFB games
            # Vertex Colors
            for _ in range(atomic.numVertices):
                atomic.colors.append(RWColor32.read(parser))
            # UVS
            for _ in range(atomic.numVertices):
                atomic.uvs.append(RW_UV(u=parser.readFloat(), v=parser.readFloat()))

        atomic.triangles = []
        for _ in range(atomic.numTriangles):
            triangle = RW_Triangle()
            triangle.vertex1 = parser.readUint16()
            triangle.vertex2 = parser.readUint16()
            triangle.vertex3 = parser.readUint16()
            triangle.materialIndex = parser.readUint16()
            atomic.triangles.append(triangle)

        atomic.extension_sector = RW_Extension.read(
            parser, RWSectionType.rwID_ATOMICSECT
        )

        return atomic

    def write(this, f, stamp, collision_only_map=False):
        buf = io.BytesIO()
        sbuf = io.BytesIO()

        # region struct data
        _write_u32(sbuf, this.matListWindowBase)
        _write_u32(sbuf, len(this.triangles))  # numTriangles
        _write_u32(sbuf, len(this.vertices))  # numVertices

        this.boxMax.write(sbuf)
        this.boxMin.write(sbuf)

        _write_u32(sbuf, this.collSectorPresent)
        _write_u32(sbuf, this.unused)
        # endregion

        for vertex in this.vertices:
            vertex.write(sbuf)

        if not collision_only_map:
            if len(this.colors) != len(this.vertices):
                raise ValueError(
                    f"Failed to write AtomicSector! {len(this.vertices)} vertices but {len(this.colors)} Vertex Colors"
                )
            for color in this.colors:
                color.write(sbuf)

            if len(this.uvs) != len(this.vertices):
                raise ValueError(
                    f"Failed to write AtomicSector! {len(this.vertices)} vertices but {len(this.uvs)} UVs"
                )
            for uv in this.uvs:
                _write_f32(sbuf, uv.u)
                _write_f32(sbuf, uv.v)

        for triangle in this.triangles:
            _write_u16(sbuf, triangle.vertex1)
            _write_u16(sbuf, triangle.vertex2)
            _write_u16(sbuf, triangle.vertex3)
            _write_u16(sbuf, triangle.materialIndex)

        buf.write(sbuf.getvalue())

        this.extension_sector.write(buf, stamp)

        _write_u32(
            f, len(buf.getvalue()) + RWHeader().binSize
        )  # payload size for atomic sector header
        _write_u32(f, stamp)  # version for atomic sector header
        rw_struct_header = RWHeader(
            type=RWSectionType.rwID_STRUCT.value,
            size=len(sbuf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_struct_header.pack())
        f.write(buf.getvalue())


class RW_World_PlaneSectorType(Enum):
    """
    These specific numbers aren't arbitrary,
    they're byte offsets into an RwV3d struct,
    which is just three consecutive floats {x, y, z} at offsets 0, 4, and 8.
    So the engine can use type directly to index the relevant coordinate of a point
    (that's what the GETCOORD macro in the headers does).
    You can see this in the whitepaper's iterator example: partition->type = 4;
    /* the y-axis */.

    REFRENCE TO: RenderWare Whitepapers - worlds.pdf
    WRITTEN BY: Claude Opus 4.8 Extra
    """

    rwPLANE_X = 0
    rwPLANE_Y = 4
    rwPLANE_Z = 8


@dataclass
class RW_World_PlaneSector:
    hdr_payload_size: int = 0
    hdr_version: int = 0

    struct_header: "RWHeader" = field(default_factory=lambda: RWHeader())

    type: RW_World_PlaneSectorType = RW_World_PlaneSectorType.rwPLANE_X  # uint32 (axis)
    value: float = 0.0  # float32
    """
    value - the position of that plane along the chosen axis,
    i.e. the axis offset of the dividing plane.
    If type == 4 (Y) and value == 100.0,
    the plane is y = 100. To decide which side a point falls on,
    you read the point's coordinate at the axis given by type and compare
    it against value: less goes to the negative/left subtree, greater-or-equal goes
    to the positive/right subtree. For an axis-aligned plane this comparison is the
    dot-product test the overview section describes
    it collapses to picking one coordinate.
    
    REFRENCE TO: RenderWare Whitepapers - worlds.pdf
    WRITTEN BY: Claude Opus 4.8 Extra
    """

    left_is_atomic: int = 0  # uint32
    right_is_atomic: int = 0  # uint32

    left_value: float = 0.0  # float32
    right_value: float = 0.0  # float32

    """
    left_value and right_value:
    those exist because RenderWare allows sectors to overlap (page 10).
    value is the nominal split position, while left_value and right_value are 
    the actual extents of the negative and positive sub-boxes, which may overlap rather 
    than meeting exactly at value. That's the mechanism that lets the builder avoid cutting 
    geometry at the plane.
    
    REFRENCE TO: RenderWare Whitepapers - worlds.pdf
    WRITTEN BY: Claude Opus 4.8 Extra
    """

    left_child_id: int = 0
    left_data: Optional[Union["RW_World_AtomicSector", "RW_World_PlaneSector"]] = field(
        default=None, init=False
    )

    right_child_id: int = 0
    right_data: Optional[Union["RW_World_AtomicSector", "RW_World_PlaneSector"]] = (
        field(default=None, init=False)
    )

    @staticmethod
    def read(parser: Parser, collision_only_map=False) -> "RW_World_PlaneSector":
        ps = RW_World_PlaneSector()
        ps.hdr_payload_size = parser.readUint32()
        ps.hdr_version = parser.readUint32()

        ps.struct_header = RWHeader.read(parser)

        plane_type = parser.readUint32()
        ps.type = RW_World_PlaneSectorType(plane_type)

        ps.value = parser.readFloat()

        ps.left_is_atomic = parser.readUint32()
        ps.right_is_atomic = parser.readUint32()

        ps.left_value = parser.readFloat()
        ps.right_value = parser.readFloat()

        ps.left_child_id = parser.readUint32()

        if ps.left_is_atomic == 1:
            if ps.left_child_id != 0x0009:
                raise ValueError(
                    f"Expected AtomicSector (0x0009) for left child, got 0x{ps.left_child_id:04X}"
                )
            ps.left_data = RW_World_AtomicSector.read(parser, collision_only_map=collision_only_map)
        else:
            if ps.left_child_id != 0x000A:
                raise ValueError(
                    f"Expected PlaneSector (0x000A) for left child, got 0x{ps.left_child_id:04X}"
                )
            ps.left_data = RW_World_PlaneSector.read(parser, collision_only_map=collision_only_map)

        ps.right_child_id = parser.readUint32()

        if ps.right_is_atomic == 1:
            if ps.right_child_id != 0x0009:
                raise ValueError(
                    f"Expected AtomicSector (0x0009) for right child, got 0x{ps.right_child_id:04X}"
                )
            ps.right_data = RW_World_AtomicSector.read(parser, collision_only_map=collision_only_map)
        else:
            if ps.right_child_id != 0x000A:
                raise ValueError(
                    f"Expected PlaneSector (0x000A) for right child, got 0x{ps.right_child_id:04X}"
                )
            ps.right_data = RW_World_PlaneSector.read(parser, collision_only_map=collision_only_map)

        return ps

    def write(this, f, stamp):
        buf = io.BytesIO()
        sbuf = io.BytesIO()

        # region struct data
        _write_u32(sbuf, this.type.value)
        _write_f32(sbuf, this.value)

        _write_u32(sbuf, this.left_is_atomic)
        _write_u32(sbuf, this.right_is_atomic)

        _write_f32(sbuf, this.left_value)
        _write_f32(sbuf, this.right_value)
        # endregion

        buf.write(sbuf.getvalue())

        # region left child
        if this.left_is_atomic == 1:
            _write_u32(buf, RWSectionType.rwID_ATOMICSECT.value)  # AtomicSector
        else:
            _write_u32(buf, RWSectionType.rwID_PLANESECT.value)  # PlaneSector

        this.left_data.write(buf, stamp)
        # endregion

        # region right child
        if this.right_is_atomic == 1:
            _write_u32(buf, RWSectionType.rwID_ATOMICSECT.value)  # AtomicSector
        else:
            _write_u32(buf, RWSectionType.rwID_PLANESECT.value)  # PlaneSector

        this.right_data.write(buf, stamp)
        # endregion

        _write_u32(
            f, len(buf.getvalue()) + RWHeader().binSize
        )  # payload size for plane sector header
        _write_u32(f, stamp)  # version for plane sector header
        rw_struct_header = RWHeader(
            type=RWSectionType.rwID_STRUCT.value,
            size=len(sbuf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_struct_header.pack())
        f.write(buf.getvalue())


@dataclass
class RW_World_RootChunk:
    section_id: int = 0  # uint32

    data: Optional[Union[RW_World_AtomicSector, RW_World_PlaneSector]] = None

    @staticmethod
    def read(parser: Parser, parent, collision_only_map=False) -> "RW_World_RootChunk":
        rootchunk = RW_World_RootChunk()
        rootchunk.section_id = parser.readUint32()

        if parent.data.numAtomicSectors == 1 and parent.data.numPlaneSectors == 0:
            rootchunk.data = RW_World_AtomicSector.read(parser, collision_only_map=collision_only_map)
        elif parent.data.numPlaneSectors > 0:
            rootchunk.data = RW_World_PlaneSector.read(parser, collision_only_map=collision_only_map)
        else:
            raise ValueError(
                f"Unexpected world struct sector counts: atomic={parent.data.numAtomicSectors}, plane={parent.data.numPlaneSectors}"
            )

        return rootchunk

    def write(this, f, stamp, collision_only_map):
        _write_u32(f, this.section_id)

        if isinstance(this.data, RW_World_AtomicSector):
            this.data.write(f, stamp, collision_only_map)
        elif isinstance(this.data, RW_World_PlaneSector):
            this.data.write(f, stamp)
        else:
            raise ValueError(f"Unexpected root chunk data type: {type(this.data)}")


@dataclass
class RW_WorldStruct:
    header: RWHeader = field(default_factory=RWHeader)
    rootIsWorldSector: int = 0  # often 0
    inverseOrigin: Vector3 = field(default_factory=Vector3)  # often -0 -0 -0

    data: Union[WorldStructData_A, WorldStructData_B, None] = None  # often Type A

    def write(this, f, stamp):
        buf = io.BytesIO()

        _write_u32(buf, this.rootIsWorldSector)
        this.inverseOrigin.write(buf)

        this.data.write(buf, stamp)

        rw_header = RWHeader(
            type=RWSectionType.rwID_STRUCT.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())


@dataclass
class RW_World:
    header: RWHeader = field(default_factory=RWHeader)

    world_struct: "RW_WorldStruct" = field(default_factory=RW_WorldStruct)

    material_list: RW_MaterialList = field(default_factory=RW_MaterialList)

    world_chunk: RW_World_RootChunk = field(init=False)

    ext_header: RWHeader = field(default_factory=RWHeader)
    extData: bytes = b""  # ext_header.payload_size

    def save(self, filepath: Union[str, Path], collision_only_map=False):
        buf = io.BytesIO()

        self.world_struct.write(buf, DEFAULT_VERSION_STAMP)

        self.material_list.write(buf, DEFAULT_VERSION_STAMP)

        self.world_chunk.write(buf, DEFAULT_VERSION_STAMP, collision_only_map)

        ext_header = RWHeader(
            type=RWSectionType.rwID_EXTENSION.value,
            size=len(self.extData),
            library_id_stamp=DEFAULT_VERSION_STAMP,
        )
        buf.write(ext_header.pack())
        buf.write(self.extData)

        rw_header = RWHeader(
            type=RWSectionType.rwID_WORLD.value,
            size=len(buf.getvalue()),
            library_id_stamp=DEFAULT_VERSION_STAMP,
        )
        with open(filepath, "wb") as f:
            f.write(rw_header.pack())
            f.write(buf.getvalue())


# ═══════════════════════════════════════════════════════
#  helpers
# ═══════════════════════════════════════════════════════


def _write_u8(f, v):
    f.write(struct.pack("<B", v))


def _write_u16(f, v):
    f.write(struct.pack("<H", v))


def _write_u32(f, v):
    f.write(struct.pack("<I", v))


def _write_s32(f, v):
    f.write(struct.pack("<i", v))


def _write_f32(f, v):
    f.write(struct.pack("<f", v))


def _write_bytes(f, data):
    f.write(data)


def _read_fixed_string(f, length: int) -> str:
    raw = f.read(length)
    null = raw.find(b"\x00")
    return (raw[:null] if null >= 0 else raw).decode("ascii", errors="replace")


def _write_fixed_string(f, s: str, length: int):
    encoded = s.encode("ascii", errors="replace")[: length - 1]
    f.write(encoded + b"\x00" * (length - len(encoded)))


def _write_header(f, chunk_type: int, size: int, stamp: int = None):
    f.write(struct.pack("<III", chunk_type, size, stamp))


def expect_chunk_type_or_raise(
    header: RWHeader, expected_type: int, error: str = "Wrong Chunk Type"
):
    if header.type != expected_type:
        raise ValueError(
            f"{error}: expected 0x{expected_type:02X}, got 0x{header.type:02X} ({int(header.type)})"
        )


def load_bsp(filepath: Union[str, Path], collision_only_map=False) -> RW_World:
    """Load a BSP file from disk

    Args:
        filepath: Path to the .bsp file.

    Returns:
        Parsed BSP.
    """
    bsp = RW_World()

    with open(filepath, "rb") as f:
        parser = Parser(f.read(), endian="little")

        bsp.header = RWHeader.read(parser)

        expect_chunk_type_or_raise(
            bsp.header, RWSectionType.rwID_WORLD.value, "Not a RW BSP (TOP)"
        )

        bsp.world_struct = RW_WorldStruct()
        bsp.world_struct.header = RWHeader.read(parser)

        expect_chunk_type_or_raise(
            bsp.world_struct.header,
            RWSectionType.rwID_STRUCT.value,
            "Not a RW BSP (TOP_STRUCT)",
        )

        bsp.world_struct.rootIsWorldSector = parser.readUint32()
        bsp.world_struct.inverseOrigin = Vector3.read(parser)

        if bsp.world_struct.header.size == 0x40:
            bsp.world_struct.data = WorldStructData_A()
            bsp.world_struct.data.numTriangles = parser.readUint32()
            bsp.world_struct.data.numVertices = parser.readUint32()
            bsp.world_struct.data.numPlaneSectors = parser.readUint32()
            bsp.world_struct.data.numAtomicSectors = parser.readUint32()
            bsp.world_struct.data.colSectorSize = parser.readUint32()
            bsp.world_struct.data.worldFlags = RpWorldFlags.decode(parser.readUint32())
            bsp.world_struct.data.worldFlags.print()
            bsp.world_struct.data.boxMax = Vector3.read(parser)
            bsp.world_struct.data.boxMin = Vector3.read(parser)
        elif bsp.world_struct.header.size == 0x30:
            bsp.world_struct.data = WorldStructData_B()
            bsp.world_struct.data.boxMax = Vector3.read(parser)
            bsp.world_struct.data.numTriangles = parser.readUint32()
            bsp.world_struct.data.numVertices = parser.readUint32()
            bsp.world_struct.data.numPlaneSectors = parser.readUint32()
            bsp.world_struct.data.numAtomicSectors = parser.readUint32()
            bsp.world_struct.data.colSectorSize = parser.readUint32()
            bsp.world_struct.data.worldFlags = RpWorldFlags.decode(parser.readUint32())
        else:
            raise ValueError(
                f"Unexpected RW_WorldStruct payload size: {bsp.world_struct.header.payload_size}"
            )

        bsp.material_list = RW_MaterialList.read(parser)

        bsp.world_chunk = RW_World_RootChunk.read(
            parser, bsp.world_struct, collision_only_map
        )

        if parser.getRemainingBytes() >= RWHeader().binSize:
            bsp.ext_header = RWHeader.read(parser)
            expect_chunk_type_or_raise(
                bsp.ext_header,
                RWSectionType.rwID_EXTENSION.value,
                "Not a RW BSP (TOP_EXTENSION)",
            )
            if parser.getRemainingBytes() < bsp.ext_header.size:
                raise ValueError(
                    f"Declared extension data size {bsp.ext_header.size} exceeds remaining file size {parser.getRemainingBytes()}"
                )
            bsp.extData = parser.readBytes(bsp.ext_header.size)

    return bsp


def _collect_atomic_sectors(
    chunk: Union[RW_World_AtomicSector, RW_World_PlaneSector],
) -> list[RW_World_AtomicSector]:
    if chunk is None:
        return []

    sectors = []
    if isinstance(chunk, RW_World_AtomicSector):
        sectors.append(chunk)
    elif isinstance(chunk, RW_World_PlaneSector):
        sectors.extend(_collect_atomic_sectors(chunk.left_data))
        sectors.extend(_collect_atomic_sectors(chunk.right_data))

    return sectors


# ═══════════════════════════════════════════════════════
#  BSP World Builder
# ═══════════════════════════════════════════════════════


def _make_atomic_sector(
    vertices: list[tuple[float, float, float]],
    triangles: list[tuple[int, int, int, int]],
    uvs: Optional[list[tuple[float, float]]],
    colors: Optional[list[tuple[int, int, int, int]]],
    tri_indices: list[int],
    collision_only: bool,
) -> RW_World_AtomicSector:
    used_global = sorted(set(
        v for i in tri_indices for v in triangles[i][:3]
    ))
    g2l = {g: li for li, g in enumerate(used_global)}

    local_verts = [Vector3(*vertices[g]) for g in used_global]

    local_tris = [
        RW_Triangle(
            g2l[triangles[i][0]],
            g2l[triangles[i][1]],
            g2l[triangles[i][2]],
            triangles[i][3],
        )
        for i in tri_indices
    ]

    if local_verts:
        b_min = Vector3(
            min(v.x for v in local_verts),
            min(v.y for v in local_verts),
            min(v.z for v in local_verts),
        )
        b_max = Vector3(
            max(v.x for v in local_verts),
            max(v.y for v in local_verts),
            max(v.z for v in local_verts),
        )
    else:
        b_min = b_max = Vector3(0.0, 0.0, 0.0)

    sector = RW_World_AtomicSector()
    sector.matListWindowBase = 0
    sector.vertices = local_verts
    sector.boxMin = b_min
    sector.boxMax = b_max
    sector.collSectorPresent = 0
    sector.unused = 0

    if not collision_only:
        sector.colors = (
            [RWColor32(*colors[g]) for g in used_global]
            if colors is not None
            else [RWColor32(255, 255, 255, 255)] * len(used_global)
        )
        sector.uvs = (
            [RW_UV(uvs[g][0], uvs[g][1]) for g in used_global]
            if uvs is not None
            else [RW_UV(0.0, 0.0)] * len(used_global)
        )
    else:
        sector.colors = []
        sector.uvs = []

    sector.triangles = local_tris

    sector.extension_sector = RW_Extension()
    sector.extension_sector.children = [
        RW_BinMeshPlugin.generate_from_triangles(
            local_tris,
            flag=RW_BinMeshPlugin_Flags.TRIANGLE_LIST,
            matListWindowBase=0,
        )
    ]

    return sector


def _build_bsp_node(
    vertices: list[tuple[float, float, float]],
    triangles: list[tuple[int, int, int, int]],
    uvs: Optional[list[tuple[float, float]]],
    colors: Optional[list[tuple[int, int, int, int]]],
    tri_indices: list[int],
    max_tris: int,
    collision_only: bool,
) -> tuple[Union[RW_World_AtomicSector, RW_World_PlaneSector], int, int]:
    """Returns (node, num_plane_sectors, num_atomic_sectors)."""
    if len(tri_indices) <= max_tris:
        return _make_atomic_sector(vertices, triangles, uvs, colors, tri_indices, collision_only), 0, 1

    def centroid(i):
        v1, v2, v3 = triangles[i][0], triangles[i][1], triangles[i][2]
        return (
            (vertices[v1][0] + vertices[v2][0] + vertices[v3][0]) / 3.0,
            (vertices[v1][1] + vertices[v2][1] + vertices[v3][1]) / 3.0,
            (vertices[v1][2] + vertices[v2][2] + vertices[v3][2]) / 3.0,
        )

    centroids = [centroid(i) for i in tri_indices]
    spans = [
        max(c[a] for c in centroids) - min(c[a] for c in centroids)
        for a in range(3)
    ]
    axis = spans.index(max(spans))
    axis_type = [
        RW_World_PlaneSectorType.rwPLANE_X,
        RW_World_PlaneSectorType.rwPLANE_Y,
        RW_World_PlaneSectorType.rwPLANE_Z,
    ][axis]

    sorted_pairs = sorted(zip(tri_indices, centroids), key=lambda p: p[1][axis])
    sorted_indices = [p[0] for p in sorted_pairs]
    sorted_axis_vals = [p[1][axis] for p in sorted_pairs]

    mid = len(sorted_indices) // 2
    left_indices = sorted_indices[:mid]
    right_indices = sorted_indices[mid:]

    if not left_indices or not right_indices:
        return _make_atomic_sector(vertices, triangles, uvs, colors, tri_indices, collision_only), 0, 1

    split_value = (sorted_axis_vals[mid - 1] + sorted_axis_vals[mid]) / 2.0

    def vert_axis_vals(indices):
        return [vertices[triangles[i][vi]][axis] for i in indices for vi in range(3)]

    left_vv = vert_axis_vals(left_indices)
    right_vv = vert_axis_vals(right_indices)
    left_value = max(left_vv) if left_vv else split_value
    right_value = min(right_vv) if right_vv else split_value

    left_node, lp, la = _build_bsp_node(vertices, triangles, uvs, colors, left_indices, max_tris, collision_only)
    right_node, rp, ra = _build_bsp_node(vertices, triangles, uvs, colors, right_indices, max_tris, collision_only)

    plane = RW_World_PlaneSector()
    plane.type = axis_type
    plane.value = split_value
    plane.left_is_atomic = 1 if isinstance(left_node, RW_World_AtomicSector) else 0
    plane.right_is_atomic = 1 if isinstance(right_node, RW_World_AtomicSector) else 0
    plane.left_value = left_value
    plane.right_value = right_value
    plane.left_data = left_node
    plane.right_data = right_node

    return plane, lp + rp + 1, la + ra


def build_bsp_world(
    vertices: list[tuple[float, float, float]],
    triangles: list[tuple[int, int, int, int]],
    uvs: Optional[list[tuple[float, float]]] = None,
    colors: Optional[list[tuple[int, int, int, int]]] = None,
    materials: Optional[list[RW_Material]] = None,
    max_tris_per_sector: int = 6000,
    collision_only: bool = False,
) -> RW_World:
    """Build an RW_World from flat geometry data.

    Args:
        vertices: List of (x, y, z) world-space positions.
        triangles: List of (v1, v2, v3, mat_idx) tuples. mat_idx is a global
            index into *materials*.
        uvs: Per-vertex (u, v) pairs, same length as *vertices*. None for untextured.
        colors: Per-vertex (r, g, b, a) tuples in 0-255 range, same length as
            *vertices*. None defaults every vertex to opaque white.
        materials: List of RW_Material objects that form the global material list.
            Defaults to a single blank white material.
        max_tris_per_sector: Maximum triangles allowed in one AtomicSector before
            the builder splits it into two children. Tune to balance depth vs sector size.
        collision_only: When True, omits vertex colours and UVs (collision BSP).

    Returns:
        RW_World instance ready to be written with .save().
    """
    if materials is None:
        materials = [RW_Material()]

    tri_indices = list(range(len(triangles)))

    root_node, num_planes, num_atomics = _build_bsp_node(
        vertices, triangles, uvs, colors, tri_indices, max_tris_per_sector, collision_only
    )

    # Global bounding box from referenced vertices
    used = set(v for tri in triangles for v in tri[:3])
    if used:
        xs = [vertices[i][0] for i in used]
        ys = [vertices[i][1] for i in used]
        zs = [vertices[i][2] for i in used]
        box_min = Vector3(min(xs), min(ys), min(zs))
        box_max = Vector3(max(xs), max(ys), max(zs))
    else:
        box_min = box_max = Vector3(0.0, 0.0, 0.0)

    all_atomics = _collect_atomic_sectors(root_node)
    total_verts = sum(len(s.vertices) for s in all_atomics)
    total_tris = sum(len(s.triangles) for s in all_atomics)

    flags = RpWorldFlags()
    flags.positions = True
    flags.light = True
    if not collision_only:
        if uvs is not None:
            flags.textured = True
        if colors is not None:
            flags.preLit = True

    struct_data = WorldStructData_A()
    struct_data.numTriangles = total_tris
    struct_data.numVertices = total_verts
    struct_data.numPlaneSectors = num_planes
    struct_data.numAtomicSectors = num_atomics
    struct_data.colSectorSize = 0
    struct_data.worldFlags = flags
    struct_data.boxMax = box_max
    struct_data.boxMin = box_min

    world_struct = RW_WorldStruct()
    world_struct.rootIsWorldSector = 1
    world_struct.inverseOrigin = Vector3(0.0, 0.0, 0.0)
    world_struct.data = struct_data

    matlist = RW_MaterialList()
    matlist.material_count = len(materials)
    matlist.materialIndices = [-1] * len(materials)
    matlist.materials = list(materials)

    if isinstance(root_node, RW_World_AtomicSector):
        section_id = RWSectionType.rwID_ATOMICSECT.value
    else:
        section_id = RWSectionType.rwID_PLANESECT.value

    world_chunk = RW_World_RootChunk()
    world_chunk.section_id = section_id
    world_chunk.data = root_node

    world = RW_World()
    world.world_struct = world_struct
    world.material_list = matlist
    world.world_chunk = world_chunk
    world.extData = b""

    return world

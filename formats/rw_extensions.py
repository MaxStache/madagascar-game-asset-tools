from enum import Enum
import io
import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import BinaryIO, Union, Optional
from lib.parser import Parser
from rwConstants import RWSectionType, RWSectionType_TFB, DEFAULT_VERSION_STAMP
from rw_basics import RWColor32, Vector3, RWHeader, RW_World_Triangle
from rich.pretty import pprint

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


def sector_is_atomic(sectorType: RWSectionType) -> bool:
    return sectorType in [
        RWSectionType.rwID_ATOMICSECT,
        RWSectionType.rwID_ATOMIC,
    ]


@dataclass
class RW_EXT_BASE:
    header: RWHeader = field(default_factory=RWHeader)

    def read(header: RWHeader, parser: Parser) -> "RW_EXT_BASE":
        raise NotImplementedError(
            "[RW_EXT_BASE]: Must implement read method for each extension type"
        )

    def write(self, f: BinaryIO, stamp=DEFAULT_VERSION_STAMP):
        raise NotImplementedError(
            "[RW_EXT_BASE]: Must implement write method for each extension type"
        )


@dataclass
class RW_EXT_UNKNOWN(RW_EXT_BASE):
    raw_data: bytes = b""

    def read(header: RWHeader, parser: Parser) -> "RW_EXT_UNKNOWN":
        ext = RW_EXT_UNKNOWN()
        ext.header = header
        ext.raw_data = parser.readBytes(header.size)
        return ext

    def write(self, f: BinaryIO, stamp=DEFAULT_VERSION_STAMP):
        rw_header = RWHeader(
            type=self.header.type,
            size=len(self.raw_data),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(self.raw_data)


class RW_BinMeshPLG_Type(Enum):
    TRIANGLE_LIST = 0
    TRIANGLE_STRIP = 1


@dataclass
class RW_BinMeshPLG_Mesh:
    numIndices: int = field(default=0)  # uint32
    materialIndex: int = field(
        default=0
    )  # uint32 - Material Index in the Geometry's Material List

    indices: list[int] = field(
        default_factory=list, init=False
    )  # uint32[numIndices] - Vertex indices for this mesh


@dataclass
class RW_EXT_BinMeshPLG(RW_EXT_BASE):
    """
    The Bin Mesh plugin holds an optimized representation of the model topology.
    Triangles are grouped together into Meshes by their Material and stored as triangle strips
    when the rpGEOMETRYTRISTRIP flag (0x1) is set in the Geometry, otherwise as triangle lists.
    In pre-instanced files, the chunk looks different according to platform.
    ~ https://gtamods.com/wiki/Bin_Mesh_PLG_(RW_Section)

    This is a NON pre-instanced bin mesh plg!
    """

    flags: RW_BinMeshPLG_Type = field(
        default=RW_BinMeshPLG_Type.TRIANGLE_LIST
    )  # uint32
    numMeshes: int = field(default=0)  # uint32
    numIndices: int = field(
        default=0
    )  # uint32 - Total number of indices across all meshes

    meshes: list[RW_BinMeshPLG_Mesh] = field(
        default_factory=list, init=False
    )  # RW_BinMeshPLG_Mesh[numMeshes]

    def read(header: RWHeader, p: Parser) -> "RW_EXT_BinMeshPLG":
        ext = RW_EXT_BinMeshPLG()
        ext.header = header
        ext.flags = RW_BinMeshPLG_Type(p.readUint32())
        ext.numMeshes = p.readUint32()
        ext.numIndices = p.readUint32()

        ext.meshes = []
        for meshIndex in range(ext.numMeshes):
            mesh = RW_BinMeshPLG_Mesh()
            mesh.numIndices = p.readUint32()
            mesh.materialIndex = p.readUint32()
            mesh.indices = [p.readUint32() for _ in range(mesh.numIndices)]
            ext.meshes.append(mesh)

        return ext

    @staticmethod
    def generate_from_triangles(
        triangles: list[RW_World_Triangle],
        stamp=DEFAULT_VERSION_STAMP,
        flag: RW_BinMeshPLG_Type = RW_BinMeshPLG_Type.TRIANGLE_LIST,
        matListWindowBase: int = 0,
    ) -> "RW_EXT_BinMeshPLG":
        ext = RW_EXT_BinMeshPLG()
        ext.header = RWHeader(type=RWSectionType.rwID_BINMESHPLUGIN.value, size=0, library_id_stamp=stamp)

        if flag == RW_BinMeshPLG_Type.TRIANGLE_STRIP:
            print("WARN! TRIANGLE STRIP IS BROKEN CURENTLY")
            print("WARN! TRIANGLE STRIP IS BROKEN CURENTLY")
            print("WARN! TRIANGLE STRIP IS BROKEN CURENTLY")
            print("WARN! TRIANGLE STRIP IS BROKEN CURENTLY")
            print("WARN! TRIANGLE STRIP IS BROKEN CURENTLY")
            print("WARN! TRIANGLE STRIP IS BROKEN CURENTLY")
            print("WARN! TRIANGLE STRIP IS BROKEN CURENTLY")
            print("WARN! TRIANGLE STRIP IS BROKEN CURENTLY")
            ext.flags = RW_BinMeshPLG_Type.TRIANGLE_STRIP

            material_to_mesh: dict[int, RW_BinMeshPLG_Mesh] = {}

            for tri in triangles:
                if tri.materialIndex not in material_to_mesh:
                    material_to_mesh[tri.materialIndex] = RW_BinMeshPLG_Mesh(
                        numIndices=0,
                        materialIndex=tri.materialIndex,
                    )

            # Process each material separately
            for material_index, mesh in material_to_mesh.items():
                tris = [
                    (t.vertex1, t.vertex2, t.vertex3)
                    for t in triangles
                    if t.materialIndex == material_index
                ]

                used = [False] * len(tris)

                while not all(used):
                    start_idx = used.index(False)
                    a, b, c = tris[start_idx]

                    strip = [a, b, c]
                    used[start_idx] = True

                    while True:
                        edge = (strip[-2], strip[-1])

                        found = False

                        for i, tri in enumerate(tris):
                            if used[i]:
                                continue

                            verts = [tri[0], tri[1], tri[2]]

                            # Find triangle sharing current edge
                            for new_v in verts:
                                if new_v in edge:
                                    continue

                                if edge[0] in verts and edge[1] in verts:
                                    strip.append(new_v)
                                    used[i] = True
                                    found = True
                                    break

                            if found:
                                break

                        if not found:
                            break

                    mesh.indices.extend(strip)

                mesh.numIndices = len(mesh.indices)

            ext.meshes = list(material_to_mesh.values())
            ext.numMeshes = len(ext.meshes)
            ext.numIndices = sum(mesh.numIndices for mesh in ext.meshes)

        elif flag == RW_BinMeshPLG_Type.TRIANGLE_LIST:
            ext.flags = RW_BinMeshPLG_Type.TRIANGLE_LIST

            material_to_mesh: dict[int, RW_BinMeshPLG_Mesh] = {}

            for tri in triangles:
                if tri.materialIndex + matListWindowBase not in material_to_mesh:
                    material_to_mesh[tri.materialIndex + matListWindowBase] = RW_BinMeshPLG_Mesh(
                        numIndices=0,
                        materialIndex=tri.materialIndex + matListWindowBase,
                    )

                mesh = material_to_mesh[tri.materialIndex + matListWindowBase]
                mesh.indices.extend([tri.vertex1, tri.vertex2, tri.vertex3])
                mesh.numIndices += 3

            ext.meshes = list(material_to_mesh.values())
            ext.numMeshes = len(ext.meshes)
            ext.numIndices = sum(mesh.numIndices for mesh in ext.meshes)

        return ext

    def write(self, f: BinaryIO, stamp=DEFAULT_VERSION_STAMP):
        buf = io.BytesIO()
        _write_u32(buf, self.flags.value)
        _write_u32(buf, self.numMeshes)
        _write_u32(buf, self.numIndices)
        for mesh in self.meshes:
            _write_u32(buf, mesh.numIndices)
            _write_u32(buf, mesh.materialIndex)
            for idx in mesh.indices:
                _write_u32(buf, idx)

        rw_header = RWHeader(
            type=RWSectionType.rwID_BINMESHPLUGIN.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())


@dataclass
class RW_EXT_MaterialEffectsPLG_GeometryExt(RW_EXT_BASE):
    """
    https://gtamods.com/wiki/Material_Effects_PLG_(RW_Section)#Atomic_extension

    Contains a bool that says if material´s Material Effect PLG will be applied on this atomic
    In RW versions >= 3.4.0.0 this chunk is only written when the value is 1.
    """

    matFXEnabled: int = field(default=False)  # uint32 - 0 or 1

    def read(header: RWHeader, p: Parser) -> "RW_EXT_MaterialEffectsPLG_GeometryExt":
        ext = RW_EXT_MaterialEffectsPLG_GeometryExt()
        ext.header = header
        ext.matFXEnabled = p.readUint32()

        return ext

    def write(self, f: BinaryIO, stamp=DEFAULT_VERSION_STAMP):
        buf = io.BytesIO()
        _write_u32(buf, self.matFXEnabled)

        rw_header = RWHeader(
            type=RWSectionType.rwID_MATERIALEFFECTSPLUGIN.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())


class RW_EXT_MaterialEffectsPLG_EffectType(Enum):
    rwMATFXEFFECTNULL = 0x00  # No Effect
    rwMATFXEFFECTBUMPMAP = 0x01  # Bump Map
    rwMATFXEFFECTENVMAP = 0x02  # Environment Map (Reflections)
    rwMATFXEFFECTBUMPENVMAP = 0x03  # Bump Map/Environment Map
    rwMATFXEFFECTDUAL = 0x04  # Dual Textures
    rwMATFXEFFECTUVTRANSFORM = 0x05  # UV-Tranformation
    rwMATFXEFFECTDUALUVTRANSFORM = 0x06  # Dual Textures/UV-Transformation


@dataclass
class RW_EXT_MaterialEffectsPLG(RW_EXT_BASE):
    """
    https://gtamods.com/wiki/Material_Effects_PLG_(RW_Section)
    """

    effectType: RW_EXT_MaterialEffectsPLG_EffectType = field(
        default=False
    )  # uint32 - RW_EXT_MaterialEffectsPLG_EffectType
    data: bytes = b""  # Effect-specific data, format depends on effectType

    def read(header: RWHeader, p: Parser) -> "RW_EXT_MaterialEffectsPLG":
        ext = RW_EXT_MaterialEffectsPLG()
        ext.header = header
        ext.effectType = RW_EXT_MaterialEffectsPLG_EffectType(p.readUint32())
        ext.data = p.readBytes(len(p.data) - p.tell())

        return ext

    def write(self, f: BinaryIO, stamp=DEFAULT_VERSION_STAMP):
        buf = io.BytesIO()
        _write_u32(buf, self.effectType.value)
        buf.write(self.data)

        rw_header = RWHeader(
            type=RWSectionType.rwID_MATERIALEFFECTSPLUGIN.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())


@dataclass
class RW_ExtensionSector:
    header: RWHeader = field(default_factory=RWHeader)
    extensions: list[RW_EXT_BASE] = field(default_factory=list, init=False)

    def read(parser: Parser, parent_type: RWSectionType) -> "RW_ExtensionSector":
        ext_s = RW_ExtensionSector()
        ext_s.header = RWHeader.read(parser)
        p = Parser(parser.readBytes(ext_s.header.size))
        ext_s.extensions = []

        while p.tell() < ext_s.header.size:
            ext_header = RWHeader.read(p)
            ext_data = p.readBytes(ext_header.size)
            ext_parser: Parser = Parser(ext_data)

            match ext_header.type:
                case RWSectionType.rwID_BINMESHPLUGIN.value:  # BIN MESH PLG
                    ext = RW_EXT_BinMeshPLG.read(ext_header, ext_parser)
                case (
                    RWSectionType.rwID_MATERIALEFFECTSPLUGIN.value
                ):  # MATERIAL EFFECTS PLG
                    if sector_is_atomic(parent_type):
                        ext = RW_EXT_MaterialEffectsPLG_GeometryExt.read(
                            ext_header, ext_parser
                        )
                    else:
                        # print("Material Effects PLG found in non-atomic sector, skipping...")
                        ext = RW_EXT_MaterialEffectsPLG.read(ext_header, ext_parser)
                case 2147483894:  # Some unk extension found on nearly every material
                    ext = RW_EXT_UNKNOWN.read(ext_header, ext_parser)
                case _:
                    ext = RW_EXT_UNKNOWN.read(ext_header, ext_parser)

            ext_s.extensions.append(ext)

        return ext_s

    def pack(self, stamp=DEFAULT_VERSION_STAMP, ignore_errors=False) -> bytes:
        buf = io.BytesIO()
        for ext in self.extensions:
            try:
                ext.write(buf, stamp=stamp)
            except NotImplementedError as e:
                if ignore_errors:
                    continue

                print()
                print(
                    "---------------------------- FATAL ERROR ----------------------------"
                )
                print(f"Extension class {ext.__class__.__name__} failed to pack!")
                print(e)
                print()

        rw_header = RWHeader(
            type=RWSectionType.rwID_EXTENSION.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        return rw_header.pack() + buf.getvalue()


if __name__ == "__main__":
    import rwwBSP
    import rw_extensions as _rw  # avoid double-import class identity mismatch
    import math
    bsp = rwwBSP.load_bsp(
        "Levels/KingOfNY-unchanged/13_KingofNY9_Combined188_NoShadow.bsp"
    )


    for sec in rwwBSP._collect_atomic_sectors(bsp.world_chunk.data):
        print(f"Atomic Sector: {sec.numVertices} vertices, {sec.numTriangles} triangles")
        #sec.triangles = [rwwBSP.RW_World_Triangle(t.vertex1, t.vertex2, t.vertex3, t.materialIndex) for t in sec.triangles]
        sec.vertices = [
            rwwBSP.Vector3(
                v.x,
                v.y,
                v.z + math.sin(v.x * 0.1 + v.y * 0.2) * 20.0
            )
            for v in sec.vertices
        ]


        sec.extension_sector.extensions = [
            ext
            for ext in sec.extension_sector.extensions
            if not isinstance(ext, _rw.RW_EXT_BinMeshPLG)
        ]

        binmesh = _rw.RW_EXT_BinMeshPLG.generate_from_triangles(sec.triangles, flag=_rw.RW_BinMeshPLG_Type.TRIANGLE_LIST, matListWindowBase=sec.matListWindowBase)

        sec.extension_sector.extensions.append(
            binmesh)

        print(sec.extension_sector.extensions)

    import colorsys


    for sec in rwwBSP._collect_atomic_sectors(bsp.world_chunk.data):

        if not sec.vertices:
            continue  # skip empty sectors safely

        zs = [v.z for v in sec.vertices]
        z_min = min(zs)
        z_max = max(zs)
        z_range = (z_max - z_min) or 1.0

        def height_to_rgb(vz):
            t = (vz - z_min) / z_range
            hue = (1.0 - t) * 0.7

            r, g, b = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
            return int(r * 255), int(g * 255), int(b * 255)

        sec.colors = [
            rwwBSP.RWColor32(*height_to_rgb(v.z), c.a)
            for v, c in zip(sec.vertices, sec.colors)
        ]

    bsp.save("Levels/KingOfNY/13_KingofNY9_Combined188_NoShadow.bsp")

    exit()
    world_ext = bsp.ext_header.pack() + bsp.extData
    mat = bsp.material_list.materials[8]
    mat_ext = mat.ext_header.pack() + mat.extData
    text_ext = (
        bsp.material_list.materials[0].texture.ext_header.pack()
        + bsp.material_list.materials[0].texture.extData
    )

    atomic_sect_ext = b""

    for sec in rwwBSP._collect_atomic_sectors(bsp.world_chunk.data):
        if sec.numVertices != 0:
            #atomic_sect_ext = sec.ext_header.pack() + sec.extData
            break

    data = mat_ext

    parser = Parser(data, endian="little")

    sect = RW_ExtensionSector.read(parser, parent_type=RWSectionType.rwID_ATOMICSECT)
    print("############ " + mat.texture.diffuseTextureName + " ############")
    matches = [
        ext for ext in sect.extensions if ext.__class__.__name__ == "RW_EXT_UNKNOWN"
    ]
    pprint(sect.extensions, max_length=5)

    with open("test_ext.bin", "wb") as f:
        f.write(sect.pack())
        if sect.pack() != data:
            print("Packed data does not match original!")
            print(f"Original length: {len(data)}")
            print(f"Packed length:   {len(sect.pack())}")
            print(
                f"Count of changed bytes: {sum(1 for a, b in zip(sect.pack(), data) if a != b)}"
            )

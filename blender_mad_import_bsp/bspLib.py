#!/usr/bin/env python3

import struct
from typing import Any, Dict, List, Optional, Tuple
import random

# Values used by the original TFB/RenderWare export tools for Madagascar.
DEFAULT_VERSION_STAMP = 0x1C020016
DEFAULT_WORLD_FLAGS = 0x4001004D  # triStrip|textured|preLit|modulateMatColor|1 UV set|sectorsOverlap
DEFAULT_MATERIAL_UNUSED_INT2 = 0x32E6CF5C # 0x1C2DE734

class BinaryReader:
    """Helper class to read binary data with offset tracking."""

    def __init__(self, data: bytes):
        self.data = data
        self.offset = 0

    def read_uint8(self) -> int:
        val = struct.unpack_from("<B", self.data, self.offset)[0]
        self.offset += 1
        return val

    def read_int8(self) -> int:
        val = struct.unpack_from("<b", self.data, self.offset)[0]
        self.offset += 1
        return val

    def read_uint16(self) -> int:
        val = struct.unpack_from("<H", self.data, self.offset)[0]
        self.offset += 2
        return val

    def read_int16(self) -> int:
        val = struct.unpack_from("<h", self.data, self.offset)[0]
        self.offset += 2
        return val

    def read_uint32(self) -> int:
        val = struct.unpack_from("<I", self.data, self.offset)[0]
        self.offset += 4
        return val

    def read_int32(self) -> int:
        val = struct.unpack_from("<i", self.data, self.offset)[0]
        self.offset += 4
        return val

    def read_uint64(self) -> int:
        val = struct.unpack_from("<Q", self.data, self.offset)[0]
        self.offset += 8
        return val

    def read_int64(self) -> int:
        val = struct.unpack_from("<q", self.data, self.offset)[0]
        self.offset += 8
        return val

    def read_float32(self) -> float:
        val = struct.unpack_from("<f", self.data, self.offset)[0]
        self.offset += 4
        return val

    def read_float64(self) -> float:
        val = struct.unpack_from("<d", self.data, self.offset)[0]
        self.offset += 8
        return val

    def read_color32(self) -> Dict[str, int]:
        r = self.read_uint8()
        g = self.read_uint8()
        b = self.read_uint8()
        a = self.read_uint8()
        return {"r": r, "g": g, "b": b, "a": a}

    def read_bytes(self, count: int) -> bytes:
        val = self.data[self.offset : self.offset + count]
        self.offset += count
        return val

    def read_string(self, size: int) -> str:
        raw = self.read_bytes(size)
        null_idx = raw.find(b"\x00")
        if null_idx >= 0:
            raw = raw[:null_idx]
        return raw.decode("ascii", errors="replace")


def parse_section_header(reader: BinaryReader) -> Dict[str, int]:
    """Parse a standard RW section header."""
    return {
        "identifier": reader.read_uint32(),
        "size": reader.read_int32(),
        "version": reader.read_int32(),
    }


def parse_texture(reader: BinaryReader) -> Dict[str, Any]:
    """Parse a Texture section (0x0006)."""
    texture = {}

    # Texture Header
    header = parse_section_header(reader)
    texture["header"] = header

    # TextureStruct Header
    struct_header = parse_section_header(reader)
    texture["structHeader"] = struct_header

    # TextureStruct Data
    texture["filterMode"] = reader.read_uint8()
    texture["addressModes"] = reader.read_uint8()
    texture["useMipLevels"] = reader.read_uint16()

    # Diffuse Texture Name (0x0002)
    diffuse_header = parse_section_header(reader)
    texture["diffuseNameHeader"] = diffuse_header
    texture["diffuseTextureName"] = reader.read_string(diffuse_header["size"])

    # Alpha Texture Name (0x0002)
    alpha_header = parse_section_header(reader)
    texture["alphaNameHeader"] = alpha_header
    texture["alphaTextureName"] = reader.read_string(alpha_header["size"])

    # Texture Extension Header
    tex_ext_header = parse_section_header(reader)
    texture["extensionHeader"] = tex_ext_header
    texture["extensionData"] = reader.read_bytes(tex_ext_header["size"]).hex()

    return texture


def parse_tfb_blend_state(ext_data: bytes) -> Optional[int]:
    """Extract the blend-state field from the TFB material plugin chunk
    (0x800000F6) inside a material extension.

    Payload layout (33 or 65 bytes): magic 0x0F0F000D, flags, blendState,
    alphaRef?, srcOrDstBlend?, ... trailing byte = terrain layer index.

    blendState == 0 means the game renders the material fully opaque and
    ignores vertex/texture/material alpha entirely (terrain base layers and
    plain walls often carry garbage vertex alpha of 0). Non-zero (1 or 3 in
    shipped levels) means alpha blending is enabled (terrain overlay layers,
    shadow decals, water, cutout foliage).

    Returns None if the chunk is absent.
    """
    off = 0
    while off + 12 <= len(ext_data):
        ctype, csize, _ = struct.unpack_from("<IiI", ext_data, off)
        off += 12
        if csize < 0 or off + csize > len(ext_data):
            break
        if ctype == 0x800000F6 and csize >= 12:
            return struct.unpack_from("<I", ext_data, off + 8)[0]
        off += csize
    return None


def parse_material(reader: BinaryReader) -> Dict[str, Any]:
    """Parse a Material section (0x0007)."""
    material = {}

    # Material Header
    header = parse_section_header(reader)
    material["header"] = header

    # MaterialStruct Header
    struct_header = parse_section_header(reader)
    material["structHeader"] = struct_header

    # MaterialStruct Data
    material["unusedFlags"] = reader.read_int32()
    material["color"] = reader.read_color32()
    material["unusedInt2"] = reader.read_int32()
    material["isTextured"] = reader.read_int32()
    material["ambient"] = reader.read_float32()
    material["specular"] = reader.read_float32()
    material["diffuse"] = reader.read_float32()

    # Texture (if textured)
    if material["isTextured"] != 0:
        material["texture"] = parse_texture(reader)

    # Material Extension Header
    ext_header = parse_section_header(reader)
    material["extensionHeader"] = ext_header
    ext_data = reader.read_bytes(ext_header["size"])
    material["extensionData"] = ext_data.hex()
    material["tfbBlendState"] = parse_tfb_blend_state(ext_data)

    return material


def parse_material_list(reader: BinaryReader) -> Dict[str, Any]:
    """Parse a MaterialList section (0x0008)."""
    mat_list = {}

    # MaterialList Header
    header = parse_section_header(reader)
    mat_list["header"] = header

    # MaterialListStruct Header
    struct_header = parse_section_header(reader)
    mat_list["structHeader"] = struct_header

    # MaterialListStruct Data
    material_count = reader.read_int32()
    mat_list["materialCount"] = material_count
    mat_list["materialIndices"] = [reader.read_int32() for _ in range(material_count)]

    # Materials
    mat_list["materials"] = [parse_material(reader) for _ in range(material_count)]

    return mat_list


def parse_atomic_sector(
    reader: BinaryReader, is_collision: bool = False,
) -> Dict[str, Any]:
    """Parse an AtomicSector section (0x0009)."""
    atomic = {}

    # AtomicSector Header (identifier already read by caller)
    atomic["size"] = reader.read_int32()
    atomic["version"] = reader.read_int32()

    # AtomicSectorStruct Header
    struct_header = parse_section_header(reader)
    atomic["structHeader"] = struct_header
    struct_size = struct_header["size"]
    start_struct_position = reader.offset

    # AtomicSectorStruct Data
    atomic["matListWindowBase"] = reader.read_int32()
    num_triangles = reader.read_int32()
    num_vertices = reader.read_int32()
    atomic["numTriangles"] = num_triangles
    atomic["numVertices"] = num_vertices
    atomic["boxMax"] = {
        "x": reader.read_float32(),
        "y": reader.read_float32(),
        "z": reader.read_float32(),
    }
    atomic["boxMin"] = {
        "x": reader.read_float32(),
        "y": reader.read_float32(),
        "z": reader.read_float32(),
    }
    atomic["collSectorPresent"] = reader.read_int32()
    atomic["unused"] = reader.read_int32()

    # Check for native data (data stored elsewhere, struct only contains header)
    header_size = 11 * 4  # 11 int32/float32 fields
    if reader.offset == start_struct_position + struct_size:
        if num_vertices != 0 and num_triangles != 0:
            atomic["isNativeData"] = True
            # Skip to extension
            ext_header = parse_section_header(reader)
            atomic["extensionHeader"] = ext_header
            atomic["extensionData"] = reader.read_bytes(ext_header["size"]).hex()
            return atomic

    atomic["isNativeData"] = False

    # Reset to after header and read vertex data
    reader.offset = start_struct_position + header_size

    # Vertex Data - bulk unpack: stored as (x, y, z) tuples
    vert_raw = struct.unpack_from(f"<{num_vertices * 3}f", reader.data, reader.offset)
    reader.offset += num_vertices * 12
    atomic["vertices"] = [(vert_raw[i*3], vert_raw[i*3+1], vert_raw[i*3+2]) for i in range(num_vertices)]

    if not is_collision:
        # Check for two vertex color arrays
        # Expected size: header(44) + vertices(12*n) + colors(4*n) + uvs(8*n) + triangles(8*t)
        supposed_total_length = (
            header_size + (12 + 4 + 8) * num_vertices + 8 * num_triangles
        )
        two_vcolor_arrays = False

        extra_size = struct_size - supposed_total_length
        if num_vertices > 0 and extra_size in (num_vertices * 4, num_vertices * 12):
            two_vcolor_arrays = True

        atomic["twoColorArrays"] = two_vcolor_arrays

        # Skip first color array if there are two
        if two_vcolor_arrays:
            reader.offset += 4 * num_vertices

        # Color Data - bulk unpack: stored as (r, g, b, a) tuples
        col_raw = struct.unpack_from(f"<{num_vertices * 4}B", reader.data, reader.offset)
        reader.offset += num_vertices * 4
        atomic["colors"] = [(col_raw[i*4], col_raw[i*4+1], col_raw[i*4+2], col_raw[i*4+3]) for i in range(num_vertices)]

        # Reset position for UV data
        if two_vcolor_arrays:
            reader.offset = start_struct_position + header_size + 20 * num_vertices
        else:
            reader.offset = start_struct_position + header_size + 16 * num_vertices

        # UV Data - bulk unpack: stored as (u, v) tuples
        uv_raw = struct.unpack_from(f"<{num_vertices * 2}f", reader.data, reader.offset)
        reader.offset += num_vertices * 8
        atomic["uvs"] = [(uv_raw[i*2], uv_raw[i*2+1]) for i in range(num_vertices)]
    else:
        atomic["colors"] = []
        atomic["uvs"] = []

    # Triangle data is at the end of the struct
    reader.offset = start_struct_position + struct_size - 8 * num_triangles

    # Triangle Data - bulk unpack: stored as (v1, v2, v3, materialIndex) tuples
    tri_raw = struct.unpack_from(f"<{num_triangles * 4}H", reader.data, reader.offset)
    reader.offset += num_triangles * 8
    atomic["triangles"] = [(tri_raw[i*4], tri_raw[i*4+1], tri_raw[i*4+2], tri_raw[i*4+3]) for i in range(num_triangles)]

    # Ensure we're at the end of struct
    reader.offset = start_struct_position + struct_size

    # AtomicSector Extension Header
    ext_header = parse_section_header(reader)
    atomic["extensionHeader"] = ext_header
    atomic["extensionData"] = reader.read_bytes(ext_header["size"]).hex()

    return atomic


def parse_plane_sector(
    reader: BinaryReader, is_collision: bool = False
) -> Dict[str, Any]:
    """Parse a PlaneSector section (0x000A) recursively."""
    plane = {}

    # PlaneSector Header (identifier already read by caller)
    plane["size"] = reader.read_int32()
    plane["version"] = reader.read_int32()

    # PlaneStruct Header
    struct_header = parse_section_header(reader)
    plane["structHeader"] = struct_header

    # PlaneStruct Data
    plane["type"] = reader.read_int32()
    plane["value"] = reader.read_float32()
    left_is_atomic = reader.read_int32()
    right_is_atomic = reader.read_int32()
    plane["leftIsAtomic"] = left_is_atomic
    plane["rightIsAtomic"] = right_is_atomic
    plane["leftValue"] = reader.read_float32()
    plane["rightValue"] = reader.read_float32()

    # Left child
    left_section_id = reader.read_uint32()
    if left_is_atomic == 1:
        if left_section_id != 0x0009:
            raise ValueError(
                f"Expected AtomicSector (0x0009) for left child, got 0x{left_section_id:04X}"
            )
        plane["leftSection"] = {
            "type": "AtomicSector",
            "data": parse_atomic_sector(reader, is_collision),
        }
    else:
        if left_section_id != 0x000A:
            raise ValueError(
                f"Expected PlaneSector (0x000A) for left child, got 0x{left_section_id:04X}"
            )
        plane["leftSection"] = {
            "type": "PlaneSector",
            "data": parse_plane_sector(reader, is_collision),
        }

    # Right child
    right_section_id = reader.read_uint32()
    if right_is_atomic == 1:
        if right_section_id != 0x0009:
            raise ValueError(
                f"Expected AtomicSector (0x0009) for right child, got 0x{right_section_id:04X}"
            )
        plane["rightSection"] = {
            "type": "AtomicSector",
            "data": parse_atomic_sector(reader, is_collision),
        }
    else:
        if right_section_id != 0x000A:
            raise ValueError(
                f"Expected PlaneSector (0x000A) for right child, got 0x{right_section_id:04X}"
            )
        plane["rightSection"] = {
            "type": "PlaneSector",
            "data": parse_plane_sector(reader, is_collision),
        }

    return plane


def parse_world_chunk(
    reader: BinaryReader,
    num_atomic_sectors: int,
    num_plane_sectors: int,
    is_collision: bool = False,
) -> Optional[Dict[str, Any]]:
    """Parse the first world chunk (AtomicSector or PlaneSector)."""
    section_id = reader.read_uint32()

    if num_atomic_sectors == 1 and num_plane_sectors == 0:
        if section_id != 0x0009:
            raise ValueError(f"Expected AtomicSector (0x0009), got 0x{section_id:04X}")
        return {
            "type": "AtomicSector",
            "data": parse_atomic_sector(reader, is_collision),
        }
    elif num_plane_sectors > 0:
        if section_id != 0x000A:
            raise ValueError(f"Expected PlaneSector (0x000A), got 0x{section_id:04X}")
        return {
            "type": "PlaneSector",
            "data": parse_plane_sector(reader, is_collision),
        }

    return None


def parse(
    data: bytes, is_collision: bool = False
) -> Dict[str, Any]:
    """
    Parse binary World (0x000B) data.

    Args:
        data: Binary data to parse
        is_collision: If True, skip color and UV data in AtomicSectors
        use triangle format v1,v2,v3,mat

    Returns:
        Dictionary containing all parsed values
    """
    reader = BinaryReader(data)
    result = {}

    # World Header (0x000B)
    result["sectionIdentifier"] = reader.read_uint32()
    if result["sectionIdentifier"] != 0x000B:
        raise ValueError(
            f"Expected World section (0x000B), got 0x{result['sectionIdentifier']:04X}"
        )
    result["sectionSize"] = reader.read_int32()
    result["renderWareVersion"] = reader.read_int32()

    # WorldStruct Header (0x0001)
    result["worldStructIdentifier"] = reader.read_uint32()
    world_struct_size = reader.read_int32()
    result["worldStructSize"] = world_struct_size
    result["worldStructVersion"] = reader.read_int32()

    # WorldStruct Data (varies based on size)
    result["rootIsWorldSector"] = reader.read_int32()
    result["inverseOrigin"] = {
        "x": reader.read_float32(),
        "y": reader.read_float32(),
        "z": reader.read_float32(),
    }

    if world_struct_size == 0x40:
        result["numTriangles"] = reader.read_uint32()
        result["numVertices"] = reader.read_uint32()
        result["numPlaneSectors"] = reader.read_uint32()
        result["numAtomicSectors"] = reader.read_uint32()
        result["colSectorSize"] = reader.read_uint32()
        result["worldFlags"] = reader.read_uint32()
        result["boxMax"] = {
            "x": reader.read_float32(),
            "y": reader.read_float32(),
            "z": reader.read_float32(),
        }
        result["boxMin"] = {
            "x": reader.read_float32(),
            "y": reader.read_float32(),
            "z": reader.read_float32(),
        }
    elif world_struct_size == 0x34:
        result["boxMax"] = {
            "x": reader.read_float32(),
            "y": reader.read_float32(),
            "z": reader.read_float32(),
        }
        result["numTriangles"] = reader.read_uint32()
        result["numVertices"] = reader.read_uint32()
        result["numPlaneSectors"] = reader.read_uint32()
        result["numAtomicSectors"] = reader.read_uint32()
        result["colSectorSize"] = reader.read_uint32()
        result["worldFlags"] = reader.read_uint32()
    else:
        raise ValueError(f"Unknown worldStructSize: 0x{world_struct_size:X}")

    # MaterialList
    result["materialList"] = parse_material_list(reader)

    # First World Chunk (AtomicSector or PlaneSector tree)
    result["worldChunk"] = parse_world_chunk(
        reader,
        result["numAtomicSectors"],
        result["numPlaneSectors"],
        is_collision,
    )

    # World Extension Header (0x0003)
    result["worldExtIdentifier"] = reader.read_uint32()
    world_ext_size = reader.read_int32()
    result["worldExtSize"] = world_ext_size
    result["worldExtVersion"] = reader.read_int32()
    result["worldExtData"] = reader.read_bytes(world_ext_size).hex()

    return result


def parse_file(
    filepath: str, is_collision: bool = False
) -> Dict[str, Any]:
    """
    Parse a binary file.

    Args:
        filepath: Path to the binary file
        is_collision: If True, skip color and UV data in AtomicSectors

    Returns:
        Dictionary containing all parsed values
    """
    with open(filepath, "rb") as f:
        data = f.read()
    return parse(data, is_collision)


def collect_atomic_sectors(chunk: Optional[Dict[str, Any]]) -> list:
    """Recursively collect all AtomicSector data from the BSP tree."""
    if chunk is None:
        return []

    sectors = []
    if chunk["type"] == "AtomicSector":
        sectors.append(chunk["data"])
    elif chunk["type"] == "PlaneSector":
        plane_data = chunk["data"]
        sectors.extend(collect_atomic_sectors(plane_data.get("leftSection")))
        sectors.extend(collect_atomic_sectors(plane_data.get("rightSection")))

    return sectors


# ═══════════════════════════════════════════════════════════════════
# BSP writing — mirrors the output of the original TFB/RenderWare tools
# ═══════════════════════════════════════════════════════════════════


def _chunk(ctype: int, payload: bytes, stamp: int) -> bytes:
    """Wrap a payload in a standard RW section header."""
    return struct.pack("<IiI", ctype, len(payload), stamp) + payload


def _struct_chunk(payload: bytes, stamp: int) -> bytes:
    return _chunk(0x0001, payload, stamp)


def _string_chunk(s: str, stamp: int) -> bytes:
    """RW string chunk (0x0002), NUL-terminated and padded to 4 bytes."""
    raw = s.encode("ascii", errors="replace") + b"\x00"
    raw += b"\x00" * (-len(raw) % 4)
    return _chunk(0x0002, raw, stamp)


def parse_material_extension(ext_hex: str) -> Dict[str, Any]:
    """Parse the TFB material extension chunk (0x800000F6).

    Payload layout (33 bytes): magic(4) flags(4) blendState(4) alphaRef(4) blendFunc(4) + 13 trailing bytes
    Returns a dict with all fields for round-trip storage.
    """
    default: Dict[str, Any] = {
        "magic": 0x0F0F000D,
        "flags": 0x201,
        "blend_state": 0,
        "alpha_ref": 2,
        "blend_func": 8,
        "extra_hex": "00" * 13,
    }
    if not ext_hex:
        return default
    try:
        ext_data = bytes.fromhex(ext_hex)
    except ValueError:
        return default

    off = 0
    while off + 12 <= len(ext_data):
        ctype, csize, _ = struct.unpack_from("<IiI", ext_data, off)
        off += 12
        if csize < 0 or off + csize > len(ext_data):
            break
        if ctype == 0x800000F6 and csize >= 20:
            magic, flags, blend_state, alpha_ref, blend_func = struct.unpack_from(
                "<IIIII", ext_data, off
            )
            extra = ext_data[off + 20: off + csize]
            return {
                "magic": magic,
                "flags": flags,
                "blend_state": blend_state,
                "alpha_ref": alpha_ref,
                "blend_func": blend_func,
                "extra_hex": extra.hex(),
            }
        off += csize
    return default


def write_material_extension_from_parsed(parsed: Dict[str, Any], stamp: int = DEFAULT_VERSION_STAMP) -> bytes:
    """Serialize a parsed material extension dict back to RW bytes (full 0x800000F6 chunk)."""
    try:
        extra = bytes.fromhex(parsed.get("extra_hex", ""))
    except ValueError:
        extra = b""
    if not extra:
        extra = b"\x00" * 13
    payload = struct.pack(
        "<IIIII",
        parsed.get("magic", 0x0F0F000D) & 0xFFFFFFFF,
        parsed.get("flags", 0x201) & 0xFFFFFFFF,
        parsed.get("blend_state", 0) & 0xFFFFFFFF,
        parsed.get("alpha_ref", 2) & 0xFFFFFFFF,
        parsed.get("blend_func", 8) & 0xFFFFFFFF,
    ) + extra
    return _chunk(0x800000F6, payload, stamp)


def parse_texture_extension(ext_hex: str) -> Dict[str, Any]:
    """Parse the texture extension: Sky Mipmap Val (0x0110) + TFB plugin (0x800000DD)."""
    result: Dict[str, Any] = {
        "sky_mip_val": 0x0F80,
        "tfb_magic": 0x0F0F0004,
        "tfb_d1": 0,
        "tfb_d2": 0,
    }
    if not ext_hex:
        return result
    try:
        ext_data = bytes.fromhex(ext_hex)
    except ValueError:
        return result

    off = 0
    while off + 12 <= len(ext_data):
        ctype, csize, _ = struct.unpack_from("<IiI", ext_data, off)
        off += 12
        if csize < 0 or off + csize > len(ext_data):
            break
        if ctype == 0x0110 and csize >= 4:
            result["sky_mip_val"] = struct.unpack_from("<I", ext_data, off)[0]
        elif ctype == 0x800000DD and csize >= 12:
            m, d1, d2 = struct.unpack_from("<III", ext_data, off)
            result["tfb_magic"] = m
            result["tfb_d1"] = d1
            result["tfb_d2"] = d2
        off += csize
    return result


def write_texture_extension_from_parsed(parsed: Dict[str, Any], stamp: int = DEFAULT_VERSION_STAMP) -> bytes:
    """Serialize a parsed texture extension dict back to RW bytes."""
    return (
        _chunk(0x0110, struct.pack("<I", parsed.get("sky_mip_val", 0x0F80) & 0xFFFFFFFF), stamp)
        + _chunk(
            0x800000DD,
            struct.pack(
                "<III",
                parsed.get("tfb_magic", 0x0F0F0004) & 0xFFFFFFFF,
                parsed.get("tfb_d1", 0) & 0xFFFFFFFF,
                parsed.get("tfb_d2", 0) & 0xFFFFFFFF,
            ),
            stamp,
        )
    )


def parse_world_extension(ext_hex: str) -> Dict[str, Any]:
    """Parse the world extension: TFB world plugin chunk (0x800000B0)."""
    result: Dict[str, Any] = {"magic": 0x0F0F0003, "d1": 0, "d2": 0, "d3": 0}
    if not ext_hex:
        return result
    try:
        ext_data = bytes.fromhex(ext_hex)
    except ValueError:
        return result

    off = 0
    while off + 12 <= len(ext_data):
        ctype, csize, _ = struct.unpack_from("<IiI", ext_data, off)
        off += 12
        if csize < 0 or off + csize > len(ext_data):
            break
        if ctype == 0x800000B0 and csize >= 16:
            m, d1, d2, d3 = struct.unpack_from("<IIII", ext_data, off)
            result["magic"] = m
            result["d1"] = d1
            result["d2"] = d2
            result["d3"] = d3
        off += csize
    return result


def write_world_extension_from_parsed(parsed: Dict[str, Any], stamp: int = DEFAULT_VERSION_STAMP) -> bytes:
    """Serialize a parsed world extension dict back to RW bytes (full 0x800000B0 chunk)."""
    return _chunk(
        0x800000B0,
        struct.pack(
            "<IIII",
            parsed.get("magic", 0x0F0F0003) & 0xFFFFFFFF,
            parsed.get("d1", 0) & 0xFFFFFFFF,
            parsed.get("d2", 0) & 0xFFFFFFFF,
            parsed.get("d3", 0) & 0xFFFFFFFF,
        ),
        stamp,
    )


def default_material_extension(transparent: bool = False, stamp: int = DEFAULT_VERSION_STAMP) -> bytes:
    """TFB material chunk (0x800000F6) as written by the original tools.

    Payload: magic 0x0F0F000D, flags 0x201, blendState, alphaRef?, blendFunc?,
    then 13 zero bytes (33 bytes total). blendState 0/blendFunc 8 = opaque,
    blendState 3/blendFunc 5 = alpha blended.
    """
    blend_state, blend_func = (3, 5) if transparent else (0, 8)
    payload = struct.pack("<IIIII", 0x0F0F000D, 0x201, blend_state, 2, blend_func) + b"\x00" * 13
    return _chunk(0x800000F6, payload, stamp)


def default_texture_extension(stamp: int = DEFAULT_VERSION_STAMP) -> bytes:
    """Texture extension as in shipped files: Sky Mipmap Val + TFB 0x800000DD."""
    return _chunk(0x0110, struct.pack("<I", 0x0F80), stamp) + _chunk(
        0x800000DD, struct.pack("<III", 0x0F0F0004, 0, 0), stamp
    )


def default_world_extension(stamp: int = DEFAULT_VERSION_STAMP) -> bytes:
    """Minimal TFB world chunk (0x800000B0) accepted by the game."""
    return _chunk(0x800000B0, struct.pack("<IIII", 0x0F0F0003, 0, 0, 0), stamp)


def _sector_tfb_extension(stamp: int, has_geometry: bool) -> bytes:
    """TFB per-sector chunks (0x800000D4 + 0x800000FE) as in shipped files.

    The third dword of the 0x800000FE payload is 1 on every shipped sector
    that contains geometry and 0 on empty ones — the engine appears to use
    it as a "sector has renderable content" flag, so getting it wrong makes
    the game silently draw nothing.
    """
    return _chunk(0x800000D4, struct.pack("<III", 0x0F0F0003, 0, 0), stamp) + _chunk(
        0x800000FE,
        struct.pack("<IIII", 0x0F0F0003, 0, 1 if has_geometry else 0, 0),
        stamp,
    )


def build_tristrips(triangles: List[Tuple[int, int, int]]) -> List[int]:
    """Stripify triangles into a single index strip (RW/GL semantics:
    strip triangle k is winding-flipped when k is odd).

    Greedy walk with the classic SGI heuristics: seed at triangles with the
    fewest unused neighbors (chain ends), rotate the seed so the walk starts
    at a dead end, and on ties continue into the neighbor with the fewest
    unused neighbors. Substrips are stitched with degenerate triangles,
    padded so winding parity stays correct.
    """
    # directed edge (u, v) -> list of (triangle index, third vertex w)
    # where the triangle winds (u, v, w)
    edge_map: Dict[Tuple[int, int], List[Tuple[int, int]]] = {}
    used = [False] * len(triangles)
    for ti, (a, b, c) in enumerate(triangles):
        if a == b or b == c or a == c:
            used[ti] = True  # degenerate: renders nothing, keep out of strips
            continue
        for u, v, w in ((a, b, c), (b, c, a), (c, a, b)):
            edge_map.setdefault((u, v), []).append((ti, w))

    def unused_neighbors(ti: int) -> int:
        a, b, c = triangles[ti]
        count = 0
        for u, v in ((a, b), (b, c), (c, a)):
            # A neighbor continuing our edge (u, v) winds it as (v, u).
            for tj, _ in edge_map.get((v, u), ()):
                if not used[tj]:
                    count += 1
        return count

    def pick_continuation(need: Tuple[int, int]) -> Optional[Tuple[int, int]]:
        best = None
        best_count = None
        for ti, w in edge_map.get(need, ()):
            if used[ti]:
                continue
            n = unused_neighbors(ti)
            if best_count is None or n < best_count:
                best, best_count = (ti, w), n
        return best

    # Seed order: boundary triangles (fewest neighbors) first.
    seeds = sorted(range(len(triangles)), key=unused_neighbors)

    strip: List[int] = []
    for seed in seeds:
        if used[seed]:
            continue

        # Rotate the seed so the strip starts at a dead end: prefer a rotation
        # with no unused triangle continuing *into* (a, b), and among those the
        # most continuations out of (b, c).
        best_rot = None
        best_key = None
        for rot in range(3):
            t = triangles[seed]
            a, b, c = t[rot % 3], t[(rot + 1) % 3], t[(rot + 2) % 3]
            incoming = any(
                not used[ti] for ti, _ in edge_map.get((b, a), ())
            )
            outgoing = sum(
                1 for ti, _ in edge_map.get((c, b), ()) if not used[ti]
            )
            key = (incoming, -outgoing)
            if best_key is None or key < best_key:
                best_key = key
                best_rot = (a, b, c)
        a, b, c = best_rot
        used[seed] = True

        if not strip:
            strip.extend((a, b, c))
        else:
            # Stitch: duplicate the last vertex and the new first vertex so
            # every bridging triangle is degenerate, padding so the new
            # triangle lands on an even strip index (correct winding).
            strip.append(strip[-1])
            if len(strip) % 2 == 0:
                strip.append(strip[-1])
            strip.extend((a, a, b, c))

        # Extend while an unused neighbor shares the trailing edge.
        while True:
            u, v = strip[-2], strip[-1]
            # Triangle index of the candidate: k = len(strip) - 2.
            # Even k needs winding (u, v, w); odd k needs (v, u, w).
            need = (u, v) if (len(strip) - 2) % 2 == 0 else (v, u)
            cont = pick_continuation(need)
            if cont is None:
                break
            ti, w = cont
            used[ti] = True
            strip.append(w)

    return strip


def decode_tristrip(strip: List[int]) -> List[Tuple[int, int, int]]:
    """Inverse of build_tristrips (drops degenerates). Useful for validation."""
    tris = []
    for k in range(len(strip) - 2):
        a, b, c = strip[k], strip[k + 1], strip[k + 2]
        if a == b or b == c or a == c:
            continue
        tris.append((a, b, c) if k % 2 == 0 else (b, a, c))
    return tris


def _binmesh_extension(
    triangles: List[Tuple[int, int, int, int]],
    stamp: int,
    tristrip: bool = True,
) -> bytes:
    """BinMesh PLG (0x050E): triangles grouped per material, stripified.

    Empty sectors get the same empty (flags=0, 0 meshes) chunk shipped files have.
    """
    if not triangles:
        return _chunk(0x050E, struct.pack("<III", 0, 0, 0), stamp)

    by_mat: Dict[int, List[Tuple[int, int, int]]] = {}
    for v0, v1, v2, mat in triangles:
        if v0 == v1 or v1 == v2 or v0 == v2:
            continue  # degenerate: renders nothing
        by_mat.setdefault(mat, []).append((v0, v1, v2))
    if not by_mat:
        return _chunk(0x050E, struct.pack("<III", 0, 0, 0), stamp)

    meshes = []
    total = 0
    for mat in sorted(by_mat):
        if tristrip:
            indices = build_tristrips(by_mat[mat])
        else:
            indices = [i for tri in by_mat[mat] for i in tri]
        meshes.append((mat, indices))
        total += len(indices)

    payload = struct.pack("<III", 1 if tristrip else 0, len(meshes), total)
    for mat, indices in meshes:
        payload += struct.pack("<II", len(indices), mat)
        payload += struct.pack(f"<{len(indices)}I", *indices)
    return _chunk(0x050E, payload, stamp)


def _write_texture(texture: Dict[str, Any], stamp: int) -> bytes:
    ext_hex = texture.get("extensionData")
    ext = bytes.fromhex(ext_hex) if ext_hex else default_texture_extension(stamp)
    body = _struct_chunk(
        struct.pack(
            "<BBH",
            texture.get("filterMode", 2),
            texture.get("addressModes", 17),
            texture.get("useMipLevels", 1),
        ),
        stamp,
    )
    body += _string_chunk(texture.get("diffuseTextureName", ""), stamp)
    body += _string_chunk(texture.get("alphaTextureName", ""), stamp)
    body += _chunk(0x0003, ext, stamp)
    return _chunk(0x0006, body, stamp)


def _write_material(mat: Dict[str, Any], stamp: int) -> bytes:
    color = mat.get("color", {})
    is_textured = 1 if (mat.get("isTextured") and mat.get("texture")) else 0
    body = _struct_chunk(
        struct.pack(
            "<i4BiIfff",
            mat.get("unusedFlags", 0),
            color.get("r", 255) & 0xFF,
            color.get("g", 255) & 0xFF,
            color.get("b", 255) & 0xFF,
            color.get("a", 255) & 0xFF,
            mat.get("unusedInt2", DEFAULT_MATERIAL_UNUSED_INT2),
            is_textured,
            mat.get("ambient", 1.0),
            mat.get("specular", 0.0),
            mat.get("diffuse", 1.0),
        ),
        stamp,
    )
    if is_textured:
        body += _write_texture(mat["texture"], stamp)
    ext_hex = mat.get("extensionData")
    if ext_hex:
        ext = bytes.fromhex(ext_hex)
    else:
        ext = default_material_extension(mat.get("transparent", False), stamp)
    body += _chunk(0x0003, ext, stamp)
    return _chunk(0x0007, body, stamp)


def _write_material_list(materials: List[Dict[str, Any]], stamp: int) -> bytes:
    body = _struct_chunk(
        struct.pack(f"<i{len(materials)}i", len(materials), *([-1] * len(materials))),
        stamp,
    )
    for mat in materials:
        body += _write_material(mat, stamp)
    return _chunk(0x0008, body, stamp)


def _bounds(verts: List[Tuple[float, float, float]]):
    xs = [v[0] for v in verts]
    ys = [v[1] for v in verts]
    zs = [v[2] for v in verts]
    return (max(xs), max(ys), max(zs)), (min(xs), min(ys), min(zs))


def build_sector_tree(
    vertices: List[Tuple[float, float, float]],
    colors: List[Tuple[int, int, int, int]],
    uvs: List[Tuple[float, float]],
    triangles: List[Tuple[int, int, int, int]],
    max_triangles: int = 1024,
    max_vertices: int = 60000,
) -> Dict[str, Any]:
    """Recursively split triangles into a BSP tree of atomic sectors.

    Median splits on the largest bounding-box axis, like the original RW world
    importer. Triangles are never clipped — each goes wholly to one side and
    the plane sector stores overlapping left/right extents (the shipped worlds
    set rpWORLDSECTORSOVERLAP for exactly this reason).
    Returns a tree of {"type": "atomic"|"plane", ...} nodes.
    """

    def leaf(tri_ids: List[int]) -> Dict[str, Any]:
        remap: Dict[int, int] = {}
        sec_verts: List[Tuple[float, float, float]] = []
        sec_colors: List[Tuple[int, int, int, int]] = []
        sec_uvs: List[Tuple[float, float]] = []
        sec_tris = []
        for ti in tri_ids:
            v0, v1, v2, mat = triangles[ti]
            idx = []
            for v in (v0, v1, v2):
                if v not in remap:
                    remap[v] = len(sec_verts)
                    sec_verts.append(vertices[v])
                    sec_colors.append(colors[v])
                    sec_uvs.append(uvs[v])
                idx.append(remap[v])
            sec_tris.append((idx[0], idx[1], idx[2], mat))
        return {
            "type": "atomic",
            "vertices": sec_verts,
            "colors": sec_colors,
            "uvs": sec_uvs,
            "triangles": sec_tris,
        }

    def tri_verts(ti: int):
        v0, v1, v2, _ = triangles[ti]
        return vertices[v0], vertices[v1], vertices[v2]

    def split(tri_ids: List[int]) -> Dict[str, Any]:
        vert_count = len({v for ti in tri_ids for v in triangles[ti][:3]})
        if len(tri_ids) <= max_triangles and vert_count <= max_vertices:
            return leaf(tri_ids)

        vmax, vmin = _bounds([p for ti in tri_ids for p in tri_verts(ti)])
        extents = [vmax[i] - vmin[i] for i in range(3)]
        axis = extents.index(max(extents))

        centroids = [
            (sum(p[axis] for p in tri_verts(ti)) / 3.0, ti) for ti in tri_ids
        ]
        centroids.sort(key=lambda e: e[0])
        mid = len(centroids) // 2
        value = centroids[mid][0]
        left_ids = [ti for _, ti in centroids[:mid]]
        right_ids = [ti for _, ti in centroids[mid:]]
        if not left_ids or not right_ids:  # all centroids equal — force split
            left_ids = [ti for _, ti in centroids[: len(centroids) // 2]]
            right_ids = [ti for _, ti in centroids[len(centroids) // 2 :]]

        left_value = max(p[axis] for ti in left_ids for p in tri_verts(ti))
        right_value = min(p[axis] for ti in right_ids for p in tri_verts(ti))
        return {
            "type": "plane",
            "axis": axis,  # 0/1/2 -> plane type 0/4/8 (byte offset in RwV3d)
            "value": value,
            "leftValue": left_value,
            "rightValue": right_value,
            "left": split(left_ids),
            "right": split(right_ids),
        }

    return split(list(range(len(triangles))))


def _write_atomic_sector(
    node: Dict[str, Any],
    stamp: int,
    tristrip: bool,
    write_binmesh: bool = True,
    coll_value: int = 0,
) -> bytes:
    verts = node["vertices"]
    tris = node["triangles"]
    if verts:
        (bx, by, bz), (nx, ny, nz) = _bounds(verts)
    else:
        bx = by = bz = nx = ny = nz = 0.0

    payload = struct.pack(
        "<iii6fii",
        0,  # matListWindowBase — triangles carry global material indices
        len(tris),
        len(verts),
        bx, by, bz, nx, ny, nz,
        coll_value,  # shipped files carry worldFlags & 0xFF here (or stack garbage)
        0,  # unused
    )
    payload += struct.pack(f"<{len(verts) * 3}f", *[c for v in verts for c in v])
    payload += struct.pack(
        f"<{len(verts) * 4}B",
        *[min(255, max(0, int(c))) for col in node["colors"] for c in col],
    )
    payload += struct.pack(f"<{len(verts) * 2}f", *[c for uv in node["uvs"] for c in uv])
    payload += struct.pack(f"<{len(tris) * 4}H", *[i for t in tris for i in t])

    ext = _sector_tfb_extension(stamp, bool(tris))
    if tris:
        # MaterialEffectsPLG sector extension — present (payload 1) on every
        # shipped sector that has geometry.
        ext = _chunk(0x0120, struct.pack("<I", 1), stamp) + ext
    if write_binmesh:
        ext = _binmesh_extension(tris, stamp, tristrip) + ext
    body = _struct_chunk(payload, stamp) + _chunk(0x0003, ext, stamp)
    return _chunk(0x0009, body, stamp)


def _write_sector_node(
    node: Dict[str, Any],
    stamp: int,
    tristrip: bool,
    write_binmesh: bool = True,
    coll_value: int = 0,
) -> bytes:
    if node["type"] == "atomic":
        return _write_atomic_sector(node, stamp, tristrip, write_binmesh, coll_value)

    left = node["left"]
    right = node["right"]
    payload = struct.pack(
        "<ifiiff",
        node["axis"] * 4,  # rwPLANE_X/Y/Z = byte offset into RwV3d
        node["value"],
        1 if left["type"] == "atomic" else 0,
        1 if right["type"] == "atomic" else 0,
        node["leftValue"],
        node["rightValue"],
    )
    body = _struct_chunk(payload, stamp)
    body += _write_sector_node(left, stamp, tristrip, write_binmesh, coll_value)
    body += _write_sector_node(right, stamp, tristrip, write_binmesh, coll_value)
    return _chunk(0x000A, body, stamp)


def _count_sectors(node: Dict[str, Any]) -> Tuple[int, int]:
    """Returns (numPlaneSectors, numAtomicSectors)."""
    if node["type"] == "atomic":
        return 0, 1
    pl, al = _count_sectors(node["left"])
    pr, ar = _count_sectors(node["right"])
    return pl + pr + 1, al + ar


def _collect_tree_leaves(node: Dict[str, Any]) -> List[Dict[str, Any]]:
    if node["type"] == "atomic":
        return [node]
    return _collect_tree_leaves(node["left"]) + _collect_tree_leaves(node["right"])


def build_world(
    vertices: List[Tuple[float, float, float]],
    colors: List[Tuple[int, int, int, int]],
    uvs: List[Tuple[float, float]],
    triangles: List[Tuple[int, int, int, int]],
    materials: List[Dict[str, Any]],
    world_flags: int = DEFAULT_WORLD_FLAGS,
    stamp: int = DEFAULT_VERSION_STAMP,
    world_extension: Optional[bytes] = None,
    inverse_origin: Tuple[float, float, float] = (-0.0, -0.0, -0.0),
    root_is_world_sector: int = 0,
    max_triangles_per_sector: int = 1024,
    tristrip: bool = True,
    write_binmesh: bool = True,
) -> bytes:
    """Serialize a complete RW World (0x000B) the way the original tools did.

    Geometry is in RenderWare space (Y up, same as the parsed files); triangle
    tuples are (v0, v1, v2, globalMaterialIndex).
    """
    if not triangles:
        raise ValueError("Cannot export a BSP without triangles")
    if not materials:
        raise ValueError("Cannot export a BSP without materials")

    tree = build_sector_tree(
        vertices, colors, uvs, triangles, max_triangles=max_triangles_per_sector
    )
    num_planes, num_atomics = _count_sectors(tree)
    leaves = _collect_tree_leaves(tree)
    total_tris = sum(len(l["triangles"]) for l in leaves)
    total_verts = sum(len(l["vertices"]) for l in leaves)
    (bx, by, bz), (nx, ny, nz) = _bounds(vertices)

    if write_binmesh:
        if tristrip:
            world_flags |= 0x1
        else:
            world_flags &= ~0x1

    world_struct = struct.pack(
        "<i3f6I6f",
        root_is_world_sector,
        *inverse_origin,
        total_tris,
        total_verts,
        num_planes,
        num_atomics,
        0,  # colSectorSize
        world_flags & 0xFFFFFFFF,
        bx, by, bz, nx, ny, nz,
    )

    body = _struct_chunk(world_struct, stamp)
    body += _write_material_list(materials, stamp)
    body += _write_sector_node(
        tree, stamp, tristrip, write_binmesh, world_flags & 0xFF
    )
    if world_extension is None:
        world_extension = default_world_extension(stamp)
    body += _chunk(0x0003, world_extension, stamp)
    return _chunk(0x000B, body, stamp)


def write_bsp_file(filepath: str, *args, **kwargs) -> None:
    """Build a world (see build_world) and write it to disk."""
    data = build_world(*args, **kwargs)
    with open(filepath, "wb") as f:
        f.write(data)


def write_mtl(filepath: str, materials: list, texture_prefix: str = "", mat_suffix: str = ""):
    """Write materials to MTL file."""
    with open(filepath, "w") as f:
        for i, mat in enumerate(materials):
            f.write(f"newmtl material_{i}_{mat_suffix}\n")

            # Color (convert 0-255 to 0-1)
            color = mat.get("color", {})
            r = color.get("r", 255) / 255.0
            g = color.get("g", 255) / 255.0
            b = color.get("b", 255) / 255.0

            f.write(f"Kd {r:.6f} {g:.6f} {b:.6f}\n")
            f.write(
                f"Ka {mat.get('ambient', 0.1):.6f} {mat.get('ambient', 0.1):.6f} {mat.get('ambient', 0.1):.6f}\n"
            )
            f.write(
                f"Ks {mat.get('specular', 0.0):.6f} {mat.get('specular', 0.0):.6f} {mat.get('specular', 0.0):.6f}\n"
            )

            # Alpha
            a = color.get("a", 255) / 255.0
            if a < 1.0:
                f.write(f"d {a:.6f}\n")

            # Texture
            if mat.get("isTextured") and mat.get("texture"):
                tex_name = mat["texture"].get("diffuseTextureName", "")
                if tex_name:
                    f.write(f"map_Kd {texture_prefix}{tex_name}.png\n")

            f.write("\n")


def write_obj(output_path: str, filename: str, world_data: dict, texture_prefix: str = "", scale: float = 1.0):
    """Write parsed world data to OBJ file, optionally scaling geometry."""
    import os
    
    mat_suffix = str(random.randint(1000, 9999))

    sectors = collect_atomic_sectors(world_data.get("worldChunk", []))
    if not sectors:
        print("No geometry found in BSP")
        return

    materials = world_data.get("materialList", {}).get("materials", [])
    obj_path = os.path.join(output_path, f"{filename}.obj")
    mtl_path = os.path.join(output_path, f"{filename}.mtl")

    write_mtl(mtl_path, materials, texture_prefix, mat_suffix)

    vertex_offset = 0
    uv_offset = 0

    with open(obj_path, "w") as f:
        f.write("# RenderWare World BSP Export\n")
        f.write(f"# Vertices: {world_data.get('numVertices', 0)}\n")
        f.write(f"# Triangles: {world_data.get('numTriangles', 0)}\n")
        f.write(f"mtllib {filename}.mtl\n\n")

        for sector_idx, sector in enumerate(sectors):
            if sector.get("isNativeData"):
                continue

            vertices = sector.get("vertices", [])
            uvs = sector.get("uvs", [])
            triangles = sector.get("triangles", [])

            if not vertices:
                continue

            f.write(f"# Sector {sector_idx}\n")
            f.write(f"g sector_{sector_idx}\n")

            # Write vertices with scaling
            for v in vertices:
                f.write(f"v {v[0]*scale:.6f} {v[1]*scale:.6f} {v[2]*scale:.6f}\n")

            # Write UVs (V flipped)
            for uv in uvs:
                f.write(f"vt {uv[0]:.6f} {1.0 - uv[1]:.6f}\n")

            # Group triangles by material (add matListWindowBase to get actual material index)
            mat_base = sector.get("matListWindowBase", 0)
            tris_by_mat = {}
            for tri in triangles:
                mat_idx = mat_base + tri[3]
                tris_by_mat.setdefault(mat_idx, []).append(tri)

            # Write faces grouped by material
            for mat_idx in sorted(tris_by_mat.keys()):
                f.write(f"usemtl material_{mat_idx}_{mat_suffix}\n")
                for tri in tris_by_mat[mat_idx]:
                    v1 = tri[0] + vertex_offset + 1
                    v2 = tri[1] + vertex_offset + 1
                    v3 = tri[2] + vertex_offset + 1

                    if uvs:
                        vt1 = tri[0] + uv_offset + 1
                        vt2 = tri[1] + uv_offset + 1
                        vt3 = tri[2] + uv_offset + 1
                        f.write(f"f {v1}/{vt1} {v2}/{vt2} {v3}/{vt3}\n")
                    else:
                        f.write(f"f {v1} {v2} {v3}\n")

            vertex_offset += len(vertices)
            uv_offset += len(uvs)
            f.write("\n")

    print(f"Wrote {obj_path}")
    print(f"Wrote {mtl_path}")

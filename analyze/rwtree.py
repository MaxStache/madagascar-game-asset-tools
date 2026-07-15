"""Recursive RenderWare chunk tree reader."""

import formats.lib.rw_basics as rw_basics
import formats.lib.rwConstants as rw_constants
import formats.lib.parser as parser

RWHeader = rw_basics.RWHeader
RWSectionType = rw_constants.RWSectionType
Parser = parser.Parser

CONTAINER_CHUNKS = {
    RWSectionType.rwID_CLUMP.value,
    RWSectionType.rwID_FRAMELIST.value,
    RWSectionType.rwID_GEOMETRY.value,
    RWSectionType.rwID_GEOMETRYLIST.value,
    RWSectionType.rwID_TEXDICTIONARY.value,
    RWSectionType.rwID_TEXTURENATIVE.value,
    RWSectionType.rwID_EXTENSION.value,
    RWSectionType.rwID_MATERIAL.value,
    RWSectionType.rwID_MATLIST.value,
    RWSectionType.rwID_ATOMIC.value,
    RWSectionType.rwID_TEXTURE.value,
    RWSectionType.rwID_LIGHT.value,
    RWSectionType.rwID_WORLD.value,
    RWSectionType.rwID_ATOMICSECT.value,
    RWSectionType.rwID_PLANESECT.value,

    #RW AUDIO
    RWSectionType.rwaID_WAVEDICT.value,
    RWSectionType.rwaID_WAVEDICT_WAVE.value,
    RWSectionType.rwaID_WAVE.value,
}

# Containers that carry their own fields before the first child chunk.
# Maps chunk type -> number of payload bytes to skip when descending.
CONTAINER_PREFIX_BYTES = {
    # uint32 total_subsongs, see formats/sections/RWA/WAVEDICT_WAVE_080C.py
    RWSectionType.rwaID_WAVEDICT_WAVE.value: 4,
}


def read_recursive(parser, depth=0):
    header = RWHeader.read(parser)

    if header.size > parser.remaining():
        # Malformed size field. Some files carry garbage in the high byte
        # (e.g. 0x0100000C for a 12-byte struct); fall back to the low 24
        # bits if that fits, otherwise clamp to what is actually left.
        masked = header.size & 0x00FFFFFF
        fixed = masked if masked <= parser.remaining() else parser.remaining()
        print(
            f"Warning: chunk 0x{header.type:X} at depth {depth} declares "
            f"size {header.size:#x} but only {parser.remaining()} bytes "
            f"remain; using {fixed}"
        )
        header.size = fixed

    data = parser.read(header.size)

    children = []
    if header.type in CONTAINER_CHUNKS:
        subparser = Parser(data, endian="little")
        subparser.skip(CONTAINER_PREFIX_BYTES.get(header.type, 0))
        while subparser.remaining() >= RWHeader.BYTE_SIZE:
            children.append(read_recursive(subparser, depth + 1))

    return header, data, children

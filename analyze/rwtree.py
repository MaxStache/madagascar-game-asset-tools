"""Recursive RenderWare chunk tree reader."""

import formats.lib.rw_basics as rw_basics
import formats.lib.rwConstants as rw_constants
import formats.lib.parser as parser

RWHeader = rw_basics.RWHeader
RWSectionType = rw_constants.RWSectionType
Parser = parser.Parser

CONTAINER_CHUNKS = {
    RWSectionType.rwID_CLUMP.value,
    RWSectionType.rwID_Frame.value,
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
}


def read_recursive(parser, depth=0):
    header = RWHeader.read(parser)
    data = parser.read(header.size)

    children = []
    if header.type in CONTAINER_CHUNKS:
        subparser = Parser(data, endian="little")
        while subparser.remaining() > 0:
            children.append(read_recursive(subparser, depth + 1))

    return header, data, children

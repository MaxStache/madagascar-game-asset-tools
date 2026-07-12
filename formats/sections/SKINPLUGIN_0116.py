import io
from dataclasses import dataclass, field

from formats.lib.writer import _write_u8, _write_f32, _write_u32
from formats.lib.parser import Parser
from formats.lib.rwConstants import RWSectionType
from formats.lib.rw_basics import RW_Section, RWHeader, expect_chunk_type_or_raise, RW_Matrix4x4, library_id_unpack


@dataclass
class RW_SkinPlugin_Bone:
    unused: int = 0  # u32 - Only stored if version < 0x37000 && maxVertexWeights == 0
    transform: RW_Matrix4x4 = field(
        default_factory=RW_Matrix4x4
    )  # f32[4][4] - Skin-to-Bone transform.


@dataclass
class RW_SkinPlugin_BoneGroup:
    firstBone: int = 0  # u8 - Index of first bone in boneRemaps array.
    numBones: int = 0  # u8 - Number of bones in boneRemaps that define the mesh (starting from firstBone).


@dataclass
class RW_SkinPlugin_BoneRemap:
    boneIndex: int = 0  # u8 - Index of the bone in boneRemapIndices.
    indices: int = 0  # u8 - The number of elements of the boneRemapIndices that are included by the group in boneRemapIndices.


@dataclass
class RW_SkinPlugin(RW_Section):
    """https://gtamods.com/wiki/Skin_PLG_(RW_Section)"""

    header: RWHeader = field(default_factory=RWHeader)

    numBones: int = 0  # Overall number of bones in the skeleton.
    usedBones: int = 0  # Number of bones affected by the skin.
    maxVertexWeights: int = (
        0  # Maximum number of non-zero weights per vertex. Can be 0 - 4,
        # if 0 engine attempts to figure out this number by looking into each weight array (see below) and counting the non-zero weights.
        # It then takes the largest number from the results.
    )
    _padding: bytes = field(
        default_factory=lambda: b"\x00"
    )  # Padding byte to align the structure to 4 bytes.

    # The number of vertices is obtained from the parent geometry section.
    affected_bone_indices: list[int] = field(
        default_factory=list
    )  # u8 each, length = usedBones  - A list of bone indices, that are affected by the skin.

    vertex_bone_mappings: list[list[tuple[int]]] = field(
        default_factory=list
    )  # (u8,u8,u8,u8) each, length = parent.struct.numVertices   - A list that maps all vertices to (up to) four bones of the skeleton.

    vertex_bone_mapping_weights: list[tuple[float]] = field(
        default_factory=list
    )  # (f32,f32,f32,f32) each, length = parent.struct.numVertices   - A list that weights each vertex-bone mapping.

    bone_transform_matrices: list[RW_SkinPlugin_Bone] = field(
        default_factory=list
    )  # f32[4][3] each, length = numBones   - A list of transformation matrices for each bone in the skeleton.

    # --- Bone Group Remapping ---
    # Unused in Madagascar and RenderWare-based GTA games

    boneLimit: int = 0  # u32 - the maximum number of bones per group. (?)
    numGroups: int = 0  # u32 - the number of bone groups.
    numRemaps: int = 0  # u32 - the number of bone remappings.

    boneRemapIndices: list[int] = field(
        default_factory=list
    )  # u8 each, length = numBones - an array of all bone indices where each element identifies a bone of the skeleton
    boneGroups: list[RW_SkinPlugin_BoneGroup] = field(
        default_factory=list
    )  # RW_SkinPlugin_BoneGroup each, length = numGroups
    boneRemaps: list[RW_SkinPlugin_BoneRemap] = field(
        default_factory=list
    )  # RW_SkinPlugin_BoneRemap each, length = numRemaps

    @staticmethod
    def read(parser: Parser, parent=None) -> "RW_SkinPlugin":
        skinplg = RW_SkinPlugin()
        skinplg.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            skinplg.header,
            RWSectionType.rwID_SKINPLUGIN.value,
            "RW_SkinPlugin chunk type",
        )

        skinplg.numBones = parser.readUint8()
        skinplg.usedBones = parser.readUint8()
        skinplg.maxVertexWeights = parser.readUint8()
        skinplg._padding = parser.readBytes(1)  # padding to align to 4 bytes

        for _ in range(skinplg.usedBones):
            skinplg.affected_bone_indices.append(parser.readUint8())

        if parent.header.type != RWSectionType.rwID_GEOMETRY.value:
            raise ValueError(
                "RW_SkinPlugin must be a child of RW_Geometry, but parent is "
                + RWSectionType(parent.header.type).name
            )

        pNumVertices = parent.struct.numVertices

        skinplg.vertex_bone_mappings = []
        for _ in range(pNumVertices):
            mapping = (
                parser.readUint8(),
                parser.readUint8(),
                parser.readUint8(),
                parser.readUint8(),
            )
            skinplg.vertex_bone_mappings.append(mapping)

        skinplg.vertex_bone_mapping_weights = []
        for _ in range(pNumVertices):
            weights = (
                parser.readFloat(),
                parser.readFloat(),
                parser.readFloat(),
                parser.readFloat(),
            )
            skinplg.vertex_bone_mapping_weights.append(weights)

        skinplg.bone_transform_matrices = []
        for _ in range(skinplg.numBones):
            unused = 0
            if skinplg.header.version < 0x37000 and skinplg.maxVertexWeights == 0:
                unused = (
                    parser.readUint32()
                )  # Only stored if version < 0x37000 && maxVertexWeights == 0

            skinplg.bone_transform_matrices.append(
                RW_SkinPlugin_Bone(unused, RW_Matrix4x4.read(parser))
            )

        skinplg.boneLimit = parser.readUint32()
        skinplg.numGroups = parser.readUint32()
        skinplg.numRemaps = parser.readUint32()

        if skinplg.numGroups > 0:
            for _ in range(skinplg.numBones):
                skinplg.boneRemapIndices.append(parser.readUint8())

            for _ in range(skinplg.numGroups):
                firstBone = parser.readUint8()
                numBones = parser.readUint8()
                skinplg.boneGroups.append(RW_SkinPlugin_BoneGroup(firstBone, numBones))

            for _ in range(skinplg.numRemaps):
                boneIndex = parser.readUint8()
                indices = parser.readUint8()
                skinplg.boneRemaps.append(RW_SkinPlugin_BoneRemap(boneIndex, indices))

        return skinplg

    def write(this, f, stamp, parent=None):
        buf = io.BytesIO()

        _write_u8(buf, len(this.bone_transform_matrices))
        _write_u8(buf, len(this.affected_bone_indices))
        _write_u8(buf, this.maxVertexWeights)
        _write_u8(buf, 0) # padding to align to 4 bytes

        for bone_index in this.affected_bone_indices:
            _write_u8(buf, bone_index)

        for m in this.vertex_bone_mappings:
             _write_u8(buf, m[0])
             _write_u8(buf, m[1])
             _write_u8(buf, m[2])
             _write_u8(buf, m[3])

        for w in this.vertex_bone_mapping_weights:
            _write_f32(buf, w[0])
            _write_f32(buf, w[1])
            _write_f32(buf, w[2])
            _write_f32(buf, w[3])

        for bone in this.bone_transform_matrices:
            if library_id_unpack(stamp)[0] < 0x37000 and this.maxVertexWeights == 0:
                _write_u32(buf, bone.unused) # Only stored if version < 0x37000 && maxVertexWeights == 0

            bone.transform.write(buf)

        _write_u32(buf, this.boneLimit)
        _write_u32(buf, len(this.boneGroups))
        _write_u32(buf, len(this.boneRemaps))

        if len(this.boneGroups) > 0:
            for bRmpIdx in this.boneRemapIndices:
                _write_u8(buf, bRmpIdx)

            for bgrp in this.boneGroups:
                _write_u8(buf, bgrp.firstBone)
                _write_u8(buf, bgrp.numBones)

            for brmp in this.boneRemaps:
                _write_u8(buf, brmp.boneIndex)
                _write_u8(buf, brmp.indices)

        rw_header = RWHeader(
            type=RWSectionType.rwID_SKINPLUGIN.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())

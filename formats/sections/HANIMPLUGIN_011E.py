import io
from dataclasses import dataclass, field

from ..lib.parser import Parser
from ..rwConstants import RWSectionType
from ..rw_basics import RW_Section, RWHeader, expect_chunk_type_or_raise

@dataclass
class RpBoneFlags:
    popParentMatrix: bool = False  # 0x00000001 POPPARENTMATRIX  - this flag must be set for bones which don't have child bones
    pushParentMatrix: bool = False  # 0x00000002 PUSHPARENTMATRIX - this flag must be set for all bones, except those which are the latest in a particular hierarchical level

    @staticmethod
    def decode(value: int) -> "RpBoneFlags":
        f = RpBoneFlags()
        f.popParentMatrix = bool(value & 0x00000001)
        f.pushParentMatrix = bool(value & 0x00000002)
        return f

    def encode(self) -> int:
        v = 0
        if self.popParentMatrix:
            v |= 0x00000001
        if self.pushParentMatrix:
            v |= 0x00000002
        return v
    
    def print(self):
        print("RpBoneFlags:")
        print(f"  popParentMatrix: {self.popParentMatrix}")
        print(f"  pushParentMatrix: {self.pushParentMatrix}")

@dataclass
class RpHAnimHierarchyFlags:
    subHierarchy: bool = False  # 0x1 - hierarchy inherits from another hierarchy
    noMatrices: bool = False  # 0x2 - hierarchy doesn't use local matrices for bones
    updateModellingMatrices: bool = False  # 0x1000 - update local matrices for bones
    updateLTMS: bool = False  # 0x2000 - recalculate global matrices for bones
    localSpaceMatrices: bool = False  # 0x4000 - hierarchy computes matrices in the local space
    
    @staticmethod
    def decode(value: int) -> "RpHAnimHierarchyFlags":
        f = RpHAnimHierarchyFlags()
        f.subHierarchy = bool(value & 0x1)
        f.noMatrices = bool(value & 0x2)
        f.updateModellingMatrices = bool(value & 0x1000)
        f.updateLTMS = bool(value & 0x2000)
        f.localSpaceMatrices = bool(value & 0x3000)
        return f

    def encode(self) -> int:
        v = 0
        if self.subHierarchy:
            v |= 0x1
        if self.noMatrices:
            v |= 0x2
        if self.updateModellingMatrices:
            v |= 0x1000
        if self.updateLTMS:
            v |= 0x2000
        if self.localSpaceMatrices:
            v |= 0x3000
        return v
    
    def print(self):
        print("RpHAnimFlags:")
        print(f"  subHierarchy: {self.subHierarchy}")
        print(f"  noMatrices: {self.noMatrices}")
        print(f"  updateModellingMatrices: {self.updateModellingMatrices}")
        print(f"  updateLTMS: {self.updateLTMS}")
        print(f"  localSpaceMatrices: {self.localSpaceMatrices}")


@dataclass
class RW_HAnimPlugin_Bone(RW_Section):
    nodeId: int = 0 # u32 - user Id for this bone
    nodeIndex: int = 0 # u32 - bone index in this array
    flags: RpBoneFlags = field(default_factory=RpBoneFlags) # u32 - bone flags

@dataclass
class RW_HAnimPlugin(RW_Section):
    """https://gtamods.com/wiki/HAnim_PLG_(RW_Section)"""
    header: RWHeader = field(default_factory=RWHeader)
    
    hAnimVersion: int = 0 # u32 - animation's version format (in all GTAs - 1.0 (0x100))
    nodeId: int = 0 # u32 - user Id for this bone
    numNodes: int = 0 # u32 - number of bones in hierarchy (if this bone is a root bone; for all other bones this parameter is set to 0)

    # if numNodes > 0:
    flags: RpHAnimHierarchyFlags = field(default_factory=RpHAnimHierarchyFlags) # u32 - flags (in all GTAs - 0)
    keyFrameSize: int = 0 # u32 - size of data (in bytes) needed for one animaton frame (in GTA this parameter is equal to 36)

    bones: list[RW_HAnimPlugin_Bone] = field(default_factory=list) # RW_HAnimPlugin_Bone[numNodes] - array of bones (if this bone is a root bone; for all other bones this parameter is not present)
    # endif

    @staticmethod
    def read(parser: Parser, parent_type=None) -> "RW_HAnimPlugin":
        hanim = RW_HAnimPlugin()
        hanim.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            hanim.header,
            RWSectionType.rwID_HANIMPLUGIN.value,
            "RW_HAnimPlugin chunk type",
        )

        hanim.hAnimVersion = parser.readUint32()
        hanim.nodeId = parser.readUint32()
        hanim.numNodes = parser.readUint32()

        if hanim.numNodes > 0:
            hanim.flags = RpHAnimHierarchyFlags.decode(parser.readUint32())
            hanim.keyFrameSize = parser.readUint32()

            for _ in range(hanim.numNodes):
                bone = RW_HAnimPlugin_Bone()
                bone.nodeId = parser.readUint32()
                bone.nodeIndex = parser.readUint32()
                bone.flags = RpBoneFlags.decode(parser.readUint32())
                hanim.bones.append(bone)


        return hanim

    def write(this, f, stamp):
        buf = io.BytesIO()

        # Writing here

        rw_header = RWHeader(
            type=RWSectionType.rwID_HANIMPLUGIN.value,  # TODO: REPLACE!
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())
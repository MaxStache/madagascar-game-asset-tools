from dataclasses import dataclass


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

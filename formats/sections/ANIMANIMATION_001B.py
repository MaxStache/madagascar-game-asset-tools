from enum import IntEnum
import io
from dataclasses import dataclass, field
from typing import Union

from formats.lib.writer import _write_f32, _write_f16, _write_u32
from formats.lib.parser import Parser
from formats.lib.rwConstants import RWSectionType
from formats.lib.rw_basics import (
    RW_Section,
    RWHeader,
    Vector3,
    expect_chunk_type_or_raise,
)

KEYFRAME_PARENT_NONE_OFFSET = 0xFF30C9D8


class RW_AnimAnimation_KeyframeType(IntEnum):
    # RW common
    UNCOMPRESSED = 0x1
    COMPRESSED = 0x2
    # Other studios may have additional keyframe types


@dataclass
class RW_AnimAnimation_CompressedKeyframe:
    time: float = field(default=0.0)  # in seconds

    rotation: tuple[float, float, float, float] = field(
        default_factory=lambda: (0.0, 0.0, 0.0, 1.0)
    )  # Quantized quaternion components

    position: tuple[float, float, float] = field(
        default_factory=lambda: (0.0, 0.0, 0.0)
    )  # Quantized position components

    prev_frame_off: int = field(default=0)  # Offset to the previous keyframe

    bone_id: int = field(default=-1)  # Bone ID

    def read(parser: Parser) -> "RW_AnimAnimation_CompressedKeyframe":
        kf = RW_AnimAnimation_CompressedKeyframe()

        kf.time = parser.readFloat()  # in seconds

        # print(kf.time)

        kf.rotation = (  # Quantized quaternion components.Quantized quaternion components.
            parser.readFloat16(),  # x
            parser.readFloat16(),  # y
            parser.readFloat16(),  # z
            parser.readFloat16(),  # w
        )

        kf.position = (  # Quantized position components.
            parser.readFloat16(),  # x
            parser.readFloat16(),  # y
            parser.readFloat16(),  # z
        )

        kf.prev_frame_off = parser.readUint32()  # Offset to the previous keyframe

        return kf

    def write(this, f, idx, prev_keyframe_offsets):
        _write_f32(f, this.time)

        _write_f16(f, this.rotation[0])
        _write_f16(f, this.rotation[1])
        _write_f16(f, this.rotation[2])
        _write_f16(f, this.rotation[3])

        _write_f16(f, this.position[0])
        _write_f16(f, this.position[1])
        _write_f16(f, this.position[2])

        if this.bone_id in prev_keyframe_offsets:
            _write_u32(f, KEYFRAME_PARENT_NONE_OFFSET)
        else:
            _write_u32(f, prev_keyframe_offsets[this.bone_id])
        prev_keyframe_offsets[this.bone_id] = idx * 22


@dataclass
class RW_AnimAnimation(RW_Section):
    header: RWHeader = field(default_factory=RWHeader)

    version: int = field(default=0x100)  # 0x100 = version 1.0 etc.
    keyframe_type: RW_AnimAnimation_KeyframeType = field(
        default=RW_AnimAnimation_KeyframeType.UNCOMPRESSED
    )

    keyframe_count: int = field(default=0)

    flags: int = field(default=0)  # unknown flags

    duration: float = field(default=0.0)  # duration in seconds

    keyframes: Union[list[RW_AnimAnimation_CompressedKeyframe]] = field(
        default_factory=list
    )

    pos_offset: Vector3 = field(default_factory=Vector3)
    pos_scale: Vector3 = field(default_factory=Vector3)

    @staticmethod
    def read(parser: Parser, parent=None) -> "RW_AnimAnimation":
        anim = RW_AnimAnimation()
        anim.header = RWHeader.read(parser)
        expect_chunk_type_or_raise(
            anim.header,
            RWSectionType.rwID_ANIMANIMATION.value,
            "RW_AnimAnimation chunk type",
        )

        anim.version = parser.readUint32()
        anim.keyframe_type = RW_AnimAnimation_KeyframeType(parser.readUint32())

        anim.keyframe_count = parser.readUint32()
        anim.flags = parser.readUint32()

        anim.duration = parser.readFloat()

        if anim.keyframe_type == RW_AnimAnimation_KeyframeType.UNCOMPRESSED:
            raise NotImplementedError("Uncompressed keyframes are not implemented yet.")
        elif anim.keyframe_type == RW_AnimAnimation_KeyframeType.COMPRESSED:
            anim._read_keyframes_compressed(parser)
            pass
        else:
            raise ValueError(f"Unhandled keyframe type: {anim.keyframe_type}")

        return anim

    def _read_keyframes_compressed(self, parser: Parser):
        KEYFRAME_SIZE = 22  # Each compressed keyframe is 22 bytes
        keyframe_offsets = []
        bone_id = -1

        for idx in range(self.keyframe_count):
            keyframe_offsets.append(idx * 24) # using 24 bytes for a keyframe, whyever
            keyframe_parser = Parser(parser.readBytes(KEYFRAME_SIZE))

            keyframe = RW_AnimAnimation_CompressedKeyframe.read(
                keyframe_parser
            )

            if keyframe.prev_frame_off & 0x3F000000:
                bone_id = bone_id + 1 if keyframe.time == 0.0 else 0
            else:
                prev_kf_id = keyframe_offsets.index(keyframe.prev_frame_off)
                bone_id = self.keyframes[prev_kf_id].bone_id

            keyframe.bone_id = bone_id

            self.keyframes.append(keyframe)

        self.pos_offset = Vector3.read(parser)
        self.pos_scale = Vector3.read(parser)

    def write(this, f, stamp, parent=None):
        buf = io.BytesIO()

        prev_keyframe_offsets = {}
        for kf_idx, kf in enumerate(this.keyframes):
            kf.write(buf, kf_idx, prev_keyframe_offsets)

        rw_header = RWHeader(
            type=RWSectionType.rwID_ANIMANIMATION.value,
            size=len(buf.getvalue()),
            library_id_stamp=stamp,
        )
        f.write(rw_header.pack())
        f.write(buf.getvalue())

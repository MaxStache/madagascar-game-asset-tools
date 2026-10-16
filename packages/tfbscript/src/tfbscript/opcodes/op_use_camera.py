from dataclasses import dataclass, field
from typing import BinaryIO, override

from tfbscript.ansi import func_call
from tfbscript.binary import write_f32, write_u8
from tfbscript.opcodes.base import Opcode, opcode
from tfbscript.opcodes.enums import CamTransitionInMode, CamTransitionOutMode
from tfbscript.payload import PayloadReader
from tfbscript.reference import Reference


@opcode("use camera")
@dataclass
class OpUseCamera(Opcode):
    camera_ref: Reference = field(default_factory=Reference)

    trans_in_mode: CamTransitionInMode = field(default=CamTransitionInMode.fade_in)
    trans_in_duration: float = field(default=0.0)

    trans_out_mode: CamTransitionOutMode = field(
        default=CamTransitionOutMode.no_transition
    )
    trans_out_duration: float | None = field(default=None)

    @classmethod
    @override
    def parse_payload(cls, reader: PayloadReader) -> "OpUseCamera":
        camera_ref = reader.readRef()

        trans_in_mode = CamTransitionInMode(reader.read_u8())
        trans_in_duration = reader.read_f32()

        trans_out_mode = CamTransitionOutMode(reader.read_u8())

        trans_out_duration = None
        if trans_out_mode != CamTransitionOutMode.no_transition:
            trans_out_duration = reader.read_f32()

        return cls(
            camera_ref=camera_ref,
            trans_in_mode=trans_in_mode,
            trans_in_duration=trans_in_duration,
            trans_out_mode=trans_out_mode,
            trans_out_duration=trans_out_duration,
        )

    @override
    def write_payload(self, f: BinaryIO) -> None:
        self.camera_ref.write(f)
        write_u8(f, self.trans_in_mode)
        write_f32(f, self.trans_in_duration)

        write_u8(f, self.trans_out_mode)
        if self.trans_out_mode != CamTransitionOutMode.no_transition:
            assert self.trans_out_duration is not None # Should never assert
            write_f32(f, self.trans_out_duration)

    @override
    def source_line(self, inline: bool = False) -> str:
        return func_call(
            "useCamera",
            str(self.camera_ref),
            f"trans_in: {self.trans_in_mode} for {self.trans_in_duration}sec",
            f"trans_out: {self.trans_out_mode} for {self.trans_out_duration}sec"
            if self.trans_out_mode != CamTransitionOutMode.no_transition
            else f"trans_out: {self.trans_out_mode}",
        )


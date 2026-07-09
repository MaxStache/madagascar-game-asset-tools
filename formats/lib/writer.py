import struct

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
import struct
import uuid
from os import SEEK_SET, SEEK_CUR, SEEK_END 
from enum import IntEnum
import numpy as np
import quaternion
import tkinter as tk
from tkinter import ttk
import sys

class Parser:
    def __init__(self, data: bytes, endian: str = "little"):
        if not isinstance(data, (bytes, bytearray)):
            raise TypeError("data must be bytes or bytearray")

        self.data = data
        self.offset = 0

        if endian == "little":
            self.endian = "<"
        elif endian == "big":
            self.endian = ">"
        else:
            raise ValueError("endian must be 'little' or 'big'")

    # -------------------------
    # Core helpers
    # -------------------------

    def _read(self, fmt: str):
        size = struct.calcsize(fmt)
        if self.offset + size > len(self.data):
            raise EOFError("Attempt to read past end of buffer")

        value = struct.unpack_from(fmt, self.data, self.offset)
        self.offset += size
        return value[0] if len(value) == 1 else value

    def read(self, size: int) -> bytes:
        """
        Equivalent to RwStreamRead(stream, buffer, size)
        Returns bytes read (may be shorter only at EOF).
        """
        if self.offset + size > len(self.data):
            return b""

        chunk = self.data[self.offset : self.offset + size]
        self.offset += size
        return chunk

    def seek(self, offset: int):
        if offset < 0 or offset > len(self.data):
            raise ValueError("Invalid seek offset")
        self.offset = offset

    def tell(self) -> int:
        return self.offset

    def skip(self, size: int):
        self.seek(self.offset + size)

    def canRead(self, size: int) -> bool:
        return self.offset + size <= len(self.data)

    # -------------------------
    # Integer reads
    # -------------------------

    def readUint8(self):
        return self._read(self.endian + "B")

    def readInt8(self):
        return self._read(self.endian + "b")

    def readUint16(self):
        return self._read(self.endian + "H")

    def readInt16(self):
        return self._read(self.endian + "h")

    def readUint32(self):
        return self._read(self.endian + "I")

    def readInt32(self):
        return self._read(self.endian + "i")

    def readUint64(self):
        return self._read(self.endian + "Q")

    def readInt64(self):
        return self._read(self.endian + "q")

    # -------------------------
    # Floating point
    # -------------------------

    def readFloat(self):
        return self._read(self.endian + "f")

    def readFloat16(self):
        return self._read(self.endian + "e")

    def readDouble(self):
        return self._read(self.endian + "d")

    # -------------------------
    # Raw / strings
    # -------------------------

    def readBytes(self, size: int) -> bytes:
        if self.offset + size > len(self.data):
            raise EOFError("Attempt to read past end of buffer")

        b = self.data[self.offset : self.offset + size]
        self.offset += size
        return b

    def readCString(self, encoding="utf-8") -> str:
        start = self.offset
        while self.offset < len(self.data) and self.data[self.offset] != 0:
            self.offset += 1

        if self.offset >= len(self.data):
            raise EOFError("Unterminated C string")

        s = self.data[start : self.offset].decode(encoding)
        self.offset += 1  # skip null byte
        return s

    def readPaddedCString(self, alignment=4, encoding="utf-8") -> str:
        start = self.offset
        s = self.readCString(encoding)
        byte_length = self.offset - start  # actual bytes consumed including null
        remainder = byte_length % alignment
        if remainder:
            self.offset += alignment - remainder
        return s

    def readGUID(self):
        guid_bytes = self.readBytes(16)
        return uuid.UUID(bytes=guid_bytes)

    def readBool(self):
        return self.readUint32() != 0


ANM_CHUNK_ID = 0x1B


class KeyframeType(IntEnum):
    UNCOMPRESSED = 0x1  # RW common
    COMPRESSED = 0x2  # RW common


def read_keyframes_compressed(buf: Parser, keyframes_num, chunk_info):
    keyframes = []
    frame_offs = []
    bone_id = -1

    for kf_id in range(keyframes_num):
        frame_offs.append(kf_id * 24)
        time = buf.readFloat()
        rot = (
            buf.readFloat16(),
            buf.readFloat16(),
            buf.readFloat16(),
            buf.readFloat16(),
        )
        rot = np.quaternion(rot[3], rot[0], rot[1], rot[2])
        pos = (buf.readFloat16(), buf.readFloat16(), buf.readFloat16())
        prev_frame_off = buf.readUint32()

        if prev_frame_off & 0x3F000000:
            bone_id = bone_id + 1 if time == 0.0 else 0
        else:
            prev_kf_id = frame_offs.index(prev_frame_off)
            bone_id = keyframes[prev_kf_id].get("bone_id")

        keyframes.append(
            {
                "time": time,
                "bone_id": bone_id,
                "rot": rot,
                "pos": pos,
            }
        )

    pos_offset = (buf.readFloat(), buf.readFloat(), buf.readFloat())
    pos_scale = (buf.readFloat(), buf.readFloat(), buf.readFloat())

    for kf in keyframes:
        x = kf["pos"][0] * pos_scale[0] + pos_offset[0]
        y = kf["pos"][1] * pos_scale[1] + pos_offset[1]
        z = kf["pos"][2] * pos_scale[2] + pos_offset[2]

        kf["pos"] = (x, y, z)

    return keyframes


def read_anm_animation(parser: Parser, chunk_info):
    buf = Parser(parser.readBytes(chunk_info["size"]))

    version = buf.readUint32()
    keyframe_type = buf.readUint32()
    keyframes_num = buf.readUint32()
    flags = buf.readUint32()

    duration = buf.readFloat()

    keyframes = []

    render_func = {
        # RW common
        #KeyframeType.UNCOMPRESSED: read_keyframes_uncompressed,
        KeyframeType.COMPRESSED: read_keyframes_compressed,
    }.get(keyframe_type)

    if render_func:
        keyframes = render_func(buf, keyframes_num, chunk_info)
    else:
        print(f"Unknown keyframe type: {keyframe_type}")
        sys.exit()
        
    return {
        "version": version,
        "keyframe_type": keyframe_type,
        "flags": flags,
        "duration": duration,
        "keyframes": keyframes,
    }


def read_anm_chunk(parser: Parser, chunk_info):
    buf = Parser(parser.readBytes(chunk_info["size"]))
    if chunk_info["id"] == ANM_CHUNK_ID:
        return read_anm_animation(buf, chunk_info)

# 204_marty_face_QUW.subanm.anm
# 200_marty_face_CONS.subanm.anm
# 327_alex_run.anm
with open("./ENG_KoNY_LPA/200_marty_face_CONS.subanm.anm", "rb") as f:
    f.seek(0, SEEK_END)
    size = f.tell()
    f.seek(0, SEEK_SET)

    chunks = []

    buf = Parser(f.read())

    while buf.canRead(4):
        chunk_info = {
            "id": buf.readUint32(),
            "size": buf.readUint32(),
            "version": buf.readUint32(),
        }
        anm_chunk = read_anm_chunk(buf, chunk_info)
        if anm_chunk:
            chunks.append(anm_chunk)

    print(f"Parsed {len(chunks)} ANM chunks")
    chunk_print = chunks[0].copy()
    chunk_print["keyframes"] = "HIDDEN"
    print(chunk_print)

    # Create main window
    root = tk.Tk()
    root.title("Tkinter Table Example")
    root.geometry("500x300")

    # Create table (Treeview)
    columns = tuple(chunks[0]["keyframes"][0].keys())
    table = ttk.Treeview(root, columns=columns, show="headings")

    for col in columns:
        table.heading(col, text=col)
        table.column(col, anchor="center", width=120)

    # Insert sample data
    data = [
        tuple(d.values()) for d in chunks[0]["keyframes"]
    ]

    for row in data:
        table.insert("", tk.END, values=row)

    # Add table to window
    table.pack(expand=True, fill="both", padx=10, pady=10)

    # Run the app
    root.mainloop()
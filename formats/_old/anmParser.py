from os import SEEK_SET, SEEK_END 
from enum import IntEnum
import numpy as np
import tkinter as tk
from tkinter import ttk
import sys

from formats.lib.parser import Parser

ANM_CHUNK_ID = 0x1B


class KeyframeType(IntEnum):
    UNCOMPRESSED = 0x1  # RW common
    COMPRESSED = 0x2  # RW common


def read_keyframes_compressed(buf: Parser, keyframes_num, chunk_info):
    keyframes = []
    keyframe_offsets = []
    bone_id = -1

    for kf_id in range(keyframes_num):
        keyframe_offsets.append(kf_id * 24)
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
            prev_kf_id = keyframe_offsets.index(prev_frame_off)
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
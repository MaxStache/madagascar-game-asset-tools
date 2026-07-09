def bytes_pad4(data: bytes) -> bytes:
    padding = (4 - (len(data) % 4)) % 4
    return data + b"\x00" * padding
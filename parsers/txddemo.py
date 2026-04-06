from tqdm import tqdm
import rwtxd
from enum import Enum


class FilterMode(Enum):
    FILTER_NONE = 0x00
    FILTER_NEAREST = 0x01
    FILTER_LINEAR = 0x02
    FILTER_MIP_NEAREST = 0x03
    FILTER_MIP_LINEAR = 0x04
    FILTER_LINEAR_MIP_NEAREST = 0x05
    FILTER_LINEAR_MIP_LINEAR = 0x06


class AddressingMode(Enum):
    WRAP_NONE = 0x00
    WRAP_WRAP = 0x01
    WRAP_MIRROR = 0x02
    WRAP_CLAMP = 0x03


# Round-trip
txd = rwtxd.load("../ENG_KoNY_LPA/2_TD_LEVEL FOLDER.txd")

# print(next(t for t in txd.textures if t.name == "head"))
print("EXPORTING...")

# for texture in tqdm(txd.textures, desc="Exporting textures"):
#    rwtxd.export_png(texture, f"temp/{texture.name}.png")
#    if texture.name == "melman_tissue2":
#        print("\n")
#        print(texture._xbox_texelDataSize)

txd_out = rwtxd.TextureDictionary()

print("IMPORTING INTO NEW...")


def assemble_filter_mode(
    filterMode: FilterMode, uAddressing: AddressingMode, vAddressing: AddressingMode
) -> int:
    # validate ranges
    if not (0 <= filterMode < 2**8):
        raise ValueError("filterMode must fit in 8 bits (0-255)")
    if not (0 <= uAddressing < 2**4):
        raise ValueError("uAddressing must fit in 4 bits (0-15)")
    if not (0 <= vAddressing < 2**4):
        raise ValueError("vAddressing must fit in 4 bits (0-15)")

    value = (
        (filterMode) | (uAddressing << 8) | (vAddressing << 12)
        # pad is 0, so no shift needed
    )

    return value
def disassemble_filter_mode(value: int) -> tuple[int, int, int]:
    # validate 16-bit range if desired
    if not (0 <= value < 2**16):
        raise ValueError("value must fit in 16 bits (0-65535)")

    filterMode = value & 0xFF          # 8 bits
    uAddressing = (value >> 8) & 0xF   # next 4 bits
    vAddressing = (value >> 12) & 0xF  # next 4 bits

    return filterMode, uAddressing, vAddressing

for texture in tqdm(txd.textures, desc="Importing textures"):
    imported_texture = rwtxd.import_png(f"temp/{texture.name}.png", name=texture.name)
    text_filter_mode = disassemble_filter_mode(texture.filter_mode)
    imported_texture.filter_mode = assemble_filter_mode(
        FilterMode(text_filter_mode[0]).value,
        AddressingMode(text_filter_mode[1]).value,
        AddressingMode(text_filter_mode[2]).value,
    )
    txd_out.textures.append(imported_texture)

rwtxd.save(txd_out, "../ENG_KoNY_LPA_MODIFIED/2_TD_LEVEL FOLDER.txd")

from tqdm import tqdm
import rwtxd
import sys

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

disa = rwtxd.disassemble_filter_mode(0x3302)
print(rwtxd.FilterMode(disa[0]).name)
print(rwtxd.AddressingMode(disa[1]).name)
print(rwtxd.AddressingMode(disa[2]).name)

sys.exit(1)

for original_texture in tqdm(txd.textures, desc="Importing textures"):
    imported_texture = rwtxd.import_png(f"temp/{original_texture.name}.png", name=original_texture.name)
    
    # Preseve original filter mode
    text_filter_mode = rwtxd.disassemble_filter_mode(original_texture.filter_mode)
    imported_texture.filter_mode = rwtxd.assemble_filter_mode(
        rwtxd.FilterMode(text_filter_mode[0]).value,
        rwtxd.AddressingMode(text_filter_mode[1]).value,
        rwtxd.AddressingMode(text_filter_mode[2]).value,
    )
    # Could also be done like this:
    # imported_texture.filter_mode = original_texture.filter_mode
    
    txd_out.textures.append(imported_texture)

rwtxd.save(txd_out, "../ENG_KoNY_LPA_MODIFIED/2_TD_LEVEL FOLDER.txd")

import rwaRWS as rwaRWS


rws = rwaRWS.load_2057("Levels/banquet/8_WavDictXBOX.rws")
rws.save("myrws.rws")

sub = rws.getSubstream(0)
sub.export_wav(f"{sub.header_info.stream_name}.wav")



# print(next(t for t in txd.textures if t.name == "head"))
#print("EXPORTING...")

# for texture in tqdm(txd.textures, desc="Exporting textures"):
#    rwtxd.export_png(texture, f"temp/{texture.name}.png")
#    if texture.name == "melman_tissue2":
#        print("\n")
#        print(texture._xbox_texelDataSize)

#txd_out = rwaRWS.TextureDictionary()

#print("IMPORTING INTO NEW...")

#for texture in tqdm(txd.textures, desc="Importing textures"):
#    imported_texture = rwaRWS.import_png(f"temp/{texture.name}.png", name=texture.name)
#    text_filter_mode = rwaRWS.disassemble_filter_mode(texture.filter_mode)
#    imported_texture.filter_mode = rwaRWS.assemble_filter_mode(
#        rwaRWS.FilterMode(text_filter_mode[0]).value,
#        rwaRWS.AddressingMode(text_filter_mode[1]).value,
#        rwaRWS.AddressingMode(text_filter_mode[2]).value,
#    )
#    txd_out.textures.append(imported_texture)

#rwaRWS.save(txd_out, "../ENG_KoNY_LPA_MODIFIED/2_TD_LEVEL FOLDER.txd")

import rwwBSP as rwwBSP


skybsp = rwwBSP.load_bsp("Levels/KingOfNY-unchanged/5_KingofNY9_Combined188_Sky.bsp")

def dump(*sections):
    """Pretty struct dump. Each section: (title, [(label, value), ...])."""
    w = max(len(lbl) for _, rows in sections for lbl, _ in rows)
    for title, rows in sections:
        print(f"\n  {title}")
        print("  " + "─" * (w + 18))
        for lbl, val in rows:
            print(f"  {lbl:<{w}}  {val}")


ws, wc = skybsp.world_struct, skybsp.world_chunk

dump(
    ("Sectors", [
        ("numAtomicSectors", ws.data.numAtomicSectors),
        ("numPlaneSectors",  ws.data.numPlaneSectors),
    ]),
    ("Mesh", [
        ("numVertices",  ws.data.numVertices),
        ("numTriangles", ws.data.numTriangles),
    ]),
    ("Collision & flags", [
        ("colSectorSize",     ws.data.colSectorSize),
        ("inverseOrigin",     ws.inverseOrigin),
        ("rootIsWorldSector", ws.rootIsWorldSector),
        ("worldFlags",        f"0x{ws.data.worldFlags:08X}"),
    ]),
    ("world_chunk", [
        ("collSectorPresent", wc.data.collSectorPresent),
        ("unused",            wc.data.unused),
    ]),
)

ml = skybsp.material_list
print(f"\n  Materials  ({ml.material_count} total)")
print("  " + "─" * 60)
for i, mat in enumerate(ml.materials):
    idx = ml.materialIndices[i]
    c = mat.color
    tex_name = mat.texture.diffuseTextureName if mat.isTextured and mat.texture else "(none)"
    alpha_name = mat.texture.alphaTextureName if mat.isTextured and mat.texture else ""
    print(f"  [{i:>3}]  idx={idx:>3}  flags=0x{mat.flags:04X}"
          f"  color=({c.r},{c.g},{c.b},{c.a})"
          f"  amb={mat.ambient:.3f}  spec={mat.specular:.3f}  diff={mat.diffuse:.3f}"
          f"  tex={tex_name!r}"
          + (f"  alpha={alpha_name!r}" if alpha_name else ""))

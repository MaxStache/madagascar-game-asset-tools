import rwwBSP as rwwBSP


BSP_FILENAME = "13_KingofNY9_Combined188_NoShadow.bsp"

bsp = rwwBSP.load_bsp(f"Levels/KingOfNY/{BSP_FILENAME}")

print(bsp.world_struct.data.boxMax.x * 0.05)
print(bsp.world_struct.data.boxMax.y * 0.05)
print(bsp.world_struct.data.boxMax.z * 0.05)
print()
print(bsp.world_struct.data.boxMin.x * 0.05)
print(bsp.world_struct.data.boxMin.y * 0.05)
print(bsp.world_struct.data.boxMin.z * 0.05)
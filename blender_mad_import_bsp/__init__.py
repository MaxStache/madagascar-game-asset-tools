bl_info = {
    "name": "Madagascar RW BSP Importer",
    "author": "Maxttc",
    "version": (0, 4, 0),
    "blender": (3, 0, 0),
    "location": "File > Import/Export > BSP (.bsp)",
    "description": "Imports and exports Madagascar RenderWare BSP files",
    "category": "Import-Export",
}

if "bpy" in locals():
    import importlib

    importlib.reload(gui)  # noqa: F821
else:
    from . import gui

import bpy  # noqa: E402
from bpy.utils import register_class, unregister_class  # noqa: E402

# PropertyGroups must be registered before Panels and before the pointer
# properties are assigned — innermost first (leaves of the dependency tree).
_property_groups = (
    gui.BSPWorldExtProps,
    gui.BSPWorldProps,
    gui.BSPMatExtProps,
    gui.BSPTexExtProps,
    gui.BSPTexProps,
    gui.BSPMatProps,
)

_classes = (
    gui.IMPORT_OT_bsp,
    gui.EXPORT_OT_bsp,
    gui.OBJECT_PT_bsp_properties,
    gui.MATERIAL_PT_bsp_properties,
)


def register():
    for cls in _property_groups:
        register_class(cls)

    bpy.types.Object.bsp = bpy.props.PointerProperty(type=gui.BSPWorldProps)
    bpy.types.Material.bsp = bpy.props.PointerProperty(type=gui.BSPMatProps)

    for cls in _classes:
        register_class(cls)

    bpy.types.TOPBAR_MT_file_import.append(gui.import_bsp_func)
    bpy.types.TOPBAR_MT_file_export.append(gui.export_bsp_func)


def unregister():
    bpy.types.TOPBAR_MT_file_import.remove(gui.import_bsp_func)
    bpy.types.TOPBAR_MT_file_export.remove(gui.export_bsp_func)

    for cls in reversed(_classes):
        unregister_class(cls)

    del bpy.types.Object.bsp
    del bpy.types.Material.bsp

    for cls in reversed(_property_groups):
        unregister_class(cls)

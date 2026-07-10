import bpy
from bpy.types import PropertyGroup, Panel
from bpy.props import (
    BoolProperty, IntProperty, FloatProperty,
    FloatVectorProperty, StringProperty, PointerProperty,
)
from .. import bspLib


class BSPWorldExtProps(PropertyGroup):
    """TFB world extension chunk 0x800000B0 payload."""
    magic: IntProperty(
        name="Plugin Magic",
        description="First payload word of the 0x800000B0 chunk (usually 0x0F0F0003)",
        default=0x0F0F0003, min=-(2**31), max=2**31 - 1,
    )  # type: ignore
    d1: IntProperty(name="D1", default=0, min=-(2**31), max=2**31 - 1)  # type: ignore
    d2: IntProperty(name="D2", default=0, min=-(2**31), max=2**31 - 1)  # type: ignore
    d3: IntProperty(name="D3", default=0, min=-(2**31), max=2**31 - 1)  # type: ignore


class BSPWorldProps(PropertyGroup):
    has_data: BoolProperty(name="Has BSP World Data", default=False)  # type: ignore
    world_flags: IntProperty(
        name="World Flags",
        description="rpWORLD flags bitfield written to the WorldStruct",
        default=bspLib.DEFAULT_WORLD_FLAGS, min=-(2**31), max=2**31 - 1,
    )  # type: ignore
    stamp: IntProperty(
        name="Version Stamp",
        description="RenderWare version stamp written into every section header",
        default=bspLib.DEFAULT_VERSION_STAMP, min=-(2**31), max=2**31 - 1,
    )  # type: ignore
    import_scale: FloatProperty(
        name="Import Scale",
        description="Scale factor used when importing; invert to recover original RW units on export",
        default=0.0625, min=0.000001, max=1000.0,
    )  # type: ignore
    inv_origin: FloatVectorProperty(
        name="Inverse Origin",
        description="World inverse-origin stored in WorldStruct (usually 0,0,0)",
        size=3, default=(-0.0, -0.0, -0.0),
    )  # type: ignore
    root_is_world_sector: IntProperty(
        name="Root Is World Sector",
        description="WorldStruct flag: 1 when the root node is a single AtomicSector",
        default=0, min=0, max=1,
    )  # type: ignore
    ext: PointerProperty(type=BSPWorldExtProps)  # type: ignore


class BSPMatExtProps(PropertyGroup):
    """TFB material extension chunk 0x800000F6 payload (fully parsed)."""
    magic: IntProperty(
        name="Plugin Magic",
        description="First payload word (0x0F0F000D identifies this as a TFB material plugin)",
        default=0x0F0F000D, min=-(2**31), max=2**31 - 1,
    )  # type: ignore
    flags: IntProperty(
        name="Flags",
        description="Plugin flags word (0x201 in all shipped files)",
        default=0x201, min=0, max=2**31 - 1,
    )  # type: ignore
    blend_state: IntProperty(
        name="Blend State",
        description="0 = opaque (game ignores all alpha), 3 = alpha-blended, 1 = additive",
        default=0, min=0, max=255,
    )  # type: ignore
    alpha_ref: IntProperty(
        name="Alpha Reference",
        description="Alpha-test reference value (2 in all shipped files)",
        default=2, min=0, max=255,
    )  # type: ignore
    blend_func: IntProperty(
        name="Blend Function",
        description="8 = opaque blend function, 5 = alpha-blended, 7 = additive",
        default=8, min=0, max=255,
    )  # type: ignore
    extra_hex: StringProperty(
        name="Trailing Bytes (hex)",
        description="Remaining payload bytes after the 5 known fields (13 zero bytes in shipped files)",
        default="00" * 13,
    )  # type: ignore


class BSPTexExtProps(PropertyGroup):
    """Texture extension: Sky Mipmap Val (0x0110) + TFB texture plugin (0x800000DD)."""
    sky_mip_val: IntProperty(
        name="Sky Mip Val",
        description="Payload of the 0x0110 Sky Mipmap Val chunk (0x0F80 = 3968 in shipped files)",
        default=0x0F80, min=0, max=2**31 - 1,
    )  # type: ignore
    tfb_magic: IntProperty(
        name="TFB Plugin Magic",
        description="First word of the 0x800000DD payload (0x0F0F0004 in shipped files)",
        default=0x0F0F0004, min=-(2**31), max=2**31 - 1,
    )  # type: ignore
    tfb_d1: IntProperty(name="TFB D1", default=0, min=-(2**31), max=2**31 - 1)  # type: ignore
    tfb_d2: IntProperty(name="TFB D2", default=0, min=-(2**31), max=2**31 - 1)  # type: ignore


class BSPTexProps(PropertyGroup):
    filter_mode: IntProperty(
        name="Filter Mode",
        description="RW texture filter mode byte (2 = bilinear in shipped files)",
        default=2, min=0, max=255,
    )  # type: ignore
    address_modes: IntProperty(
        name="Address Modes",
        description="Packed U/V address mode byte (17 = 0x11 = wrap/wrap in shipped files)",
        default=17, min=0, max=255,
    )  # type: ignore
    use_mip_levels: IntProperty(
        name="Use Mip Levels",
        description="Mip-map usage flag stored as uint16 (1 = on in shipped files)",
        default=1, min=0, max=65535,
    )  # type: ignore
    ext: PointerProperty(type=BSPTexExtProps)  # type: ignore


class BSPMatProps(PropertyGroup):
    has_data: BoolProperty(name="Has BSP Material Data", default=False)  # type: ignore
    unused_flags: IntProperty(
        name="Unused Flags",
        description="MaterialStruct unusedFlags field (0 in all shipped files)",
        default=0, min=-(2**31), max=2**31 - 1,
    )  # type: ignore
    color: FloatVectorProperty(
        name="Color",
        description="RGBA material color (0-1 per channel) that modulates diffuse/vertex color",
        subtype='COLOR_GAMMA', size=4, default=(1.0, 1.0, 1.0, 1.0), min=0.0, max=1.0,
    )  # type: ignore
    unused_int2: IntProperty(
        name="Unused Int2",
        description="MaterialStruct second unused field (magic-like constant 0x32E6CF5C in shipped files)",
        default=bspLib.DEFAULT_MATERIAL_UNUSED_INT2, min=-(2**31), max=2**31 - 1,
    )  # type: ignore
    ambient: FloatProperty(
        name="Ambient", description="Material ambient lighting factor",
        default=1.0, min=0.0, max=2.0,
    )  # type: ignore
    specular: FloatProperty(
        name="Specular", description="Material specular lighting factor",
        default=0.0, min=0.0, max=2.0,
    )  # type: ignore
    diffuse: FloatProperty(
        name="Diffuse", description="Material diffuse lighting factor",
        default=1.0, min=0.0, max=2.0,
    )  # type: ignore
    ext: PointerProperty(type=BSPMatExtProps)  # type: ignore
    is_textured: BoolProperty(
        name="Is Textured",
        description="Whether this material references a texture",
        default=False,
    )  # type: ignore
    texture: PointerProperty(type=BSPTexProps)  # type: ignore


# ── Panels ──────────────────────────────────────────────────────────────────


class OBJECT_PT_bsp_properties(Panel):
    bl_label = "BSP World Properties"
    bl_idname = "OBJECT_PT_bsp_properties"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"

    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj and obj.type == 'MESH' and obj.bsp.has_data

    def draw(self, context):
        layout = self.layout
        bsp = context.object.bsp

        col = layout.column(align=True)
        col.prop(bsp, "import_scale")
        col.separator()
        col.prop(bsp, "world_flags")
        col.label(text=f"    0x{bsp.world_flags & 0xFFFFFFFF:08X}")
        col.prop(bsp, "stamp")
        col.label(text=f"    0x{bsp.stamp & 0xFFFFFFFF:08X}")
        col.separator()
        col.prop(bsp, "root_is_world_sector")
        col.prop(bsp, "inv_origin")

        box = layout.box()
        box.label(text="World Extension  (chunk 0x800000B0)")
        col2 = box.column(align=True)
        col2.prop(bsp.ext, "magic")
        col2.label(text=f"    0x{bsp.ext.magic & 0xFFFFFFFF:08X}")
        col2.prop(bsp.ext, "d1")
        col2.prop(bsp.ext, "d2")
        col2.prop(bsp.ext, "d3")


class MATERIAL_PT_bsp_properties(Panel):
    bl_label = "BSP Material Properties"
    bl_idname = "MATERIAL_PT_bsp_properties"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "material"

    @classmethod
    def poll(cls, context):
        return context.material and context.material.bsp.has_data

    def draw(self, context):
        layout = self.layout
        bsp = context.material.bsp

        layout.prop(bsp, "color")

        col = layout.column(align=True)
        col.prop(bsp, "ambient")
        col.prop(bsp, "specular")
        col.prop(bsp, "diffuse")

        box = layout.box()
        box.label(text="TFB Material Extension  (chunk 0x800000F6)")
        col2 = box.column(align=True)
        col2.prop(bsp.ext, "blend_state")
        col2.prop(bsp.ext, "blend_func")
        col2.prop(bsp.ext, "alpha_ref")
        col2.separator()
        col2.prop(bsp.ext, "flags")
        col2.label(text=f"    0x{bsp.ext.flags & 0xFFFF:04X}")
        col2.prop(bsp.ext, "magic")
        col2.label(text=f"    0x{bsp.ext.magic & 0xFFFFFFFF:08X}")
        col2.separator()
        col2.prop(bsp.ext, "extra_hex")

        if bsp.is_textured:
            box2 = layout.box()
            box2.label(text="Texture Sampling")
            col3 = box2.column(align=True)
            col3.prop(bsp.texture, "filter_mode")
            col3.prop(bsp.texture, "address_modes")
            col3.prop(bsp.texture, "use_mip_levels")

            box3 = box2.box()
            box3.label(text="Texture Extension  (0x0110 + 0x800000DD)")
            col4 = box3.column(align=True)
            col4.prop(bsp.texture.ext, "sky_mip_val")
            col4.label(text=f"    0x{bsp.texture.ext.sky_mip_val:04X}")
            col4.separator()
            col4.prop(bsp.texture.ext, "tfb_magic")
            col4.label(text=f"    0x{bsp.texture.ext.tfb_magic & 0xFFFFFFFF:08X}")
            col4.prop(bsp.texture.ext, "tfb_d1")
            col4.prop(bsp.texture.ext, "tfb_d2")

        box4 = layout.box()
        box4.label(text="Internal / Unused")
        col5 = box4.column(align=True)
        col5.prop(bsp, "unused_flags")
        col5.prop(bsp, "unused_int2")
        col5.label(text=f"    0x{bsp.unused_int2 & 0xFFFFFFFF:08X}")

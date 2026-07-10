from bpy.types import Operator
from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty, FloatProperty, BoolProperty, IntProperty

from .. import bspLib


def _material_to_bsp(bl_mat, stamp):
    """Build a bspLib material dict from a Blender material.

    Imported materials carry all original data in the bsp PropertyGroup and
    round-trip byte-identically (incl. parsed TFB extensions).
    Anything else gets defaults, marked transparent when the Blender material
    uses a blended surface.
    """
    if bl_mat is not None and bl_mat.bsp.has_data:
        bsp = bl_mat.bsp
        cf = bsp.color
        mat = {
            "unusedFlags": bsp.unused_flags,
            "color": {
                "r": min(255, max(0, round(cf[0] * 255))),
                "g": min(255, max(0, round(cf[1] * 255))),
                "b": min(255, max(0, round(cf[2] * 255))),
                "a": min(255, max(0, round(cf[3] * 255))),
            },
            "unusedInt2": bsp.unused_int2,
            "isTextured": 1 if bsp.is_textured else 0,
            "ambient": bsp.ambient,
            "specular": bsp.specular,
            "diffuse": bsp.diffuse,
        }
        # Rebuild TFB material extension from stored parsed fields
        mat["extensionData"] = bspLib.write_material_extension_from_parsed(
            {
                "magic": bsp.ext.magic,
                "flags": bsp.ext.flags,
                "blend_state": bsp.ext.blend_state,
                "alpha_ref": bsp.ext.alpha_ref,
                "blend_func": bsp.ext.blend_func,
                "extra_hex": bsp.ext.extra_hex,
            },
            stamp,
        ).hex()

        # Texture: sampling params from PropertyGroup, name from node tree
        if bsp.is_textured:
            tex_name = _tex_name_from_nodes(bl_mat)
            tex_ext_bytes = bspLib.write_texture_extension_from_parsed(
                {
                    "sky_mip_val": bsp.texture.ext.sky_mip_val,
                    "tfb_magic": bsp.texture.ext.tfb_magic,
                    "tfb_d1": bsp.texture.ext.tfb_d1,
                    "tfb_d2": bsp.texture.ext.tfb_d2,
                },
                stamp,
            )
            mat["texture"] = {
                "filterMode": bsp.texture.filter_mode,
                "addressModes": bsp.texture.address_modes,
                "useMipLevels": bsp.texture.use_mip_levels,
                "diffuseTextureName": tex_name,
                "alphaTextureName": "",
                "extensionData": tex_ext_bytes.hex(),
            }
        return mat

    # Fallback for materials not imported from BSP
    mat = {
        "unusedFlags": 0,
        "color": {"r": 255, "g": 255, "b": 255, "a": 255},
        "unusedInt2": bspLib.DEFAULT_MATERIAL_UNUSED_INT2,
        "isTextured": 0,
        "ambient": 1.0,
        "specular": 0.0,
        "diffuse": 1.0,
    }
    if bl_mat is None:
        return mat

    transparent = False
    if hasattr(bl_mat, "surface_render_method"):
        transparent = bl_mat.surface_render_method == "BLENDED"
    elif getattr(bl_mat, "blend_method", "OPAQUE") != "OPAQUE":
        transparent = True
    mat["transparent"] = transparent

    tex_name = _tex_name_from_nodes(bl_mat)
    if tex_name:
        mat["isTextured"] = 1
        mat["texture"] = {
            "filterMode": 2,
            "addressModes": 17,
            "useMipLevels": 1,
            "diffuseTextureName": tex_name,
            "alphaTextureName": "",
        }
    return mat


def _tex_name_from_nodes(bl_mat):
    """Extract the texture base name from a TEX_IMAGE node (label or image name)."""
    if not (bl_mat and bl_mat.use_nodes and bl_mat.node_tree):
        return ""
    for node in bl_mat.node_tree.nodes:
        if node.type == "TEX_IMAGE":
            name = node.label or (node.image.name if node.image else "")
            if name:
                for ext in (".png", ".PNG", ".dds", ".DDS", ".tga", ".TGA"):
                    if name.endswith(ext):
                        name = name[: -len(ext)]
                        break
                return name
    return ""


class EXPORT_OT_bsp(Operator, ExportHelper):
    bl_idname = "export_scene.bsp"
    bl_label = "Export BSP"
    bl_options = {"PRESET"}

    filename_ext = ".bsp"
    filter_glob: StringProperty(default="*.bsp", options={"HIDDEN"})  # type: ignore

    scale: FloatProperty(
        name="Scale",
        description="Import scale to undo (must match the scale the map was imported with; ignored when 'Use Stored Settings' finds one)",
        default=0.05,
        min=0.000001,
        max=1000.0,
    )  # type: ignore

    selected_only: BoolProperty(
        name="Selected Objects Only",
        description="Export only selected mesh objects (all visible mesh objects otherwise)",
        default=True,
    )  # type: ignore

    apply_modifiers: BoolProperty(
        name="Apply Modifiers",
        description="Export the evaluated (modifier-applied) meshes",
        default=True,
    )  # type: ignore

    use_stored_settings: BoolProperty(
        name="Use Stored Settings",
        description="Reuse world flags, extensions, version stamp and import scale stored on an object by the BSP importer, so re-exports match the original file",
        default=True,
    )  # type: ignore

    max_sector_triangles: IntProperty(
        name="Max Triangles / Sector",
        description="Sectors are split like the original RW world importer until below this",
        default=1024,
        min=64,
        max=16000,
    )  # type: ignore

    write_binmesh: BoolProperty(
        name="Generate BinMesh",
        description="Write the BinMesh PLG (pre-optimized topology) into each sector like the original tools. The game renders from this data, so only disable for debugging",
        default=True,
    )  # type: ignore

    tristrip: BoolProperty(
        name="Triangle Strips",
        description="Write BinMesh data as triangle strips like the original tools (disable for plain triangle lists)",
        default=True,
    )  # type: ignore

    def execute(self, context):
        objs = [
            o
            for o in (context.selected_objects if self.selected_only else context.visible_objects)
            if o.type == "MESH"
        ]
        if not objs and context.active_object and context.active_object.type == "MESH":
            objs = [context.active_object]
        if not objs:
            self.report({"ERROR"}, "No mesh objects to export")
            return {"CANCELLED"}

        # World-level settings from the BSP PropertyGroup, falling back to operator props
        world_kwargs = {}
        scale = self.scale
        stamp = bspLib.DEFAULT_VERSION_STAMP

        if self.use_stored_settings:
            for o in [context.active_object] + objs:
                if not (o and o.bsp.has_data):
                    continue
                obj_bsp = o.bsp
                stamp = obj_bsp.stamp & 0xFFFFFFFF
                scale = obj_bsp.import_scale
                world_kwargs = {
                    "world_flags": obj_bsp.world_flags & 0xFFFFFFFF,
                    "stamp": stamp,
                    "inverse_origin": tuple(obj_bsp.inv_origin),
                    "root_is_world_sector": obj_bsp.root_is_world_sector,
                    "world_extension": bspLib.write_world_extension_from_parsed(
                        {
                            "magic": obj_bsp.ext.magic,
                            "d1": obj_bsp.ext.d1,
                            "d2": obj_bsp.ext.d2,
                            "d3": obj_bsp.ext.d3,
                        },
                        stamp,
                    ),
                }
                break

        try:
            verts, cols, uvs, tris, materials = self._gather_geometry(context, objs, scale, stamp)
        except ValueError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}

        if not tris:
            self.report({"ERROR"}, "No exportable triangles found")
            return {"CANCELLED"}

        data = bspLib.build_world(
            verts,
            cols,
            uvs,
            tris,
            materials,
            max_triangles_per_sector=self.max_sector_triangles,
            tristrip=self.tristrip,
            write_binmesh=self.write_binmesh,
            **world_kwargs,
        )
        with open(self.filepath, "wb") as f:
            f.write(data)

        self.report(
            {"INFO"},
            f"Exported {len(verts)} verts, {len(tris)} tris, {len(materials)} materials ({len(data)} bytes)",
        )
        return {"FINISHED"}

    def _gather_geometry(self, context, objs, scale, stamp):
        import bpy  # noqa: F401

        depsgraph = context.evaluated_depsgraph_get() if self.apply_modifiers else None

        verts = []
        cols = []
        uvs = []
        tris = []
        materials = []
        mat_index_cache = {}  # bl material name (or None) -> global index

        def material_index(bl_mat):
            key = bl_mat.name if bl_mat else None
            if key not in mat_index_cache:
                mat_index_cache[key] = len(materials)
                materials.append(_material_to_bsp(bl_mat, stamp))
            return mat_index_cache[key]

        inv = 1.0 / scale
        for obj in objs:
            src = obj.evaluated_get(depsgraph) if depsgraph else obj
            mesh = src.to_mesh()
            try:
                mesh.calc_loop_triangles()
                mw = obj.matrix_world

                uv_layer = mesh.uv_layers.active
                uv_data = uv_layer.data if uv_layer else None

                col_data = None
                col_domain = "CORNER"
                if hasattr(mesh, "color_attributes") and mesh.color_attributes:
                    attr = (
                        mesh.color_attributes.get("Color")
                        or mesh.color_attributes.active_color
                    )
                    if attr:
                        col_data = attr.data
                        col_domain = attr.domain
                elif mesh.vertex_colors.active:
                    col_data = mesh.vertex_colors.active.data

                # Blender -> RW: undo import transform (scale + Y/Z swap)
                positions = []
                for v in mesh.vertices:
                    p = mw @ v.co
                    positions.append((p.x * inv, p.z * inv, p.y * inv))

                slot_mats = [material_index(s.material) for s in obj.material_slots]
                if not slot_mats:
                    slot_mats = [material_index(None)]

                weld = {}
                for lt in mesh.loop_triangles:
                    mat = slot_mats[lt.material_index] if lt.material_index < len(slot_mats) else slot_mats[0]
                    corner_ids = []
                    for loop_index in lt.loops:
                        loop = mesh.loops[loop_index]
                        vi = loop.vertex_index
                        if uv_data is not None:
                            u, v = uv_data[loop_index].uv
                            uv = (u, 1.0 - v)  # undo import V flip
                        else:
                            uv = (0.0, 0.0)
                        if col_data is not None:
                            ci = loop_index if col_domain == "CORNER" else vi
                            c = col_data[ci].color
                            col = tuple(min(255, max(0, round(c[k] * 255.0))) for k in range(4))
                        else:
                            col = (255, 255, 255, 255)
                        # Weld by value, not vertex index: coincident vertices
                        # with equal UV and color become one RW vertex, like
                        # the original files (stacked blend layers share
                        # vertices; the importer splits them for Blender).
                        key = (positions[vi], uv, col)
                        gi = weld.get(key)
                        if gi is None:
                            gi = len(verts)
                            weld[key] = gi
                            verts.append(positions[vi])
                            uvs.append(uv)
                            cols.append(col)
                        corner_ids.append(gi)
                    # undo import winding flip: blender (v0, v2, v1) -> RW (v0, v1, v2)
                    tris.append((corner_ids[0], corner_ids[2], corner_ids[1], mat))
            finally:
                src.to_mesh_clear()

        if len(materials) > 0xFFFF:
            raise ValueError("Too many materials for BSP (max 65535)")
        return verts, cols, uvs, tris, materials

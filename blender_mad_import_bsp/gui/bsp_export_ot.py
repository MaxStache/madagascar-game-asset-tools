import json

from bpy.types import Operator
from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty, FloatProperty, BoolProperty, IntProperty

from .. import bspLib


def _material_to_bsp(bl_mat):
    """Build a bspLib material dict from a Blender material.

    Imported materials carry the original parsed data in the "bsp_material"
    custom property and round-trip byte-identically (incl. TFB extensions).
    Anything else gets the defaults the original tools wrote, marked
    transparent when the Blender material uses a blended surface.
    """
    if bl_mat is not None:
        stored = bl_mat.get("bsp_material")
        if stored:
            try:
                return json.loads(stored)
            except (ValueError, TypeError):
                pass

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

    tex_name = ""
    if bl_mat.use_nodes and bl_mat.node_tree:
        for node in bl_mat.node_tree.nodes:
            if node.type == "TEX_IMAGE":
                if node.label:
                    tex_name = node.label
                elif node.image:
                    tex_name = node.image.name
                break
    if tex_name:
        for ext in (".png", ".PNG", ".dds", ".DDS", ".tga", ".TGA"):
            if tex_name.endswith(ext):
                tex_name = tex_name[: -len(ext)]
                break
        mat["isTextured"] = 1
        mat["texture"] = {
            "filterMode": 2,
            "addressModes": 17,
            "useMipLevels": 1,
            "diffuseTextureName": tex_name,
            "alphaTextureName": "",
        }
    return mat


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

        # World-level settings, stored by the importer for faithful re-export
        world_kwargs = {}
        scale = self.scale
        if self.use_stored_settings:
            for o in [context.active_object] + objs:
                stored = o.get("bsp_world") if o else None
                if not stored:
                    continue
                try:
                    w = json.loads(stored)
                except (ValueError, TypeError):
                    continue
                world_kwargs = {
                    "world_flags": w.get("worldFlags", bspLib.DEFAULT_WORLD_FLAGS),
                    "stamp": w.get("stamp", bspLib.DEFAULT_VERSION_STAMP),
                    "inverse_origin": tuple(w.get("inverseOrigin", (-0.0, -0.0, -0.0))),
                    "root_is_world_sector": w.get("rootIsWorldSector", 0),
                }
                if w.get("worldExtData"):
                    world_kwargs["world_extension"] = bytes.fromhex(w["worldExtData"])
                if w.get("importScale"):
                    scale = w["importScale"]
                break

        try:
            verts, cols, uvs, tris, materials = self._gather_geometry(context, objs, scale)
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

    def _gather_geometry(self, context, objs, scale):
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
                materials.append(_material_to_bsp(bl_mat))
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

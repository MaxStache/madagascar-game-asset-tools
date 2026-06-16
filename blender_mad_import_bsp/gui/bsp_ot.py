from bpy.types import Operator
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, FloatProperty, BoolProperty

from ..bspLib import parse_file as parse_bsp_file
from ..bspLib import collect_atomic_sectors


class IMPORT_OT_bsp(Operator, ImportHelper):
    bl_idname = "import_scene.bsp"
    bl_label = "Import BSP"
    bl_options = {"PRESET", "UNDO"}

    filename_ext = ".bsp"
    filter_glob: StringProperty(default="*.bsp", options={"HIDDEN"})  # type: ignore

    scale: FloatProperty(
        name="Scale",
        description="Scale factor for imported geometry (Default 0.01 because RW Unit is 1cm but blender is 1m, we need to scale it a little larger because its too small otherwise and blender hates that)",
        default=0.05,
        min=0.000001,
        max=1000.0,
    )  # type: ignore

    texture_prefix: StringProperty(
        name="Texture Prefix",
        description="Path prefix for textures relative to BSP location (e.g., 'textures/' or '../shared/')",
        default="",
    )  # type: ignore

    recalc_normals: BoolProperty(
        name="Recalculate Normals",
        description="Recalculate face normals to be consistent (disable if your BSP has intentional double-sided geometry)",
        default=False,
    )  # type: ignore

    def execute(self, context):
        import os

        if os.path.isdir(self.filepath):
            self.report(
                {"ERROR"}, "Selected path is a folder, please select a BSP file."
            )
            return {"CANCELLED"}

        result = self.import_bsp(
            context,
            self.filepath,
            self.scale,
            self.texture_prefix,
            self.recalc_normals,
        )
        return result or {"FINISHED"}

    def import_bsp(self, context, filepath, scale=0.05, texture_prefix="", recalc_normals=False):
        import bpy
        import bmesh
        import random
        import os

        parsed_bsp = parse_bsp_file(filepath)
        sectors = collect_atomic_sectors(parsed_bsp.get("worldChunk", []))
        if not sectors:
            self.report({"ERROR"}, "No geometry found in BSP")
            return {"CANCELLED"}

        materials = parsed_bsp.get("materialList", {}).get("materials", [])
        mat_suffix = str(random.randint(1000, 9999))
        bsp_name = os.path.splitext(os.path.basename(filepath))[0]
        bsp_dir = os.path.dirname(filepath)

        # Pre-scan: determine which material indices have non-opaque vertex alpha
        ALPHA_THRESHOLD = 254
        materials_with_vertex_alpha = set()
        for sector in sectors:
            if sector.get("isNativeData"):
                continue
            sector_colors = sector.get("colors", [])
            sector_triangles = sector.get("triangles", [])
            mat_base = sector.get("matListWindowBase", 0)
            if not sector_colors:
                continue
            for tri in sector_triangles:
                mat_idx = mat_base + tri[3]
                for vi in (tri[0], tri[1], tri[2]):
                    if vi < len(sector_colors) and sector_colors[vi][3] < ALPHA_THRESHOLD:
                        materials_with_vertex_alpha.add(mat_idx)
                        break

        # Create Blender materials
        blender_materials = []
        for i, mat in enumerate(materials):
            bl_mat = bpy.data.materials.new(name=f"{bsp_name}_mat_{i}_{mat_suffix}")
            bl_mat.use_nodes = True
            bl_mat.use_backface_culling = False

            nodes = bl_mat.node_tree.nodes
            links = bl_mat.node_tree.links
            bsdf = nodes.get("Principled BSDF")

            if bsdf:
                color = mat.get("color", {})
                r = color.get("r", 255) / 255.0
                g = color.get("g", 255) / 255.0
                b = color.get("b", 255) / 255.0
                a = color.get("a", 255) / 255.0
                bsdf.inputs["Base Color"].default_value = (r, g, b, 1.0)
                bsdf.inputs["Roughness"].default_value = 1.0 - mat.get("specular", 0.0)

                vcol_node = nodes.new(type="ShaderNodeVertexColor")
                vcol_node.layer_name = "Color"
                vcol_node.location = (-650, 300)

                is_transparent = (
                    a < 0.999
                    or mat.get("isTransparent", False)
                    or mat.get("hasAlpha", False)
                    or mat.get("alphaBlend", False)
                    or i in materials_with_vertex_alpha
                )

                tex_node = None
                if mat.get("isTextured") and mat.get("texture"):
                    tex_name = mat["texture"].get("diffuseTextureName", "")
                    if tex_name:
                        tex_node = nodes.new(type="ShaderNodeTexImage")
                        tex_node.location = (-300, 300)
                        tex_node.label = tex_name
                        tex_node.interpolation = "Closest"

                        tex_path = os.path.join(bsp_dir, texture_prefix, f"{tex_name}.png")
                        try:
                            image = bpy.data.images.load(tex_path, check_existing=True)
                        except Exception:
                            image = bpy.data.images.new(name=tex_name, width=1, height=1)
                            image.filepath = tex_path
                            image.source = "FILE"
                        tex_node.image = image

                # Color: texture × vertex_color (or just vertex_color if no texture)
                if tex_node:
                    import bpy.app
                    if bpy.app.version >= (4, 0, 0):
                        mix_node = nodes.new(type="ShaderNodeMix")
                        mix_node.data_type = "RGBA"
                        mix_node.blend_type = "MULTIPLY"
                        mix_node.inputs["Factor"].default_value = 1.0
                        mix_node.location = (-100, 300)
                        links.new(tex_node.outputs["Color"], mix_node.inputs["A"])
                        links.new(vcol_node.outputs["Color"], mix_node.inputs["B"])
                        links.new(mix_node.outputs["Result"], bsdf.inputs["Base Color"])
                    else:
                        mix_node = nodes.new(type="ShaderNodeMixRGB")
                        mix_node.blend_type = "MULTIPLY"
                        mix_node.inputs["Fac"].default_value = 1.0
                        mix_node.location = (-100, 300)
                        links.new(tex_node.outputs["Color"], mix_node.inputs["Color1"])
                        links.new(vcol_node.outputs["Color"], mix_node.inputs["Color2"])
                        links.new(mix_node.outputs["Color"], bsdf.inputs["Base Color"])
                else:
                    links.new(vcol_node.outputs["Color"], bsdf.inputs["Base Color"])

                # Alpha: vcol_alpha × tex_alpha × mat_a — all three only when relevant
                if is_transparent:
                    alpha_out = vcol_node.outputs["Alpha"]

                    if tex_node:
                        mul = nodes.new(type="ShaderNodeMath")
                        mul.operation = "MULTIPLY"
                        mul.location = (-300, 100)
                        links.new(tex_node.outputs["Alpha"], mul.inputs[0])
                        links.new(alpha_out, mul.inputs[1])
                        alpha_out = mul.outputs["Value"]

                    if a < 0.999:
                        mul2 = nodes.new(type="ShaderNodeMath")
                        mul2.operation = "MULTIPLY"
                        mul2.inputs[0].default_value = a
                        mul2.location = (-100, 100)
                        links.new(alpha_out, mul2.inputs[1])
                        alpha_out = mul2.outputs["Value"]

                    links.new(alpha_out, bsdf.inputs["Alpha"])

                if hasattr(bl_mat, "surface_render_method"):
                    bl_mat.surface_render_method = "BLENDED" if is_transparent else "DITHERED"
                else:
                    if is_transparent:
                        bl_mat.blend_method = "BLEND"
                        if hasattr(bl_mat, "shadow_method"):
                            bl_mat.shadow_method = "HASHED"
                    else:
                        bl_mat.blend_method = "OPAQUE"

            blender_materials.append(bl_mat)

        all_verts = []
        all_faces = []
        all_face_materials = []
        all_uvs = []
        all_colors = []
        vertex_offset = 0

        for sector in sectors:
            if sector.get("isNativeData"):
                continue
            vertices = sector.get("vertices", [])
            uvs = sector.get("uvs", [])
            colors = sector.get("colors", [])
            triangles = sector.get("triangles", [])
            mat_base = sector.get("matListWindowBase", 0)
            if not vertices:
                continue

            for i, v in enumerate(vertices):
                all_verts.append((v[0] * scale, v[2] * scale, v[1] * scale))
                all_uvs.append((uvs[i][0], 1.0 - uvs[i][1]) if uvs and i < len(uvs) else (0.0, 0.0))
                if colors and i < len(colors):
                    c = colors[i]
                    all_colors.append((c[0] / 255.0, c[1] / 255.0, c[2] / 255.0, c[3] / 255.0))
                else:
                    all_colors.append((1.0, 1.0, 1.0, 1.0))

            num_sector_verts = len(vertices)
            for tri in triangles:
                v0, v1, v2 = tri[0], tri[1], tri[2]
                if v0 >= num_sector_verts or v1 >= num_sector_verts or v2 >= num_sector_verts:
                    continue
                if v0 == v1 or v0 == v2 or v1 == v2:
                    continue
                all_faces.append((
                    v0 + vertex_offset,
                    v2 + vertex_offset,
                    v1 + vertex_offset,
                ))
                all_face_materials.append(mat_base + tri[3])
            vertex_offset += len(vertices)

        if not all_faces:
            self.report({"ERROR"}, "No geometry found")
            return {"CANCELLED"}

        # Build single mesh object
        mesh = bpy.data.meshes.new(f"{bsp_name}_Mesh")
        obj = bpy.data.objects.new(bsp_name, mesh)
        context.collection.objects.link(obj)

        # Build material slots before from_pydata so we can assign per-polygon
        # indices before mesh.validate() runs. validate() can silently remove
        # degenerate faces, which would desync a post-validate foreach_set call.
        used_mats = sorted(set(all_face_materials))
        mat_to_slot = {}
        for mat_idx in used_mats:
            if mat_idx < len(blender_materials):
                mat_to_slot[mat_idx] = len(obj.data.materials)
                obj.data.materials.append(blender_materials[mat_idx])

        mesh.from_pydata(all_verts, [], all_faces)

        # Set per-polygon slot indices now — before validate removes any faces.
        slot_indices = [mat_to_slot.get(m, 0) for m in all_face_materials]
        mesh.polygons.foreach_set("material_index", slot_indices)

        mesh.validate()
        mesh.update()

        if recalc_normals:
            bm = bmesh.new()
            bm.from_mesh(mesh)
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
            bm.to_mesh(mesh)
            bm.free()
            mesh.update()

        # Apply UVs — build from mesh.loops so the count matches after mesh.validate()
        if all_uvs:
            uv_layer = mesh.uv_layers.new(name="UVMap")
            uvs_flat = [coord for loop in mesh.loops for coord in all_uvs[loop.vertex_index]]
            uv_layer.data.foreach_set("uv", uvs_flat)

        # Apply vertex colors — use color_attributes with FLOAT_COLOR so values
        # stay in linear space and aren't double-gamma-converted by the sRGB byte path.
        # Build from mesh.loops so the count matches after mesh.validate().
        if all_colors:
            colors_flat = [comp for loop in mesh.loops for comp in all_colors[loop.vertex_index]]
            if hasattr(mesh, "color_attributes"):
                col_attr = mesh.color_attributes.new(name="Color", type="FLOAT_COLOR", domain="CORNER")
                col_attr.data.foreach_set("color", colors_flat)
            else:
                color_layer = mesh.vertex_colors.new(name="Color")
                color_layer.data.foreach_set("color", colors_flat)

        obj.select_set(True)
        context.view_layer.objects.active = obj

        self.report({"INFO"}, f"Imported {len(all_verts)} verts, {len(all_faces)} faces")
        return {"FINISHED"}

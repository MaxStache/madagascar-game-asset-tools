
def _collect_atomic_sectors(
    chunk: Union[RW_World_AtomicSector, RW_World_PlaneSector],
) -> list[RW_World_AtomicSector]:
    if chunk is None:
        return []

    sectors = []
    if isinstance(chunk, RW_World_AtomicSector):
        sectors.append(chunk)
    elif isinstance(chunk, RW_World_PlaneSector):
        sectors.extend(_collect_atomic_sectors(chunk.left_data))
        sectors.extend(_collect_atomic_sectors(chunk.right_data))

    return sectors


def _get_world_bounds(bsp: RW_World) -> tuple[Vector3, Vector3]:
    data = bsp.world_struct.data

    if hasattr(data, "boxMin") and getattr(data, "boxMin") is not None:
        return data.boxMin, data.boxMax

    sectors = _collect_atomic_sectors(bsp.world_chunk.data)
    if not sectors:
        raise ValueError("No atomic sectors found for bounds")

    min_x = float("inf")
    min_y = float("inf")
    min_z = float("inf")
    max_x = float("-inf")
    max_y = float("-inf")
    max_z = float("-inf")

    for sector in sectors:
        for v in sector.vertices:
            min_x = min(min_x, v.x)
            min_y = min(min_y, v.y)
            min_z = min(min_z, v.z)
            max_x = max(max_x, v.x)
            max_y = max(max_y, v.y)
            max_z = max(max_z, v.z)

    return Vector3(min_x, min_y, min_z), Vector3(max_x, max_y, max_z)


def _get_world_bounds_multi(bsps: list[RW_World]) -> tuple[Vector3, Vector3]:
    if not bsps:
        raise ValueError("No BSPs provided for bounds")

    mins = []
    maxs = []
    for bsp in bsps:
        bmin, bmax = _get_world_bounds(bsp)
        mins.append(bmin)
        maxs.append(bmax)

    min_x = min(b.x for b in mins)
    min_y = min(b.y for b in mins)
    min_z = min(b.z for b in mins)
    max_x = max(b.x for b in maxs)
    max_y = max(b.y for b in maxs)
    max_z = max(b.z for b in maxs)

    return Vector3(min_x, min_y, min_z), Vector3(max_x, max_y, max_z)


def _replace_bounds(
    bounds_min: Vector3,
    bounds_max: Vector3,
    axis: str,
    min_value: Optional[float] = None,
    max_value: Optional[float] = None,
) -> tuple[Vector3, Vector3]:
    if axis == "x":
        new_min = Vector3(min_value if min_value is not None else bounds_min.x, bounds_min.y, bounds_min.z)
        new_max = Vector3(max_value if max_value is not None else bounds_max.x, bounds_max.y, bounds_max.z)
    elif axis == "y":
        new_min = Vector3(bounds_min.x, min_value if min_value is not None else bounds_min.y, bounds_min.z)
        new_max = Vector3(bounds_max.x, max_value if max_value is not None else bounds_max.y, bounds_max.z)
    elif axis == "z":
        new_min = Vector3(bounds_min.x, bounds_min.y, min_value if min_value is not None else bounds_min.z)
        new_max = Vector3(bounds_max.x, bounds_max.y, max_value if max_value is not None else bounds_max.z)
    else:
        new_min = bounds_min
        new_max = bounds_max

    return new_min, new_max


def _collect_plane_segments_topdown(
    node: Union[RW_World_AtomicSector, RW_World_PlaneSector],
    bounds_min: Vector3,
    bounds_max: Vector3,
    depth: int = 0,
) -> list[tuple[float, float, float, float, int, str]]:
    if node is None or isinstance(node, RW_World_AtomicSector):
        return []

    segments = []

    if node.type == RW_World_PlaneSectorType.rwPLANE_X:
        segments.append((node.value, bounds_min.z, node.value, bounds_max.z, depth, "x"))
        left_min, left_max = _replace_bounds(bounds_min, bounds_max, "x", max_value=node.left_value)
        right_min, right_max = _replace_bounds(bounds_min, bounds_max, "x", min_value=node.right_value)
    elif node.type == RW_World_PlaneSectorType.rwPLANE_Z:
        segments.append((bounds_min.x, node.value, bounds_max.x, node.value, depth, "z"))
        left_min, left_max = _replace_bounds(bounds_min, bounds_max, "z", max_value=node.left_value)
        right_min, right_max = _replace_bounds(bounds_min, bounds_max, "z", min_value=node.right_value)
    else:
        left_min, left_max = _replace_bounds(bounds_min, bounds_max, "y", max_value=node.left_value)
        right_min, right_max = _replace_bounds(bounds_min, bounds_max, "y", min_value=node.right_value)

    segments.extend(_collect_plane_segments_topdown(node.left_data, left_min, left_max, depth + 1))
    segments.extend(_collect_plane_segments_topdown(node.right_data, right_min, right_max, depth + 1))

    return segments


def export_bsp_cuts_topdown_svg(
    bsp: RW_World,
    svg_path: Union[str, Path],
    width: int = 1024,
    height: int = 1024,
    padding: int = 20,
    stroke: str = "#111111",
    stroke_width: float = 1.0,
    cut_opacity: float = 1.0,
    show_bounds: bool = True,
    draw_geometry: bool = True,
    geometry_stroke: str = "#000000",
    geometry_stroke_width: float = 0.5,
    geometry_opacity: float = 0.35,
):
    """Export a top-down SVG of BSP plane cuts.

    The view is XZ top-down (Y up). Only X/Z plane cuts are drawn.
    """
    bounds_min, bounds_max = _get_world_bounds(bsp)

    segments = _collect_plane_segments_topdown(
        bsp.world_chunk.data,
        bounds_min,
        bounds_max,
    )

    span_x = max(bounds_max.x - bounds_min.x, 1e-6)
    span_z = max(bounds_max.z - bounds_min.z, 1e-6)
    scale = min(
        (width - 2 * padding) / span_x,
        (height - 2 * padding) / span_z,
    )

    def to_svg_x(x: float) -> float:
        return padding + (x - bounds_min.x) * scale

    def to_svg_y(z: float) -> float:
        return padding + (bounds_max.z - z) * scale

    with open(svg_path, "w") as f:
        f.write("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n")
        f.write(
            f"<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"{width}\" height=\"{height}\" "
            f"viewBox=\"0 0 {width} {height}\">\n"
        )
        f.write("<rect width=\"100%\" height=\"100%\" fill=\"#ffffff\"/>\n")

        if show_bounds:
            x0 = to_svg_x(bounds_min.x)
            y0 = to_svg_y(bounds_min.z)
            x1 = to_svg_x(bounds_max.x)
            y1 = to_svg_y(bounds_max.z)
            rect_x = min(x0, x1)
            rect_y = min(y0, y1)
            rect_w = abs(x1 - x0)
            rect_h = abs(y1 - y0)
            f.write(
                f"<rect x=\"{rect_x:.2f}\" y=\"{rect_y:.2f}\" width=\"{rect_w:.2f}\" height=\"{rect_h:.2f}\" "
                f"fill=\"none\" stroke=\"#888888\" stroke-width=\"1\"/>\n"
            )

        if draw_geometry:
            sectors = _collect_atomic_sectors(bsp.world_chunk.data)
            geom_parts = []
            for sector in sectors:
                vertices = sector.vertices
                for tri in sector.triangles:
                    v1 = vertices[tri.vertex1]
                    v2 = vertices[tri.vertex2]
                    v3 = vertices[tri.vertex3]

                    x1 = to_svg_x(v1.x)
                    y1 = to_svg_y(v1.z)
                    x2 = to_svg_x(v2.x)
                    y2 = to_svg_y(v2.z)
                    x3 = to_svg_x(v3.x)
                    y3 = to_svg_y(v3.z)

                    geom_parts.append(
                        f"M {x1:.2f} {y1:.2f} L {x2:.2f} {y2:.2f} L {x3:.2f} {y3:.2f} L {x1:.2f} {y1:.2f}"
                    )

            if geom_parts:
                f.write(
                    f"<path d=\"{' '.join(geom_parts)}\" fill=\"none\" "
                    f"stroke=\"{geometry_stroke}\" stroke-width=\"{geometry_stroke_width}\" "
                    f"stroke-opacity=\"{geometry_opacity:.3f}\"/>\n"
                )

        axis_colors = {
            "x": "#d84b4b",
            "z": "#3a78d4",
            "y": "#6b6b6b",
        }
        segments_by_style = {}
        for x0, z0, x1, z1, _depth, axis in segments:
            sx0 = to_svg_x(x0)
            sy0 = to_svg_y(z0)
            sx1 = to_svg_x(x1)
            sy1 = to_svg_y(z1)
            opacity = max(0.0, min(1.0, cut_opacity))
            key = (axis, f"{opacity:.3f}")
            segments_by_style.setdefault(key, []).append(
                f"M {sx0:.2f} {sy0:.2f} L {sx1:.2f} {sy1:.2f}"
            )

        for (axis, opacity), parts in segments_by_style.items():
            axis_color = axis_colors.get(axis, stroke)
            f.write(
                f"<path d=\"{' '.join(parts)}\" fill=\"none\" stroke=\"{axis_color}\" "
                f"stroke-width=\"{stroke_width}\" stroke-opacity=\"{opacity}\"/>\n"
            )

        f.write("</svg>\n")


def export_bsp_cuts_topdown_png(
    bsp: RW_World,
    png_path: Union[str, Path],
    resolution: float = 1.0,
    padding: int = 20,
    stroke_width: float = 1.0,
    cut_opacity: float = 1.0,
    show_bounds: bool = True,
    draw_geometry: bool = True,
    geometry_mode: str = "wire",
    geometry_stroke_width: float = 0.5,
    geometry_opacity: float = 0.35,
    geometry_fill_opacity: float = 0.6,
    geometry_stride: int = 1,
    max_triangles: Optional[int] = None,
    txd_path: Optional[Union[str, Path]] = None,
    texture_flip_v: bool = True,
    texture_wrap: bool = True,
    background: str = "#ffffff",
):
    """Export a top-down PNG of BSP plane cuts.

    The view is XZ top-down (Y up). Only X/Z plane cuts are drawn.
    Resolution is pixels per world unit.
    """
    try:
        from PIL import Image, ImageDraw
    except ImportError as exc:
        raise ImportError("Pillow is required for PNG export. Install with 'pip install pillow'.") from exc

    bounds_min, bounds_max = _get_world_bounds(bsp)

    segments = _collect_plane_segments_topdown(
        bsp.world_chunk.data,
        bounds_min,
        bounds_max,
    )

    span_x = max(bounds_max.x - bounds_min.x, 1e-6)
    span_z = max(bounds_max.z - bounds_min.z, 1e-6)
    if resolution <= 0:
        raise ValueError("resolution must be > 0")

    if span_x >= span_z:
        width = max(1, int(math.ceil(resolution)))
        height = max(1, int(math.ceil(resolution * (span_z / span_x))))
    else:
        height = max(1, int(math.ceil(resolution)))
        width = max(1, int(math.ceil(resolution * (span_x / span_z))))

    scale = min(
        (width - 2 * padding) / span_x,
        (height - 2 * padding) / span_z,
    )

    def to_px_x(x: float) -> float:
        return padding + (x - bounds_min.x) * scale

    def to_px_y(z: float) -> float:
        return padding + (bounds_max.z - z) * scale

    def hex_to_rgba(hex_color: str, alpha: float) -> tuple[int, int, int, int]:
        hex_color = hex_color.lstrip("#")
        if len(hex_color) != 6:
            return (0, 0, 0, int(255 * alpha))
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        a = int(max(0.0, min(1.0, alpha)) * 255)
        return (r, g, b, a)

    img = Image.new("RGBA", (width, height), hex_to_rgba(background, 1.0))
    draw = ImageDraw.Draw(img, "RGBA")

    if show_bounds:
        x0 = to_px_x(bounds_min.x)
        y0 = to_px_y(bounds_min.z)
        x1 = to_px_x(bounds_max.x)
        y1 = to_px_y(bounds_max.z)
        rect = [min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)]
        draw.rectangle(rect, outline=hex_to_rgba("#888888", 1.0), width=1)

    if draw_geometry:
        stride = max(1, geometry_stride)
        tri_limit = max_triangles if (max_triangles is None or max_triangles > 0) else None
        mode = geometry_mode.lower().strip()
        valid_modes = {"wire", "fill", "both", "material", "material_wire", "texture", "texture_wire"}
        if mode not in valid_modes:
            raise ValueError(
                "geometry_mode must be 'wire', 'fill', 'both', 'material', 'material_wire', 'texture', or 'texture_wire'"
            )
        geom_stroke = hex_to_rgba("#000000", geometry_opacity)
        geom_fill = hex_to_rgba("#000000", geometry_fill_opacity)
        materials = bsp.material_list.materials
        tex_by_name = {}
        tex_images = {}
        if mode in {"texture", "texture_wire"}:
            if txd_path is None:
                raise ValueError("txd_path is required for texture rendering")
            import rwtxd

            txd = rwtxd.load(txd_path)
            for tex in txd.textures:
                tex_by_name[tex.name.lower()] = tex
        sectors = _collect_atomic_sectors(bsp.world_chunk.data)
        tri_count = 0
        pixels = img.load()
        for sector in sectors:
            vertices = sector.vertices
            uvs = sector.uvs if sector.uvs else None
            colors = sector.colors if sector.colors else None
            for tri_index, tri in enumerate(sector.triangles):
                if tri_index % stride != 0:
                    continue
                if tri_limit is not None and tri_count >= tri_limit:
                    break
                v1 = vertices[tri.vertex1]
                v2 = vertices[tri.vertex2]
                v3 = vertices[tri.vertex3]

                x1 = to_px_x(v1.x)
                y1 = to_px_y(v1.z)
                x2 = to_px_x(v2.x)
                y2 = to_px_y(v2.z)
                x3 = to_px_x(v3.x)
                y3 = to_px_y(v3.z)

                def get_vertex_color(idx: int) -> tuple[int, int, int, int]:
                    if colors is not None and len(colors) == len(vertices):
                        c = colors[idx]
                        return (c.r, c.g, c.b, c.a)
                    return (255, 255, 255, 255)

                def get_material_color(mat_index: int) -> tuple[int, int, int, int]:
                    if 0 <= mat_index < len(materials):
                        mc = materials[mat_index].color
                        return (mc.r, mc.g, mc.b, mc.a)
                    return (255, 255, 255, 255)

                if mode in {"texture", "texture_wire"}:
                    if uvs is None:
                        draw.polygon([x1, y1, x2, y2, x3, y3], fill=geom_fill)
                    else:
                        mat_idx = sector.matListWindowBase + tri.materialIndex
                        tex_image = None
                        mat_color = get_material_color(mat_idx)
                        if 0 <= mat_idx < len(materials):
                            mat = materials[mat_idx]
                            if mat.isTextured and mat.texture and mat.texture.diffuseTextureName:
                                tex_name = mat.texture.diffuseTextureName.lower()
                                tex = tex_by_name.get(tex_name)
                                if tex is not None:
                                    tex_image = tex_images.get(tex_name)
                                    if tex_image is None:
                                        rgba = rwtxd.decode(tex)
                                        tex_image = Image.frombytes("RGBA", (tex.width, tex.height), rgba)
                                        tex_images[tex_name] = tex_image

                        if tex_image is None:
                            vc1 = get_vertex_color(tri.vertex1)
                            vc2 = get_vertex_color(tri.vertex2)
                            vc3 = get_vertex_color(tri.vertex3)
                            vc_r = (vc1[0] + vc2[0] + vc3[0]) / 3.0
                            vc_g = (vc1[1] + vc2[1] + vc3[1]) / 3.0
                            vc_b = (vc1[2] + vc2[2] + vc3[2]) / 3.0
                            vc_a = (vc1[3] + vc2[3] + vc3[3]) / 3.0
                            fill_r = int((mat_color[0] * vc_r) / 255.0)
                            fill_g = int((mat_color[1] * vc_g) / 255.0)
                            fill_b = int((mat_color[2] * vc_b) / 255.0)
                            fill_a = (mat_color[3] / 255.0) * (vc_a / 255.0) * geometry_fill_opacity
                            fill_color = (fill_r, fill_g, fill_b, int(max(0.0, min(1.0, fill_a)) * 255))
                            draw.polygon([x1, y1, x2, y2, x3, y3], fill=fill_color)
                        else:
                            u1 = uvs[tri.vertex1].u
                            v1 = uvs[tri.vertex1].v
                            u2 = uvs[tri.vertex2].u
                            v2 = uvs[tri.vertex2].v
                            u3 = uvs[tri.vertex3].u
                            v3 = uvs[tri.vertex3].v
                            if texture_flip_v:
                                v1 = 1.0 - v1
                                v2 = 1.0 - v2
                                v3 = 1.0 - v3

                            min_x = max(0, int(math.floor(min(x1, x2, x3))))
                            max_x = min(width - 1, int(math.ceil(max(x1, x2, x3))))
                            min_y = max(0, int(math.floor(min(y1, y2, y3))))
                            max_y = min(height - 1, int(math.ceil(max(y1, y2, y3))))

                            def edge(ax, ay, bx, by, cx, cy):
                                return (cx - ax) * (by - ay) - (cy - ay) * (bx - ax)

                            area = edge(x1, y1, x2, y2, x3, y3)
                            if area != 0:
                                inv_area = 1.0 / area
                                tw, th = tex_image.size
                                tex_pixels = tex_image.load()
                                vc1 = get_vertex_color(tri.vertex1)
                                vc2 = get_vertex_color(tri.vertex2)
                                vc3 = get_vertex_color(tri.vertex3)
                                for py in range(min_y, max_y + 1):
                                    for px in range(min_x, max_x + 1):
                                        w1 = edge(x2, y2, x3, y3, px, py)
                                        w2 = edge(x3, y3, x1, y1, px, py)
                                        w3 = edge(x1, y1, x2, y2, px, py)
                                        if (w1 >= 0 and w2 >= 0 and w3 >= 0) or (w1 <= 0 and w2 <= 0 and w3 <= 0):
                                            u = (w1 * u1 + w2 * u2 + w3 * u3) * inv_area
                                            v = (w1 * v1 + w2 * v2 + w3 * v3) * inv_area
                                            vc_r = (w1 * vc1[0] + w2 * vc2[0] + w3 * vc3[0]) * inv_area
                                            vc_g = (w1 * vc1[1] + w2 * vc2[1] + w3 * vc3[1]) * inv_area
                                            vc_b = (w1 * vc1[2] + w2 * vc2[2] + w3 * vc3[2]) * inv_area
                                            vc_a = (w1 * vc1[3] + w2 * vc2[3] + w3 * vc3[3]) * inv_area
                                            if texture_wrap:
                                                u = u % 1.0
                                                v = v % 1.0
                                            else:
                                                u = max(0.0, min(1.0, u))
                                                v = max(0.0, min(1.0, v))

                                            tx = min(tw - 1, max(0, int(u * (tw - 1))))
                                            ty = min(th - 1, max(0, int(v * (th - 1))))
                                            src = tex_pixels[tx, ty]
                                            if len(src) == 4:
                                                sr, sg, sb, sa = src
                                            else:
                                                sr, sg, sb = src
                                                sa = 255
                                            sr = int(sr * (mat_color[0] / 255.0) * (vc_r / 255.0))
                                            sg = int(sg * (mat_color[1] / 255.0) * (vc_g / 255.0))
                                            sb = int(sb * (mat_color[2] / 255.0) * (vc_b / 255.0))
                                            sa = (sa / 255.0) * (mat_color[3] / 255.0) * (vc_a / 255.0) * geometry_fill_opacity
                                            if sa >= 0.999:
                                                pixels[px, py] = (sr, sg, sb, 255)
                                            elif sa > 0.0:
                                                dr, dg, db, da = pixels[px, py]
                                                inv = 1.0 - sa
                                                pixels[px, py] = (
                                                    int(sr * sa + dr * inv),
                                                    int(sg * sa + dg * inv),
                                                    int(sb * sa + db * inv),
                                                    255,
                                                )
                elif mode in {"material", "material_wire"}:
                    mat_idx = sector.matListWindowBase + tri.materialIndex
                    mat_color = get_material_color(mat_idx)
                    vc1 = get_vertex_color(tri.vertex1)
                    vc2 = get_vertex_color(tri.vertex2)
                    vc3 = get_vertex_color(tri.vertex3)
                    vc_r = (vc1[0] + vc2[0] + vc3[0]) / 3.0
                    vc_g = (vc1[1] + vc2[1] + vc3[1]) / 3.0
                    vc_b = (vc1[2] + vc2[2] + vc3[2]) / 3.0
                    vc_a = (vc1[3] + vc2[3] + vc3[3]) / 3.0
                    fill_r = int((mat_color[0] * vc_r) / 255.0)
                    fill_g = int((mat_color[1] * vc_g) / 255.0)
                    fill_b = int((mat_color[2] * vc_b) / 255.0)
                    fill_a = (mat_color[3] / 255.0) * (vc_a / 255.0) * geometry_fill_opacity
                    fill_color = (fill_r, fill_g, fill_b, int(max(0.0, min(1.0, fill_a)) * 255))
                    draw.polygon([x1, y1, x2, y2, x3, y3], fill=fill_color)
                elif mode in {"fill", "both"}:
                    draw.polygon([x1, y1, x2, y2, x3, y3], fill=geom_fill)
                if mode in {"wire", "both", "material_wire", "texture_wire"}:
                    draw.line([x1, y1, x2, y2], fill=geom_stroke, width=max(1, int(geometry_stroke_width)))
                    draw.line([x2, y2, x3, y3], fill=geom_stroke, width=max(1, int(geometry_stroke_width)))
                    draw.line([x3, y3, x1, y1], fill=geom_stroke, width=max(1, int(geometry_stroke_width)))
                tri_count += 1
            if tri_limit is not None and tri_count >= tri_limit:
                break

    axis_colors = {
        "x": "#d84b4b",
        "z": "#3a78d4",
        "y": "#6b6b6b",
    }
    cut_alpha = max(0.0, min(1.0, cut_opacity))
    for x0, z0, x1, z1, _depth, axis in segments:
        sx0 = to_px_x(x0)
        sy0 = to_px_y(z0)
        sx1 = to_px_x(x1)
        sy1 = to_px_y(z1)
        color = hex_to_rgba(axis_colors.get(axis, "#111111"), cut_alpha)
        draw.line([sx0, sy0, sx1, sy1], fill=color, width=max(1, int(stroke_width)))

    img.save(png_path)


def export_bsp_cuts_topdown_png_layers(
    bsps: list[RW_World],
    png_path: Union[str, Path],
    resolution: float = 1.0,
    padding: int = 20,
    stroke_width: float = 1.0,
    cut_opacity: float = 1.0,
    show_bounds: bool = True,
    draw_geometry: bool = True,
    geometry_mode: str = "wire",
    geometry_stroke_width: float = 0.5,
    geometry_opacity: float = 0.35,
    geometry_fill_opacity: float = 0.6,
    geometry_stride: int = 1,
    max_triangles: Optional[int] = None,
    txd_paths: Optional[list[Optional[Union[str, Path]]]] = None,
    texture_flip_v: bool = True,
    texture_wrap: bool = True,
    background: str = "#ffffff",
):
    """Export a top-down PNG by layering multiple BSPs in order.

    The view is XZ top-down (Y up). Only X/Z plane cuts are drawn.
    Resolution is pixels for the longer world-bound side.
    """
    try:
        from PIL import Image, ImageDraw
    except ImportError as exc:
        raise ImportError("Pillow is required for PNG export. Install with 'pip install pillow'.") from exc

    if not bsps:
        raise ValueError("bsps must contain at least one BSP")

    bounds_min, bounds_max = _get_world_bounds_multi(bsps)

    span_x = max(bounds_max.x - bounds_min.x, 1e-6)
    span_z = max(bounds_max.z - bounds_min.z, 1e-6)
    if resolution <= 0:
        raise ValueError("resolution must be > 0")

    if span_x >= span_z:
        width = max(1, int(math.ceil(resolution)))
        height = max(1, int(math.ceil(resolution * (span_z / span_x))))
    else:
        height = max(1, int(math.ceil(resolution)))
        width = max(1, int(math.ceil(resolution * (span_x / span_z))))

    scale = min(
        (width - 2 * padding) / span_x,
        (height - 2 * padding) / span_z,
    )

    def to_px_x(x: float) -> float:
        return padding + (x - bounds_min.x) * scale

    def to_px_y(z: float) -> float:
        return padding + (bounds_max.z - z) * scale

    def hex_to_rgba(hex_color: str, alpha: float) -> tuple[int, int, int, int]:
        hex_color = hex_color.lstrip("#")
        if len(hex_color) != 6:
            return (0, 0, 0, int(255 * alpha))
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        a = int(max(0.0, min(1.0, alpha)) * 255)
        return (r, g, b, a)

    img = Image.new("RGBA", (width, height), hex_to_rgba(background, 1.0))
    draw = ImageDraw.Draw(img, "RGBA")
    pixels = img.load()

    if show_bounds:
        x0 = to_px_x(bounds_min.x)
        y0 = to_px_y(bounds_min.z)
        x1 = to_px_x(bounds_max.x)
        y1 = to_px_y(bounds_max.z)
        rect = [min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)]
        draw.rectangle(rect, outline=hex_to_rgba("#888888", 1.0), width=1)

    if txd_paths is None:
        txd_paths = [None] * len(bsps)
    elif isinstance(txd_paths, (str, Path)):
        txd_paths = [txd_paths] * len(bsps)
    elif len(txd_paths) != len(bsps):
        raise ValueError("txd_paths must be the same length as bsps")

    axis_colors = {
        "x": "#d84b4b",
        "z": "#3a78d4",
        "y": "#6b6b6b",
    }

    for bsp, txd_path in zip(bsps, txd_paths):
        segments = _collect_plane_segments_topdown(
            bsp.world_chunk.data,
            bounds_min,
            bounds_max,
        )

        if draw_geometry:
            stride = max(1, geometry_stride)
            tri_limit = max_triangles if (max_triangles is None or max_triangles > 0) else None
            mode = geometry_mode.lower().strip()
            valid_modes = {"wire", "fill", "both", "material", "material_wire", "texture", "texture_wire"}
            if mode not in valid_modes:
                raise ValueError(
                    "geometry_mode must be 'wire', 'fill', 'both', 'material', 'material_wire', 'texture', or 'texture_wire'"
                )
            geom_stroke = hex_to_rgba("#000000", geometry_opacity)
            geom_fill = hex_to_rgba("#000000", geometry_fill_opacity)
            materials = bsp.material_list.materials
            tex_by_name = {}
            tex_images = {}
            if mode in {"texture", "texture_wire"}:
                if txd_path is None:
                    raise ValueError("txd_path is required for texture rendering")
                import rwtxd

                txd = rwtxd.load(txd_path)
                for tex in txd.textures:
                    tex_by_name[tex.name.lower()] = tex

            sectors = _collect_atomic_sectors(bsp.world_chunk.data)
            tri_count = 0
            for sector in sectors:
                vertices = sector.vertices
                uvs = sector.uvs if sector.uvs else None
                colors = sector.colors if sector.colors else None
                for tri_index, tri in enumerate(sector.triangles):
                    if tri_index % stride != 0:
                        continue
                    if tri_limit is not None and tri_count >= tri_limit:
                        break

                    v1 = vertices[tri.vertex1]
                    v2 = vertices[tri.vertex2]
                    v3 = vertices[tri.vertex3]

                    x1 = to_px_x(v1.x)
                    y1 = to_px_y(v1.z)
                    x2 = to_px_x(v2.x)
                    y2 = to_px_y(v2.z)
                    x3 = to_px_x(v3.x)
                    y3 = to_px_y(v3.z)

                    def get_vertex_color(idx: int) -> tuple[int, int, int, int]:
                        if colors is not None and len(colors) == len(vertices):
                            c = colors[idx]
                            return (c.r, c.g, c.b, c.a)
                        return (255, 255, 255, 255)

                    def get_material_color(mat_index: int) -> tuple[int, int, int, int]:
                        if 0 <= mat_index < len(materials):
                            mc = materials[mat_index].color
                            return (mc.r, mc.g, mc.b, mc.a)
                        return (255, 255, 255, 255)

                    if mode in {"texture", "texture_wire"}:
                        if uvs is None:
                            draw.polygon([x1, y1, x2, y2, x3, y3], fill=geom_fill)
                        else:
                            mat_idx = sector.matListWindowBase + tri.materialIndex
                            tex_image = None
                            mat_color = get_material_color(mat_idx)
                            if 0 <= mat_idx < len(materials):
                                mat = materials[mat_idx]
                                if mat.isTextured and mat.texture and mat.texture.diffuseTextureName:
                                    tex_name = mat.texture.diffuseTextureName.lower()
                                    tex = tex_by_name.get(tex_name)
                                    if tex is not None:
                                        tex_image = tex_images.get(tex_name)
                                        if tex_image is None:
                                            rgba = rwtxd.decode(tex)
                                            tex_image = Image.frombytes("RGBA", (tex.width, tex.height), rgba)
                                            tex_images[tex_name] = tex_image

                            if tex_image is None:
                                vc1 = get_vertex_color(tri.vertex1)
                                vc2 = get_vertex_color(tri.vertex2)
                                vc3 = get_vertex_color(tri.vertex3)
                                vc_r = (vc1[0] + vc2[0] + vc3[0]) / 3.0
                                vc_g = (vc1[1] + vc2[1] + vc3[1]) / 3.0
                                vc_b = (vc1[2] + vc2[2] + vc3[2]) / 3.0
                                vc_a = (vc1[3] + vc2[3] + vc3[3]) / 3.0
                                fill_r = int((mat_color[0] * vc_r) / 255.0)
                                fill_g = int((mat_color[1] * vc_g) / 255.0)
                                fill_b = int((mat_color[2] * vc_b) / 255.0)
                                fill_a = (mat_color[3] / 255.0) * (vc_a / 255.0) * geometry_fill_opacity
                                fill_color = (fill_r, fill_g, fill_b, int(max(0.0, min(1.0, fill_a)) * 255))
                                draw.polygon([x1, y1, x2, y2, x3, y3], fill=fill_color)
                            else:
                                u1 = uvs[tri.vertex1].u
                                v1 = uvs[tri.vertex1].v
                                u2 = uvs[tri.vertex2].u
                                v2 = uvs[tri.vertex2].v
                                u3 = uvs[tri.vertex3].u
                                v3 = uvs[tri.vertex3].v
                                if texture_flip_v:
                                    v1 = 1.0 - v1
                                    v2 = 1.0 - v2
                                    v3 = 1.0 - v3

                                min_x = max(0, int(math.floor(min(x1, x2, x3))))
                                max_x = min(width - 1, int(math.ceil(max(x1, x2, x3))))
                                min_y = max(0, int(math.floor(min(y1, y2, y3))))
                                max_y = min(height - 1, int(math.ceil(max(y1, y2, y3))))

                                def edge(ax, ay, bx, by, cx, cy):
                                    return (cx - ax) * (by - ay) - (cy - ay) * (bx - ax)

                                area = edge(x1, y1, x2, y2, x3, y3)
                                if area != 0:
                                    inv_area = 1.0 / area
                                    tw, th = tex_image.size
                                    tex_pixels = tex_image.load()
                                    vc1 = get_vertex_color(tri.vertex1)
                                    vc2 = get_vertex_color(tri.vertex2)
                                    vc3 = get_vertex_color(tri.vertex3)
                                    for py in range(min_y, max_y + 1):
                                        for px in range(min_x, max_x + 1):
                                            w1 = edge(x2, y2, x3, y3, px, py)
                                            w2 = edge(x3, y3, x1, y1, px, py)
                                            w3 = edge(x1, y1, x2, y2, px, py)
                                            if (w1 >= 0 and w2 >= 0 and w3 >= 0) or (w1 <= 0 and w2 <= 0 and w3 <= 0):
                                                u = (w1 * u1 + w2 * u2 + w3 * u3) * inv_area
                                                v = (w1 * v1 + w2 * v2 + w3 * v3) * inv_area
                                                vc_r = (w1 * vc1[0] + w2 * vc2[0] + w3 * vc3[0]) * inv_area
                                                vc_g = (w1 * vc1[1] + w2 * vc2[1] + w3 * vc3[1]) * inv_area
                                                vc_b = (w1 * vc1[2] + w2 * vc2[2] + w3 * vc3[2]) * inv_area
                                                vc_a = (w1 * vc1[3] + w2 * vc2[3] + w3 * vc3[3]) * inv_area
                                                if texture_wrap:
                                                    u = u % 1.0
                                                    v = v % 1.0
                                                else:
                                                    u = max(0.0, min(1.0, u))
                                                    v = max(0.0, min(1.0, v))

                                                tx = min(tw - 1, max(0, int(u * (tw - 1))))
                                                ty = min(th - 1, max(0, int(v * (th - 1))))
                                                src = tex_pixels[tx, ty]
                                                if len(src) == 4:
                                                    sr, sg, sb, sa = src
                                                else:
                                                    sr, sg, sb = src
                                                    sa = 255
                                                sr = int(sr * (mat_color[0] / 255.0) * (vc_r / 255.0))
                                                sg = int(sg * (mat_color[1] / 255.0) * (vc_g / 255.0))
                                                sb = int(sb * (mat_color[2] / 255.0) * (vc_b / 255.0))
                                                sa = (sa / 255.0) * (mat_color[3] / 255.0) * (vc_a / 255.0) * geometry_fill_opacity
                                                if sa >= 0.999:
                                                    pixels[px, py] = (sr, sg, sb, 255)
                                                elif sa > 0.0:
                                                    dr, dg, db, da = pixels[px, py]
                                                    inv = 1.0 - sa
                                                    pixels[px, py] = (
                                                        int(sr * sa + dr * inv),
                                                        int(sg * sa + dg * inv),
                                                        int(sb * sa + db * inv),
                                                        255,
                                                    )
                    elif mode in {"material", "material_wire"}:
                        mat_idx = sector.matListWindowBase + tri.materialIndex
                        mat_color = get_material_color(mat_idx)
                        vc1 = get_vertex_color(tri.vertex1)
                        vc2 = get_vertex_color(tri.vertex2)
                        vc3 = get_vertex_color(tri.vertex3)
                        vc_r = (vc1[0] + vc2[0] + vc3[0]) / 3.0
                        vc_g = (vc1[1] + vc2[1] + vc3[1]) / 3.0
                        vc_b = (vc1[2] + vc2[2] + vc3[2]) / 3.0
                        vc_a = (vc1[3] + vc2[3] + vc3[3]) / 3.0
                        fill_r = int((mat_color[0] * vc_r) / 255.0)
                        fill_g = int((mat_color[1] * vc_g) / 255.0)
                        fill_b = int((mat_color[2] * vc_b) / 255.0)
                        fill_a = (mat_color[3] / 255.0) * (vc_a / 255.0) * geometry_fill_opacity
                        fill_color = (fill_r, fill_g, fill_b, int(max(0.0, min(1.0, fill_a)) * 255))
                        draw.polygon([x1, y1, x2, y2, x3, y3], fill=fill_color)
                    elif mode in {"fill", "both"}:
                        draw.polygon([x1, y1, x2, y2, x3, y3], fill=geom_fill)

                    if mode in {"wire", "both", "material_wire", "texture_wire"}:
                        draw.line([x1, y1, x2, y2], fill=geom_stroke, width=max(1, int(geometry_stroke_width)))
                        draw.line([x2, y2, x3, y3], fill=geom_stroke, width=max(1, int(geometry_stroke_width)))
                        draw.line([x3, y3, x1, y1], fill=geom_stroke, width=max(1, int(geometry_stroke_width)))

                    tri_count += 1
                if tri_limit is not None and tri_count >= tri_limit:
                    break

        cut_alpha = max(0.0, min(1.0, cut_opacity))
        for x0, z0, x1, z1, _depth, axis in segments:
            sx0 = to_px_x(x0)
            sy0 = to_px_y(z0)
            sx1 = to_px_x(x1)
            sy1 = to_px_y(z1)
            color = hex_to_rgba(axis_colors.get(axis, "#111111"), cut_alpha)
            draw.line([sx0, sy0, sx1, sy1], fill=color, width=max(1, int(stroke_width)))

    img.save(png_path)


def _export_mtl(
    mtl_path: Union[str, Path],
    material_list: RW_MaterialList,
    texture_prefix: str = "",
    mat_suffix: str = "",
):
    materials = material_list.materials

    with open(mtl_path, "w") as f:
        for i, mat in enumerate(materials):
            f.write(f"newmtl material_{i}_{mat_suffix}\n")

            # Color (convert 0-255 to 0-1)
            color = mat.color
            r = color.r / 255.0
            g = color.g / 255.0
            b = color.b / 255.0

            f.write(f"Kd {r:.6f} {g:.6f} {b:.6f}\n")
            f.write(f"Ka {mat.ambient:.6f} {mat.ambient:.6f} {mat.ambient:.6f}\n")
            f.write(f"Ks {mat.specular:.6f} {mat.specular:.6f} {mat.specular:.6f}\n")

            # Alpha
            a = color.a / 255.0
            if a < 1.0:
                f.write(f"d {a:.6f}\n")

            # Texture
            if mat.isTextured and mat.texture:
                tex_name = mat.texture.diffuseTextureName
                if tex_name:
                    f.write(f"map_Kd {texture_prefix}{tex_name}.png\n")

            f.write("\n")


def export_obj(
    bsp: RW_World,
    obj_filename: Union[str, Path],
    mtl_filename: Union[str, Path],
    collision_only_map=False,
    scale=1.0,
):
    """Export a BSP to an OBJ file

    Args:
        bsp: Parsed BSP to export
        filename: Path to the output .obj file
    """
    mat_suffix = str(random.randint(1000, 9999))

    sectors = _collect_atomic_sectors(bsp.world_chunk.data)
    if not sectors:
        raise ValueError("No atomic sectors found in BSP")

    _export_mtl(
        mtl_filename,
        bsp.material_list,
        texture_prefix="textures/",
        mat_suffix=mat_suffix,
    )

    world_struct_data = bsp.world_struct.data

    vertex_offset = 0
    uv_offset = 0

    with open(obj_filename, "w") as f:
        f.write("# Madagascar Modding Tools World BSP Export\n")
        f.write(f"# Vertices: {world_struct_data.numVertices}\n")
        f.write(f"# Triangles: {world_struct_data.numTriangles}\n")
        f.write(f"mtllib {mtl_filename}\n\n")

        for sector_idx, sector in enumerate(sectors):
            vertices = sector.vertices
            uvs = sector.uvs
            triangles = sector.triangles

            if not vertices or not triangles:
                continue

            f.write(f"# Sector {sector_idx}\n")
            f.write(f"g sector_{sector_idx}\n")

            # Write vertices (with colors if available)
            use_colors = bool(sector.colors) and len(sector.colors) == len(vertices)
            for i, v in enumerate(vertices):
                if use_colors:
                    c = sector.colors[i]
                    r = c.r / 255.0
                    g = c.g / 255.0
                    b = c.b / 255.0
                    a = c.a / 255.0
                    if a < 1.0:
                        print("ALPHAAA BELOW 1", c.a)
                    f.write(
                        f"v {v.x * scale:.6f} {v.y * scale:.6f} {v.z * scale:.6f} {r:.6f} {g:.6f} {b:.6f} {a:.6f}\n"
                    )
                else:
                    f.write(
                        f"v {v.x * scale:.6f} {v.y * scale:.6f} {v.z * scale:.6f}\n"
                    )

            # Write UVs (V flipped)
            for uv in uvs:
                f.write(f"vt {uv.u:.6f} {1.0 - uv.v:.6f}\n")

            # Group triangles by material
            mat_base = sector.matListWindowBase
            tris_by_mat = {}
            for tri in triangles:
                mat_idx = mat_base + tri.materialIndex
                tris_by_mat.setdefault(mat_idx, []).append(tri)

            # Write faces grouped by material
            for mat_idx in sorted(tris_by_mat.keys()):
                f.write(f"usemtl material_{mat_idx}_{mat_suffix}\n")
                for tri in tris_by_mat[mat_idx]:
                    v1 = tri.vertex1 + vertex_offset + 1
                    v2 = tri.vertex2 + vertex_offset + 1
                    v3 = tri.vertex3 + vertex_offset + 1

                    if uvs:
                        vt1 = tri.vertex1 + uv_offset + 1
                        vt2 = tri.vertex2 + uv_offset + 1
                        vt3 = tri.vertex3 + uv_offset + 1
                        f.write(f"f {v1}/{vt1} {v2}/{vt2} {v3}/{vt3}\n")
                    else:
                        f.write(f"f {v1} {v2} {v3}\n")

            vertex_offset += len(vertices)
            uv_offset += len(uvs)
            f.write("\n")

import bpy

from bpy.types import Node


def get_new_material_color(name: str, color: tuple | None = None):
    """Returns a basic material with a basic color"""

    if name in bpy.data.materials:
        return bpy.data.materials[name]

    new_mat = bpy.data.materials.new(name=name)
    new_mat.surface_render_method = "BLENDED"
    new_mat.use_transparency_overlap = False
    new_mat.use_nodes = True

    node: Node = new_mat.node_tree.nodes["Principled BSDF"]
    node.inputs["Alpha"].default_value = color[3] if color is not None else 1.0
    node.inputs["Base Color"].default_value = (
        (color[0], color[1], color[2], 1.0) if color is not None else (0.0, 0.0, 0.0, 1.0)
    )

    return new_mat

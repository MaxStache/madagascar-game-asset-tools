from bpy.types import Panel


class OBJECT_PT_bsp_properties(Panel):
    bl_label = "BSP Properties"
    bl_idname = "OBJECT_PT_bsp_properties"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"

    @classmethod
    def poll(cls, context):
        return context.object and context.object.type == 'MESH'

    def draw(self, context):
        layout = self.layout
        obj = context.object
        box = layout.box()
        box.label(text=f"Object: {obj.name}, is super cool!")

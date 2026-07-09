from .bsp_ot import IMPORT_OT_bsp
from .bsp_export_ot import EXPORT_OT_bsp

def import_bsp_func(self, context):
    self.layout.operator(IMPORT_OT_bsp.bl_idname, text="BSP (.bsp)")

def export_bsp_func(self, context):
    self.layout.operator(EXPORT_OT_bsp.bl_idname, text="BSP (.bsp)")

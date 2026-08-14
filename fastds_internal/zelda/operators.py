import bpy

from bpy.props import EnumProperty, StringProperty
from bpy.types import Operator, Context, UILayout

from ..utility import PluginError, get_enum_name
from .utility import get_scene_enum
from .zcb import Zelda_DoImportZCB, Zelda_DoExportZCB
from .nsbmd import Zelda_DoImportNSBMD, Zelda_DoExportNSBMD


class Zelda_SearchSceneOperator(Operator):
    bl_idname = "scene.zelda_search_scene"
    bl_label = "Choose Scene"
    bl_property = "scene"
    bl_options = {"REGISTER", "UNDO"}

    scene: EnumProperty(items=lambda self, context: get_scene_enum(context), default=1)
    mode: StringProperty()

    @staticmethod
    def draw_op(layout: UILayout, enum_value: str, mode: str):
        layout_search = layout.box().row()
        layout_search.operator(Zelda_SearchSceneOperator.bl_idname, icon="VIEWZOOM", text="").mode = mode

        try:
            text = get_enum_name(get_scene_enum(bpy.context), enum_value)
        except PluginError:
            text = "Unknown"

        layout_search.label(text=text)

    def execute(self, context: Context):
        match self.mode:
            case "import":
                context.scene.fastds.zelda.importers.zcb.scene = self.scene
            case "export":
                context.scene.fastds.zelda.exporters.zcb.scene = self.scene
            case _:
                raise PluginError("ERROR: unsupported operating mode.")

        context.region.tag_redraw()
        self.report({"INFO"}, "Selected: " + self.scene)
        return {"FINISHED"}

    def invoke(self, context: Context, event):
        context.window_manager.invoke_search_popup(self)
        return {"RUNNING_MODAL"}


zelda_ops_to_register = [
    Zelda_SearchSceneOperator,
    Zelda_DoImportZCB,
    Zelda_DoExportZCB,
    Zelda_DoImportNSBMD,
    Zelda_DoExportNSBMD,
]

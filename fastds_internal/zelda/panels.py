from bpy.types import Panel

from .properties import Zelda_SceneProperties, Zelda_MaterialProperties
from .nsbmd import Zelda_NSBMDPanel
from .zcb import Zelda_ZCBPanel
from .utility import Zelda_Panel


class Zelda_WorkspacePanel(Zelda_Panel):
    bl_idname = "ZELDA_PT_workspace"
    bl_label = "Workspace Settings"

    def draw(self, context):
        layout = self.layout
        assert layout is not None

        zelda: Zelda_SceneProperties = context.scene.fastds.zelda
        zelda.draw_props(layout.column())


class Zelda_MaterialPanel(Panel):
    bl_label = "Polygon Class Settings"
    bl_idname = "MATERIAL_PT_ZELDA_polyclass"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "material"
    bl_options = {"HIDE_HEADER"}

    @classmethod
    def poll(cls, context):
        return context.scene.fastds.game_mode == "Zelda" and context.material is not None

    def draw(self, context):
        layout = self.layout
        assert layout is not None

        zelda: Zelda_MaterialProperties = context.material.fastds.zelda
        zelda.draw_props(layout.column())


zelda_panels_to_register = [
    Zelda_WorkspacePanel,
    Zelda_ZCBPanel,
    Zelda_NSBMDPanel,
    Zelda_MaterialPanel,
]

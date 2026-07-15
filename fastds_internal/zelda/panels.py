from bpy.types import Panel

from .properties import Zelda_SceneProperties


class Zelda_Panel(Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "PH/ST"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        return context.scene.fastds.game_mode == "Zelda"


class Zelda_WorkspacePanel(Zelda_Panel):
    bl_idname = "ZELDA_PT_workspace"
    bl_label = "Workspace Settings"

    def draw(self, context):
        layout = self.layout
        assert layout is not None

        zelda: Zelda_SceneProperties = context.scene.fastds.zelda
        zelda.draw_props(layout)


zelda_panels_to_register = [
    Zelda_WorkspacePanel,
]

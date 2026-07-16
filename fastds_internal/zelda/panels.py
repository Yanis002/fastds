from .properties import Zelda_SceneProperties
from .zcb import Zelda_ZCBPanel
from .utility import Zelda_Panel


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
    Zelda_ZCBPanel,
]

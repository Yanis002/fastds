from bpy.types import Panel

from ..updater import addon_updater_ops
from .properties import FastDS_SceneProperties
from .zelda.panels import zelda_panels_to_register


class FastDS_Panel(Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "FastDS"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        return True


class FastDS_ToolsPanel(FastDS_Panel):
    bl_idname = "FASTDS_PT_tools"
    bl_label = "FastDS Tools"

    @classmethod
    def poll(cls, context):
        return True

    def draw(self, context):
        assert self.layout is not None
        self.layout.label(text="Empty for now.")
        addon_updater_ops.update_notice_box_ui(self, context)


class FastDS_SettingsPanel(FastDS_Panel):
    bl_idname = "FASTDS_PT_settings"
    bl_label = "FastDS Settings"

    @classmethod
    def poll(cls, context):
        return True

    def draw(self, context):
        layout = self.layout
        assert layout is not None

        fastds: FastDS_SceneProperties = context.scene.fastds
        fastds.draw_props(layout.column())


panels_to_register = [
    FastDS_ToolsPanel,
    FastDS_SettingsPanel,
] + zelda_panels_to_register

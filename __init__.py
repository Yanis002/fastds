import bpy

from bpy.utils import register_class, unregister_class

from .updater import addon_updater_ops
from .fastds_internal.panels import panels_to_register
from .fastds_internal.properties import props_to_register, ptr_to_register
from .fastds_internal.operators import ops_to_register

# info about add on
bl_info = {
    "name": "FastDS",
    "version": (0, 0, 1),
    "author": "Yanis002",
    "location": "3DView",
    "description": "Plugin for importing/exporting DS-related data (targetting DS Zelda games).",
    "category": "Import-Export",
    "blender": (5, 0, 0),
}


class FastDS_AddonPreferences(bpy.types.AddonPreferences, addon_updater_ops.AddonUpdaterPreferences):
    bl_idname = __package__

    def draw(self, context):
        addon_updater_ops.update_settings_ui(self, context)


@bpy.app.handlers.persistent
def after_load(_a, _b):
    # Doing some operations immediately on file load can crash blender in specific situations,
    # so delay the post-load code execution.
    # (note if register() is called without a delay the function just runs immediately, so we need any non-zero delay)
    bpy.app.timers.register(after_load_impl, first_interval=0.001)


def after_load_impl():
    pass


to_register = panels_to_register + props_to_register + ops_to_register

# called on add-on enabling
# register operators and panels here
# append menu layout drawing function to an existing window
def register():
    if bpy.app.version < (3, 2, 0):
        msg = "\n".join(
            (
                "This version of FastDS does not support Blender 3.1.x and earlier Blender versions.",
                "Your Blender version is: " + ".".join(str(i) for i in bpy.app.version),
                "Please upgrade Blender to 3.2.0 or above.",
            )
        )
        print(msg)
        unsupported_exc = Exception("\n\n" + msg)
        raise unsupported_exc

    # Register addon updater first,
    # this way if a broken version fails to register the user can still pick another version.
    register_class(FastDS_AddonPreferences)
    addon_updater_ops.register(bl_info)

    for cls in to_register:
        register_class(cls)

    for infos in ptr_to_register:
        setattr(getattr(bpy.types, infos.target_type), infos.name, bpy.props.PointerProperty(type=infos.target_class, name=infos.desc))

    bpy.app.handlers.load_post.append(after_load)


# called on add-on disabling
def unregister():
    del bpy.types.Scene.fastds

    for cls in to_register:
        unregister_class(cls)

    bpy.app.handlers.load_post.remove(after_load)

    addon_updater_ops.unregister()
    unregister_class(FastDS_AddonPreferences)

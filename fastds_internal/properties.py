from bpy.types import PropertyGroup, UILayout
from bpy.props import EnumProperty, PointerProperty

from .zelda.properties import Zelda_SceneProperties, Zelda_MaterialProperties, zelda_props_to_register
from .utility import prop_split, PointerPropertyRegisterInfo

# game mode picker
enum_game_mode = [
    ("Zelda", "PH/ST", "Zelda PH/ST", 0),
]


class FastDS_SceneProperties(PropertyGroup):
    """Properties in scene.fastds (bpy.types.Scene)"""

    game_mode: EnumProperty(items=enum_game_mode)
    zelda: PointerProperty(name="Zelda Scene Properties", type=Zelda_SceneProperties)

    def draw_props(self, layout: UILayout):
        prop_split(layout, self, "game_mode", "Game Mode")


class FastDS_MaterialProperties(PropertyGroup):
    """Properties in material.fastds (bpy.types.Material)"""

    zelda: PointerProperty(name="Zelda Material Properties", type=Zelda_MaterialProperties)

props_to_register = zelda_props_to_register + [
    FastDS_SceneProperties,
    FastDS_MaterialProperties,
]

ptr_to_register = [
    PointerPropertyRegisterInfo("Scene", FastDS_SceneProperties, "fastds", "FastDS Scene Properties"),
    PointerPropertyRegisterInfo("Material", FastDS_MaterialProperties, "fastds", "FastDS Material Properties"),
]

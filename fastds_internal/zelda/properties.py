from bpy.types import PropertyGroup, UILayout
from bpy.props import EnumProperty

from ..utility import prop_split

enum_zelda_games = [
    ("PH", "PH", "Phantom Hourglass", 0),
    ("ST", "ST", "Spirit Tracks", 1),
]


class Zelda_SceneProperties(PropertyGroup):
    # bpy.context.scene.fast64.zelda.

    game: EnumProperty(items=enum_zelda_games)

    def draw_props(self, layout: UILayout):
        prop_split(layout, self, "game", "Game")


zelda_props_to_register = [
    Zelda_SceneProperties,
]

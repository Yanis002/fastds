from bpy.types import PropertyGroup, UILayout
from bpy.props import EnumProperty, PointerProperty

from ..utility import prop_split
from .zcb import Zelda_ZCBImportSettings, Zelda_ZCBExportSettings, Zelda_PolyClassProperties


class Zelda_ImportProperties(PropertyGroup):
    zcb: PointerProperty(type=Zelda_ZCBImportSettings)


class Zelda_ExportProperties(PropertyGroup):
    zcb: PointerProperty(type=Zelda_ZCBExportSettings)


enum_zelda_games = [
    ("PH", "PH", "Phantom Hourglass", 0),
    ("ST", "ST", "Spirit Tracks", 1),
]


class Zelda_SceneProperties(PropertyGroup):
    # bpy.context.scene.fastds.zelda.

    game: EnumProperty(items=enum_zelda_games)
    importers: PointerProperty(type=Zelda_ImportProperties)
    exporters: PointerProperty(type=Zelda_ExportProperties)

    def draw_props(self, layout: UILayout):
        prop_split(layout, self, "game", "Game")


class Zelda_MaterialProperties(PropertyGroup):
    # material.fastds.zelda.

    polyclass: PointerProperty(type=Zelda_PolyClassProperties)

    def draw_props(self, layout: UILayout):
        polyclass: Zelda_PolyClassProperties = self.polyclass
        polyclass.draw_props(layout)


zelda_props_to_register = [
    Zelda_ZCBImportSettings,
    Zelda_ZCBExportSettings,
    Zelda_ImportProperties,
    Zelda_ExportProperties,
    Zelda_PolyClassProperties,
    Zelda_SceneProperties,
    Zelda_MaterialProperties,
]

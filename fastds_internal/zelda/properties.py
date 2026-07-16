from bpy.types import PropertyGroup, UILayout, Context
from bpy.props import EnumProperty, PointerProperty, StringProperty, BoolProperty

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

enum_ph_versions = [
    ("eur", "EUR", "EUR", 0),
    ("usa", "USA", "USA", 1),
]

enum_st_versions = [
    ("eur", "EUR", "EUR", 0),
    ("jp", "JP", "JP", 1),
]


def get_version_enum(context: Context | None):
    assert context is not None, "unexpected error"
    return enum_ph_versions if context.scene.fastds.zelda.game == "PH" else enum_st_versions


class Zelda_SceneProperties(PropertyGroup):
    # bpy.context.scene.fastds.zelda.

    game: EnumProperty(items=enum_zelda_games)
    version: EnumProperty(items=lambda self, context: get_version_enum(context), default=0)
    importers: PointerProperty(type=Zelda_ImportProperties)
    exporters: PointerProperty(type=Zelda_ExportProperties)
    decomp_path: StringProperty(subtype="DIR_PATH", description="Path to the decomp project, can be left empty.")
    extract_path: StringProperty(subtype="DIR_PATH", description="Path to the extract folder, can be left empty.")
    use_decomp_extract: BoolProperty(default=True, description="Use decomp path to get the extracted folder path.")

    def draw_props(self, layout: UILayout):
        prop_split(layout, self, "game", "Game")
        layout.prop(self, "use_decomp_extract", text="Use Decomp Extract")

        if self.use_decomp_extract:
            prop_split(layout, self, "decomp_path", "Decomp Path")
            prop_split(layout, self, "version", "Version")
        else:
            prop_split(layout, self, "extract_path", "Extract Path")


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

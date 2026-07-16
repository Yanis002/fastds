import bpy

from bpy.types import Panel, Context
from pathlib import Path
from typing import TYPE_CHECKING

from ..utility import PluginError
from .constants import enum_scenes_ph, enum_scenes_st

if TYPE_CHECKING:
    from .properties import Zelda_SceneProperties


class Zelda_Panel(Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "PH/ST"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        return context.scene.fastds.game_mode == "Zelda"


def get_scene_enum(context: Context | None):
    assert context is not None, "unexpected error"
    return enum_scenes_ph if context.scene.fastds.zelda.game == "PH" else enum_scenes_st


def get_decomp_path() -> Path:
    zelda: "Zelda_SceneProperties" = bpy.context.scene.fastds.zelda

    decomp_path = Path(zelda.decomp_path).resolve()

    if not decomp_path.exists():
        raise PluginError("ERROR: the decomp path is invalid.")

    return decomp_path


def get_extract_dir(strictly_decomp: bool = False) -> Path | None:
    zelda: "Zelda_SceneProperties" = bpy.context.scene.fastds.zelda

    if zelda.use_decomp_extract:
        return get_decomp_path() / "extract" / zelda.version

    if strictly_decomp:
        return None

    extract_path = Path(zelda.extract_path).resolve()

    if not extract_path.exists():
        raise PluginError("ERROR: the extract path is invalid.")

    return extract_path

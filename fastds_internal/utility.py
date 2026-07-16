import math

from typing import Any
from bpy.types import UILayout
from dataclasses import dataclass
from mathutils import Quaternion


class PluginError(Exception):
    # arguments for exception processing
    exc_halt = "exc_halt"
    exc_warn = "exc_warn"

    """
    because exceptions generally go through multiple funcs
    and layers, the easiest way to check if we have an exception
    of a certain type is to check for our input string
    """

    @classmethod
    def check_exc_warn(self, exc):
        for arg in exc.args:
            if type(arg) is str and self.exc_warn in arg:
                return True
        return False


@dataclass
class PointerPropertyRegisterInfo:
    target_type: str
    target_class: Any
    name: str
    desc: str


@dataclass
class VecFx32:
    x: int
    y: int
    z: int


# default indentation to use when writing to decomp files
indent = " " * 4


y_up_to_z_up = Quaternion((1, 0, 0), math.radians(90.0))
yUpToZUp = y_up_to_z_up.to_matrix().to_4x4()


def prop_split(layout: UILayout, data: Any, property: str, name: str, **prop_kwargs):
    split = layout.split(factor=0.5)
    split.label(text=name)
    split.prop(data, property, text="", **prop_kwargs)

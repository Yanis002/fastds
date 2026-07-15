from typing import Any
from bpy.types import UILayout
from dataclasses import dataclass


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


# default indentation to use when writing to decomp files
indent = " " * 4


def prop_split(layout: UILayout, data: Any, property: str, name: str, **prop_kwargs):
    split = layout.split(factor=0.5)
    split.label(text=name)
    split.prop(data, property, text="", **prop_kwargs)

import math

from pathlib import Path
from typing import Any
from bpy.types import UILayout
from dataclasses import dataclass
from mathutils import Quaternion

from ..ndspy import lz10 as LZSS, narc


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


class BinaryFile:
    def __init__(self, path: Path | None, raw_data: bytes | None):
        self.path = path.resolve() if path is not None else None

        if self.path is not None:
            if not self.path.exists():
                raise PluginError("ERROR: invalid file path.")

            self.raw_data = self.path.read_bytes()
        elif raw_data is not None:
            self.raw_data = raw_data
        else:
            raise PluginError("ERROR: unexpected issue occurred.")


# default indentation to use when writing to decomp files
indent = " " * 4


y_up_to_z_up = Quaternion((1, 0, 0), math.radians(90.0))
yUpToZUp = y_up_to_z_up.to_matrix().to_4x4()


def prop_split(layout: UILayout, data: Any, property: str, name: str, **prop_kwargs):
    split = layout.split(factor=0.5)
    split.label(text=name)
    split.prop(data, property, text="", **prop_kwargs)


def get_enum_name(items, value):
    for enum_tuple in items:
        if enum_tuple[0] == value:
            return enum_tuple[1]
    raise PluginError("Could not find enum value " + str(value))


def get_lzss_file(lzss_path: Path, magic: bytes) -> tuple[bytes, narc.NARC, bytes, str]:
    """
    Attempts to fetch a specific file from a LZSS archive (this assumes it's a compressed NARC archive)

    Parameters:
        - `lzss_path`: `pathlib.Path` to the LZSS archive
        - `magic`: the expected first bytes of the file's identifier (so we can know when we hit the right file)

    Returns (in this order):
        - the LZSS file as bytes
        - the NARC itself
        - the requested file as bytes
        - the filename as a string
    """
    assert lzss_path.exists()

    lzss_bytes = LZSS.decompressFromFile(lzss_path)
    archive = narc.NARC(lzss_bytes)

    found_file = None
    filename = None
    for i, file in enumerate(archive.files):
        if file.startswith(magic):
            found_file = file
            filename = str(archive.filenames[i])
            break

    if found_file is not None and filename is not None:
        return lzss_bytes, archive, found_file, filename

    raise PluginError("ERROR: unexpected result")


def validate_binary_path(layout: UILayout, path_or_data: Path | bytes, magic: bytes, kind: str):
    """
    Makes sure a path to a binary file or its data directly is valid

    Parameters:
        - `layout`: where to draw the label
        - `path_or_data`: can be a `pathlib.Path` or `bytes`, if it's a path then it will try to find the wanted file
        - `magic`: the expected first bytes of the file's identifier
        - `kind`: the file's type

    Returns:
        - `True` if the data is valid
        - `False` if not
    """

    if isinstance(path_or_data, Path):
        if len(str(path_or_data)) == 0 or not path_or_data.exists() or path_or_data.is_dir():
            layout.label(text="This path doesn't exist.", icon="ERROR")
            return False

        # .zcb, .nsbmd, etc...
        if path_or_data.suffix.lower() == f".{kind.lower()}":
            data = path_or_data.read_bytes()
        else:
            # if it's not the file directly it means it's most likely an archive
            # note: it's technically useless to set `data` since the getter would raise an error anyway but whatever
            lzss_bytes, archive, data, filename = get_lzss_file(path_or_data, magic)
    else:
        data = path_or_data

    if data[0x00 : len(magic)] != magic:
        layout.label(text=f"Invalid {kind} file.", icon="ERROR")
        return False

    return True


def int_to_fx32(value: int) -> int:
    return value << 12


def float_to_fx32(value: float) -> int:
    return round((value * 0x2000 + 1) / 2)


def fx32_to_int(value: int) -> int:
    return value >> 12


def fx32_to_float(value: int) -> float:
    return ((value * 2) - 1) / 0x2000

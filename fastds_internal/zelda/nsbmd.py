import struct

from pathlib import Path
from bpy.props import StringProperty
from bpy.types import PropertyGroup, UILayout, Operator

from .utility import Zelda_Panel
from ..utility import PluginError, BinaryFile, prop_split, validate_binary_path
from ..gfx import G3d_NameList, G3d_Model


# based on ST decomp, shouldn't be any different on PH
class NSBMDHeader:
    """Definition of the NSBMD header"""

    fmt = "<4sHHIHHII"

    def __init__(self, raw_data: bytes, has_tex: bool):
        self.raw_data = raw_data

        (
            raw_type,
            raw_byte_order,
            raw_version,
            raw_size_file,
            raw_size_header,
            raw_num_sections,
            raw_offset_MDL0,
            raw_offset_TEX0,
        ) = struct.unpack(NSBMDHeader.fmt, self.raw_data)

        self.has_tex = has_tex
        self.type: str = raw_type.decode("utf-8")  # always 'BMD0'
        self.byte_order: int = raw_byte_order  # 0xFEFF
        self.version: int = raw_version  # always 2
        self.size_file: int = raw_size_file
        self.size_header: int = raw_size_header  # excluding the section offsets (always 0x10)
        self.num_sections: int = raw_num_sections  # 1 for 'MDL0' or 2 for 'MDL0' + 'TEX0'
        self.offset_MDL0: int = raw_offset_MDL0  # from the beginning of the file
        self.offset_TEX0: int = raw_offset_TEX0 if self.has_tex else None  # from the beginning of the file

    def is_valid(self):
        has_tex = self.num_sections == 2
        return self.type == "BMD0" and self.byte_order == 0xFEFF and self.version == 0x02 and self.has_tex == has_tex


class NSBMDModels:
    fmt = "<4sI"

    def __init__(self, raw_data: bytes):
        self.raw_data = raw_data

        raw_magic, raw_size = struct.unpack(NSBMDModels.fmt, self.raw_data[0x00:0x08])

        self.magic: str = raw_magic.decode("utf-8")
        self.section_size: int = raw_size
        self.list = G3d_NameList(self.raw_data[0x08:], self.raw_data, G3d_Model)

    def is_valid(self):
        return self.magic == "MDL0"


class NSBMDFile(BinaryFile):
    def __init__(self, path: Path | None, raw_data: bytes | None):
        super().__init__(path, raw_data)

        self.header = NSBMDHeader(self.raw_data[0x00:0x18], b"TEX0" in self.raw_data)

        if not self.header.is_valid():
            raise PluginError(f"ERROR: this file is not valid. ({repr(self.path)})")

        self.models = NSBMDModels(self.raw_data[self.header.offset_MDL0 :])
        self.textures = None

        if self.header.offset_TEX0 is not None:
            self.textures = None  # TBD

        pass


class Zelda_DoImportNSBMD(Operator):
    bl_idname = "scene.zelda_nsbmd_import"
    bl_label = "Import NSBMD"
    bl_options = {"REGISTER", "UNDO", "PRESET"}

    path: StringProperty(default="None")

    def execute(self, context):
        path = Path(self.path).resolve()
        assert path.exists(), "unexpected error"
        NSBMDFile(path, path.read_bytes())

        self.report({"INFO"}, "Not implemented yet.")
        return {"FINISHED"}


class Zelda_DoExportNSBMD(Operator):
    bl_idname = "scene.zelda_nsbmd_export"
    bl_label = "Export NSBMD"
    bl_options = {"REGISTER", "UNDO", "PRESET"}

    path: StringProperty(default="None")

    def execute(self, context):
        self.report({"INFO"}, "Not implemented yet.")
        return {"FINISHED"}


class Zelda_NSBMDImportSettings(PropertyGroup):
    path: StringProperty(description="Path to the NSBMD file", subtype="FILE_PATH")

    def draw_props(self, layout: UILayout):
        layout = layout.box()
        layout.box().label(text="Import Settings")

        prop_split(layout, self, "path", "Path")

        layout_op = layout.column()
        import_op = layout_op.operator(Zelda_DoImportNSBMD.bl_idname)
        import_op.path = self.path
        layout_op.enabled = validate_binary_path(layout, Path(self.path).resolve(), b"BMD0", "NSBMD")


class Zelda_NSBMDExportSettings(PropertyGroup):
    path: StringProperty(description="Path to the NSBMD file", subtype="FILE_PATH")

    def draw_props(self, layout: UILayout):
        layout = layout.box()
        layout.box().label(text="Export Settings")

        prop_split(layout, self, "path", "Path")

        export_op = layout.operator(Zelda_DoExportNSBMD.bl_idname)
        export_op.path = self.path


class Zelda_NSBMDPanel(Zelda_Panel):
    bl_idname = "ZELDA_PT_nsbmd"
    bl_label = "Model (.nsbmd)"

    def draw(self, context):
        layout = self.layout
        assert layout is not None

        nsbmd_import: Zelda_NSBMDImportSettings = context.scene.fastds.zelda.importers.nsbmd
        nsbmd_import.draw_props(layout.column())

        nsbmd_export: Zelda_NSBMDExportSettings = context.scene.fastds.zelda.exporters.nsbmd
        nsbmd_export.draw_props(layout.column())

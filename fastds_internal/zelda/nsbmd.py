from typing import Any
from blf import size
import struct

from dataclasses import dataclass
from pathlib import Path
from bpy.props import StringProperty
from bpy.types import PropertyGroup, UILayout, Operator

from .utility import Zelda_Panel
from ..utility import PluginError, BinaryFile, prop_split, validate_binary_path, fx32_to_float


# based on ST decomp, shouldn't be any different on PH
class NSBMDHeader:
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


class G3d_NameList_Header:
    fmt = "<HHI"

    def __init__(self, raw_data: bytes, max: int):
        self.raw_data = raw_data

        raw_element_size, raw_data_section_size, read_data = struct.unpack(G3d_NameList_Header.fmt, self.raw_data[0x00:0x08])

        self.element_size: int = raw_element_size
        self.data_section_size: int = raw_data_section_size
        self.data: int = read_data
        self.names: list[str] = []

        offset = 0x00
        for i in range(max):
            offset = (i + 1) * 0x08
            self.names.append(struct.unpack("16s", self.raw_data[offset : offset + 0x10])[0].decode("utf-8"))

        self.offset_first = offset + 0x10


class G3d_NameList:
    fmt = "<BBHHH"

    def __init__(self, raw_data: bytes):
        self.raw_data = raw_data

        raw_dummy, raw_num_elmnts, raw_size, raw_dummy2, raw_ofs_header = struct.unpack(
            G3d_NameList.fmt, self.raw_data[0x00:0x08]
        )

        self.dummy: int = raw_dummy
        self.num_elmnts: int = raw_num_elmnts  # number of elements
        self.size: int = raw_size  # size of this NameList in bytes
        self.dummy2: int = raw_dummy2
        self.ofs_header: int = raw_ofs_header  # offset to the G3d_NameList_Header
        self.entries = []  # variable size

        self.header = G3d_NameList_Header(self.raw_data[self.ofs_header :], self.num_elmnts)

    def init_entries(self, cls: Any):
        for i in range(self.num_elmnts):
            self.entries.append(cls(self.raw_data[self.ofs_header + self.header.offset_first :]))


class G3d_Model_14:
    fmt = "<BBBBBBBBiiHHHH" + "hhh" + "hhh" + "II"

    def __init__(self, raw_data: bytes):
        self.raw_data = raw_data

        (
            raw_unk_14,
            raw_scaling_handler,
            raw_texture_handler,
            raw_num_bones,
            raw_num_mat,
            raw_num_mesh,
            raw_unk_1A,
            raw_unk_1B,
            raw_up_scale,
            raw_down_scale,
            raw_num_vertex,
            raw_num_polygon,
            raw_num_triangle,
            raw_num_quad,
            raw_box_min_1,
            raw_box_min_2,
            raw_box_min_3,
            raw_box_max_1,
            raw_box_max_2,
            raw_box_max_3,
            raw_unk_38,
            raw_unk_3C,
        ) = struct.unpack(G3d_Model_14.fmt, self.raw_data)

        self.unk_14: int = raw_unk_14
        self.scaling_handler: int = raw_scaling_handler  # Determines which of the G3d_gScaleHandlers to use for this model
        self.texture_handler: int = raw_texture_handler  # Determines which of the G3d_gTextureHandlers to use for this model
        self.num_bones: int = raw_num_bones  # number of nodes
        self.num_mat: int = raw_num_mat  # number of materials
        self.num_mesh: int = raw_num_mesh  # number of meshes
        self.unk_1A: int = raw_unk_1A
        self.unk_1B: int = raw_unk_1B
        self.up_scale: int = fx32_to_float(raw_up_scale)
        self.down_scale: int = fx32_to_float(raw_down_scale)
        self.num_vertex: int = raw_num_vertex  # number of vertices
        self.num_polygon: int = raw_num_polygon  # number of polygons
        self.num_triangle: int = raw_num_triangle  # number of triangles
        self.num_quad: int = raw_num_quad  # number of quads
        self.bounding_box_min: list[int] = [raw_box_min_1, raw_box_min_2, raw_box_min_3]  # bounding box lower vertex
        self.bounding_box_max: list[int] = [raw_box_max_1, raw_box_max_2, raw_box_max_3]  # bounding box upper vertex
        self.unk_38: int = raw_unk_38
        self.unk_3C: int = raw_unk_3C


class G3d_Model:
    fmt = "<IIIII"

    def __init__(self, raw_data: bytes):
        self.raw_data = raw_data

        (
            raw_size,
            raw_off_sbc,
            raw_off_mat,
            raw_off_mesh,
            raw_off_invbmtx,
        ) = struct.unpack(G3d_Model.fmt, self.raw_data[0x00:0x14])

        self.size: int = raw_size  # size of the model in bytes
        self.off_sbc: int = raw_off_sbc  # offset of the SBC commands list (does addr + value instead of file offset + value)
        self.off_mat: int = raw_off_mat  # offset of the material list (does addr + value instead of file offset + value)
        self.off_mesh: int = raw_off_mesh  # offset of the mesh list (does addr + value instead of file offset + value)
        self.off_invbmtx: int = raw_off_invbmtx  # offset of the InvBindMatrix list
        self.unk_14 = G3d_Model_14(self.raw_data[0x14:0x40])
        self.bone_list = None  # bone list, TODO


class NSBMDModels:
    fmt = "<4sI"

    def __init__(self, raw_data: bytes):
        self.raw_data = raw_data

        raw_magic, raw_size = struct.unpack(NSBMDModels.fmt, self.raw_data[0x00:0x08])

        self.magic: str = raw_magic.decode("utf-8")
        self.section_size: int = raw_size
        self.list = G3d_NameList(self.raw_data[0x08:])
        self.list.init_entries(G3d_Model)

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

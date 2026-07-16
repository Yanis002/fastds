import struct
import bpy

from bpy.types import PropertyGroup, UILayout, Operator
from bpy.props import StringProperty
from pathlib import Path
from mathutils import Vector
from dataclasses import dataclass

from .utility import Zelda_Panel
from ..utility import PluginError, VecFx32, prop_split, yUpToZUp


class ZCBHeader:
    fmt = "<4s4sII"

    def __init__(self, raw_data: bytes):
        self.raw_data = raw_data

        raw_magic, raw_type, raw_size, raw_num_sections = struct.unpack(ZCBHeader.fmt, self.raw_data)

        self.magic: str = raw_magic[::-1].decode("utf-8")
        self.type: str = raw_type[::-1].decode("utf-8")
        self.size: int = raw_size
        self.num_sections: int = raw_num_sections

    def is_valid(self):
        return self.magic == "MCLB" and self.type == "ZCB1"


class ZCBSectionHeader:
    fmt = "<4sIHBB"

    def __init__(self, raw_data: bytes):
        self.raw_data = raw_data

        raw_type, raw_size, raw_num_entries, raw_unk_0A, raw_unk_0B = struct.unpack(ZCBSectionHeader.fmt, self.raw_data)

        self.type: str = raw_type[::-1].decode("utf-8")
        self.size: int = raw_size
        self.num_entries: int = raw_num_entries
        self.unk_0A: int = raw_unk_0A
        self.unk_0B: int = raw_unk_0B


class ZCBVertices:
    fmt = "<iii"

    def __init__(self, raw_data: bytes, header: ZCBSectionHeader):
        self.header = header
        self.raw_data = raw_data[0x0C : self.header.size]
        self.entries: list[Vector] = []

        offset = 0x00
        for _ in range(header.num_entries):
            x, y, z = struct.unpack(ZCBVertices.fmt, self.raw_data[offset : offset + 0x0C])
            pos = VecFx32(round(x / 4096), round(y / 4096), round(z / 4096))
            vertex = [pos.x, pos.y, pos.z]
            position = yUpToZUp @ Vector(vertex)
            self.entries.append(position)

            offset += 0x0C  # sizeof(VecFx32)

    def is_valid(self):
        return self.header.type == "VTXB"


class ZCBNormals:
    fmt = "<HHH"

    @dataclass
    class Entry:
        unk_00: int
        unk_02: int
        unk_04: int

    def __init__(self, raw_data: bytes, header: ZCBSectionHeader):
        self.header = header
        self.raw_data = raw_data[0x0C : self.header.size]
        self.entries: list[ZCBNormals.Entry] = []

        offset = 0x00
        for _ in range(header.num_entries):
            unk_00, unk_02, unk_04 = struct.unpack(ZCBNormals.fmt, self.raw_data[offset : offset + 0x06])
            self.entries.append(ZCBNormals.Entry(unk_00, unk_02, unk_04))
            offset += 0x06

    def is_valid(self):
        return self.header.type == "NRMB"


class ZCBPolyClasses:
    fmt = "<I"

    def __init__(self, raw_data: bytes, header: ZCBSectionHeader):
        self.header = header
        self.raw_data = raw_data[0x0C : self.header.size]
        self.entries: list[int] = []

        offset = 0x00
        for _ in range(header.num_entries):
            entry: int = struct.unpack(ZCBPolyClasses.fmt, self.raw_data[offset : offset + 0x04])
            self.entries.append(entry)
            offset += 0x04

    def is_valid(self):
        return self.header.type == "PCLB"


class ZCBTriangles:
    fmt_ph = "<HHHH"
    fmt_st = "<HHHHHHHH"

    @dataclass
    class Entry:
        vtx_indices: list[int]
        index_polyclass: int

    def __init__(self, raw_data: bytes, header: ZCBSectionHeader):
        self.header = header
        self.raw_data = raw_data[0x0C : self.header.size]
        self.entries: list[ZCBTriangles.Entry] = []

        if bpy.context.scene.fastds.zelda.game == "PH":
            entry_size = 0x08
        else:
            entry_size = 0x10

        offset = 0x00
        for _ in range(header.num_entries):
            if bpy.context.scene.fastds.zelda.game == "PH":
                unk_08 = unk_0A = unk_0C = None
                x, y, z, polyclass = struct.unpack(ZCBTriangles.fmt_ph, self.raw_data[offset : offset + entry_size])
            else:
                x, y, z, polyclass, unk_08, unk_0A, unk_0C, unk_0E = struct.unpack(
                    ZCBTriangles.fmt_st, self.raw_data[offset : offset + entry_size]
                )

            self.entries.append(ZCBTriangles.Entry([x, y, z], polyclass))
            offset += entry_size

    def is_valid(self):
        return self.header.type == "TRIB"

    def get_indices(self):
        indices = []

        for entry in self.entries:
            indices.append(entry.vtx_indices)

        return indices


# TODO
class ZCBGrid:
    fmt = "<"

    def __init__(self, raw_data: bytes, header: ZCBSectionHeader):
        self.header = header
        self.raw_data = raw_data[0x0C : self.header.size]

    def is_valid(self):
        return self.header.type == "GRDB"


class ZCBFile:
    fmt_header = "<4s4sII"

    def __init__(self, path: Path):
        self.path = path.resolve()

        if not self.path.exists():
            raise PluginError("ERROR: invalid ZCB file path.")

        self.raw_data = self.path.read_bytes()
        self.header = ZCBHeader(self.raw_data[0x00:0x10])

        if not self.header.is_valid():
            raise PluginError(f"ERROR: this file is not valid. ({repr(self.path)})")

        self.vertices: ZCBVertices | None = None
        self.normals: ZCBNormals | None = None
        self.polyclasses: ZCBPolyClasses | None = None
        self.triangles: ZCBTriangles | None = None
        self.grid: ZCBGrid | None = None

        offset = 0x20  # file header size
        for _ in range(self.header.num_sections):
            header = ZCBSectionHeader(self.raw_data[offset : offset + 0x0C])
            raw_data = self.raw_data[offset : offset + header.size]

            match header.type:
                case "VTXB":
                    self.vertices = ZCBVertices(raw_data, header)
                case "NRMB":
                    self.normals = ZCBNormals(raw_data, header)
                case "PCLB":
                    self.polyclasses = ZCBPolyClasses(raw_data, header)
                case "TRIB":
                    self.triangles = ZCBTriangles(raw_data, header)
                case "GRDB":
                    self.grid = ZCBGrid(raw_data, header)
                case _:
                    print(f"WARNING: ignoring unknown section '{header.type}'")

            offset += header.size

        if not self.is_valid():
            raise PluginError("ERROR: file parsing error")

    def is_valid(self):
        if bpy.context.scene.fastds.zelda.game == "PH":
            return (
                self.vertices is not None
                and self.polyclasses is not None
                and self.triangles is not None
                and self.grid is not None
            )
        else:
            return (
                self.vertices is not None
                and self.normals is not None
                and self.polyclasses is not None
                and self.triangles is not None
                and self.grid is not None
            )


class Zelda_DoImportZCB(Operator):
    bl_idname = "scene.zelda_zcb_import"
    bl_label = "Import ZCB"
    bl_options = {"REGISTER", "UNDO", "PRESET"}

    path: StringProperty()

    def execute(self, context):
        file = ZCBFile(Path(self.path))

        col_name = f"{file.path.stem}_collision"
        new_mesh = bpy.data.meshes.new(col_name)
        new_obj = bpy.data.objects.new(col_name, new_mesh)
        bpy.context.scene.collection.objects.link(new_obj)
        new_mesh.from_pydata(vertices=file.vertices.entries, edges=[], faces=file.triangles.get_indices())

        self.report({"INFO"}, "Success!")
        return {"FINISHED"}


class Zelda_DoExportZCB(Operator):
    bl_idname = "scene.zelda_zcb_export"
    bl_label = "Export ZCB"
    bl_options = {"REGISTER", "UNDO", "PRESET"}

    path: StringProperty()

    def execute(self, context):
        self.report({"INFO"}, "Not implemented yet.")
        return {"FINISHED"}


class Zelda_ZCBImportSettings(PropertyGroup):
    path: StringProperty(description="Path to the ZCB file", subtype="FILE_PATH")

    def draw_props(self, layout: UILayout):
        layout = layout.box()
        layout.box().label(text="Import Settings")

        prop_split(layout, self, "path", "Path")

        path = Path(self.path).resolve()

        if not path.exists():
            layout.label(text="This path doesn't exist.", icon="ERROR")
        elif len(self.path) > 0 and path.read_bytes()[0x00:0x08] != b"BLCM1BCZ":
            layout.label(text="Invalid ZCB file.", icon="ERROR")

        import_op = layout.operator(Zelda_DoImportZCB.bl_idname)
        import_op.path = self.path


class Zelda_ZCBExportSettings(PropertyGroup):
    path: StringProperty(description="Path to the ZCB file", subtype="FILE_PATH")

    def draw_props(self, layout: UILayout):
        layout = layout.box()
        layout.enabled = False
        layout.box().label(text="Export Settings")

        prop_split(layout, self, "path", "Path")

        export_op = layout.operator(Zelda_DoExportZCB.bl_idname)
        export_op.path = self.path


class Zelda_ZCBPanel(Zelda_Panel):
    bl_idname = "ZELDA_PT_zcb"
    bl_label = "Collision"

    def draw(self, context):
        layout = self.layout
        assert layout is not None

        zcb_import: Zelda_ZCBImportSettings = context.scene.fastds.zelda.importers.zcb
        zcb_import.draw_props(layout)

        zcb_export: Zelda_ZCBExportSettings = context.scene.fastds.zelda.exporters.zcb
        zcb_export.draw_props(layout)


zelda_ops_to_register = [
    Zelda_DoImportZCB,
    Zelda_DoExportZCB,
]

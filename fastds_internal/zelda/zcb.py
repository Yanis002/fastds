import struct
import bpy
import random

from bpy.types import PropertyGroup, UILayout, Operator, Material, Context
from bpy.props import StringProperty, EnumProperty
from pathlib import Path
from mathutils import Vector, Color
from dataclasses import dataclass

from .utility import Zelda_Panel, get_scene_enum, get_extract_dir
from ..utility import BinaryFile, PluginError, VecFx32, prop_split, validate_binary_path, get_lzss_file, yUpToZUp
from ..materials import get_new_material_color


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

        if self.raw_data[0x00:0x04] == b"BDRG":
            raw_type, raw_size, raw_num_entries, raw_unk_0A = struct.unpack("<4sIHH", self.raw_data)
            raw_unk_0B = None
        else:
            raw_type, raw_size, raw_num_entries, raw_unk_0A, raw_unk_0B = struct.unpack(ZCBSectionHeader.fmt, self.raw_data)

        self.type: str = raw_type[::-1].decode("utf-8")
        self.size: int = raw_size
        self.num_entries: int = raw_num_entries
        self.unk_0A: int = raw_unk_0A
        self.unk_0B: int | None = raw_unk_0B


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

    class Entry:
        def __init__(self, value: int):
            self.value = value
            self.material: Material | None = None

        def create_material(self, index: int):
            color = Color((1, 1, 1))
            color.hsv = (random.random(), 0.5, 0.5)
            self.material = get_new_material_color(f"mat_zcb_plcb_{index}_0x{self.value:08X}", color[:] + (0.5,))
            self.material.fastds.zelda.polyclass.raw_data = f"0x{self.value:08X}"

    def __init__(self, raw_data: bytes, header: ZCBSectionHeader):
        self.header = header
        self.raw_data = raw_data[0x0C : self.header.size]
        self.entries: list[ZCBPolyClasses.Entry] = []

        offset = 0x00
        for _ in range(header.num_entries):
            entry: int = struct.unpack(ZCBPolyClasses.fmt, self.raw_data[offset : offset + 0x04])[0]
            self.entries.append(ZCBPolyClasses.Entry(entry))
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


class ZCBGrid:
    @dataclass
    class Entry:
        index: int
        count: int
        entries: list[int]

    def __init__(self, raw_data: bytes, header: ZCBSectionHeader):
        self.header = header
        self.raw_data = raw_data[0x0C : self.header.size]
        self.entries: list[ZCBGrid.Entry] = []

        width = self.header.size
        height = self.header.unk_0A

        offset = 0x00

        for i in range(width):
            for j in range(height):
                count = struct.unpack("<H", self.raw_data[offset : offset + 0x02])[0]
                offset += 0x02

                end = offset + count * 0x02

                if end >= len(self.raw_data):
                    print(f"WARNING: impossible read at {i};{j};0x{offset:04X}, stopping the iteration here.")
                    return

                entries = list(struct.unpack(f"<{'H' * count}", self.raw_data[offset:end]))
                self.entries.append(ZCBGrid.Entry(j * width + i, count, entries[:]))

                aligned_count = (count + 3) & ~3
                offset += aligned_count

    def is_valid(self):
        return self.header.type == "GRDB"


class ZCBFile(BinaryFile):
    def __init__(self, path: Path | None, raw_data: bytes | None):
        super().__init__(path, raw_data)

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
                and self.vertices.is_valid()
                and self.polyclasses is not None
                and self.polyclasses.is_valid()
                and self.triangles is not None
                and self.triangles.is_valid()
                and self.grid is not None
                and self.grid.is_valid()
            )
        else:
            return (
                self.vertices is not None
                and self.vertices.is_valid()
                and self.normals is not None
                and self.normals.is_valid()
                and self.polyclasses is not None
                and self.polyclasses.is_valid()
                and self.triangles is not None
                and self.triangles.is_valid()
                and self.grid is not None
                and self.grid.is_valid()
            )


class Zelda_DoImportZCB(Operator):
    bl_idname = "scene.zelda_zcb_import"
    bl_label = "Import ZCB"
    bl_options = {"REGISTER", "UNDO", "PRESET"}

    scene: StringProperty()
    path: StringProperty(default="None")

    def execute(self, context: Context):
        def do_import(file: ZCBFile, prefix: str):
            col_name = f"{prefix}_collision"
            new_mesh = bpy.data.meshes.new(col_name)
            new_obj = bpy.data.objects.new(col_name, new_mesh)
            context.scene.collection.objects.link(new_obj)

            for i, entry in enumerate(file.polyclasses.entries):
                if entry.material is None:
                    entry.create_material(i)

                new_mesh.materials.append(entry.material)

            new_mesh.from_pydata(vertices=file.vertices.entries, edges=[], faces=file.triangles.get_indices())

            assert len(new_mesh.polygons) == len(file.triangles.entries), "wrong list lengths"
            for i in range(len(new_mesh.polygons)):
                new_mesh.polygons[i].material_index = file.triangles.entries[i].index_polyclass

        if self.path == "None":
            extract_dir = get_extract_dir(strictly_decomp=True)
            assert extract_dir is not None, "unexpected error"

            map_dir: Path = extract_dir / "files" / "Map" / self.scene
            assert map_dir.exists()

            for lzss_path in map_dir.rglob("map*.bin"):
                lzss_bytes, archive, zcb_data, zcb_filename = get_lzss_file(lzss_path, b"BLCM1BCZ")

                file = ZCBFile(None, zcb_data)
                do_import(file, lzss_path.stem)
        else:
            file = ZCBFile(Path(self.path), None)
            do_import(file, file.path.stem)

        self.report({"INFO"}, "Success!")
        return {"FINISHED"}


class Zelda_DoExportZCB(Operator):
    bl_idname = "scene.zelda_zcb_export"
    bl_label = "Export ZCB"
    bl_options = {"REGISTER", "UNDO", "PRESET"}

    path: StringProperty(default="None")

    def execute(self, context):
        self.report({"INFO"}, "Not implemented yet.")
        return {"FINISHED"}


class Zelda_ZCBImportSettings(PropertyGroup):
    path: StringProperty(description="Path to the ZCB file", subtype="FILE_PATH")
    scene: EnumProperty(items=lambda self, context: get_scene_enum(context), default=1)

    def draw_props(self, layout: UILayout):
        from .operators import Zelda_SearchSceneOperator

        layout = layout.box()
        layout.box().label(text="Import Settings")

        Zelda_SearchSceneOperator.draw_op(layout, self.scene, "import")

        if self.scene == "Custom":
            prop_split(layout, self, "path", "Path")
            validate_binary_path(layout, Path(self.path).resolve(), b"BLCM1BCZ", "ZCB")

        import_op = layout.operator(Zelda_DoImportZCB.bl_idname)

        if self.scene == "Custom":
            import_op.path = self.path
        else:
            import_op.scene = self.scene


class Zelda_ZCBExportSettings(PropertyGroup):
    path: StringProperty(description="Path to the ZCB file", subtype="FILE_PATH")
    scene: EnumProperty(items=lambda self, context: get_scene_enum(context), default=1)

    def draw_props(self, layout: UILayout):
        from .operators import Zelda_SearchSceneOperator

        layout = layout.box()
        layout.enabled = False
        layout.box().label(text="Export Settings")

        Zelda_SearchSceneOperator.draw_op(layout, self.scene, "export")

        if self.scene == "Custom":
            prop_split(layout, self, "path", "Path")

        export_op = layout.operator(Zelda_DoExportZCB.bl_idname)

        if self.scene == "Custom":
            export_op.path = self.path
        else:
            export_op.path = ""


class Zelda_ZCBPanel(Zelda_Panel):
    bl_idname = "ZELDA_PT_zcb"
    bl_label = "Collision (.zcb)"

    def draw(self, context):
        layout = self.layout
        assert layout is not None

        zcb_import: Zelda_ZCBImportSettings = context.scene.fastds.zelda.importers.zcb
        zcb_import.draw_props(layout.column())

        zcb_export: Zelda_ZCBExportSettings = context.scene.fastds.zelda.exporters.zcb
        zcb_export.draw_props(layout.column())


class Zelda_PolyClassProperties(PropertyGroup):
    raw_data: StringProperty(default="0x00000000")

    def draw_props(self, layout: UILayout):
        layout = layout.box()
        layout.box().label(text="Polygon Class Settings")

        prop_split(layout, self, "raw_data", "Raw Data")

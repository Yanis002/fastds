import struct

from typing import Any
from dataclasses import dataclass
from enum import IntEnum
from .utility import fx32_to_float


class GPUCommandType(IntEnum):
    # based on gbatek
    NOP = 0x00
    MTX_RESTORE = 0x14
    MTX_SCALE = 0x1B
    COLOR = 0x20
    NORMAL = 0x21
    TEXCOORD = 0x22
    VTX_16 = 0x23
    VTX_10 = 0x24
    VTX_XY = 0x25
    VTX_XZ = 0x26
    VTX_YZ = 0x27
    VTX_DIFF = 0x28
    BEGIN_VTXS = 0x40
    END_VTXS = 0x41

    @staticmethod
    def get_cmd_size(kind: int) -> int:
        match kind:
            case GPUCommandType.NOP.value | GPUCommandType.END_VTXS.value:
                return 0x00
            case GPUCommandType.MTX_SCALE.value:
                return 0x0C
            case GPUCommandType.VTX_16.value:
                return 0x08
            case _:
                return 0x04


@dataclass
class GPUCommand:
    kind: GPUCommandType
    count: int
    data: list[int]


# "G3d_" classes based on PH/ST decomp + gbatek/other documentation sources
class G3d_NameList_Header:
    """
    Definition of the "Name List" header

    This is a small struct containing a list of some data, it can be offsets or actual data depending on the user
    """

    fmt = "<HH"

    def __init__(self, raw_data: bytes, max: int, is_offset_list: bool):
        self.raw_data = raw_data

        raw_element_size, raw_data_section_size = struct.unpack(G3d_NameList_Header.fmt, self.raw_data[0x00:0x04])

        self.element_size: int = raw_element_size
        self.data_section_size: int = raw_data_section_size

        # some users use this to host offsets towards actual data
        # while others use this to host the actual data directly
        self.offsets: list[int] = []
        if is_offset_list:
            for i in range(max):
                offset = (i + 1) * self.element_size
                self.offsets.append(struct.unpack("<I", self.raw_data[offset : offset + 0x04])[0])

        data = self.raw_data[self.data_section_size :]
        self.names: list[str] = []
        for i in range(max):
            offset = i * 0x10
            self.names.append(struct.unpack("16s", data[offset : offset + 0x10])[0].decode("utf-8"))


class G3d_NameList:
    """
    Definition of the "Name List"

    This is a kind of array with a small header attached to it that has a purpose I'm not able to explain right now (sorry)
    """

    fmt = "<BBHHH"

    def __init__(self, raw_data: bytes, origin: bytes | None, cls: Any):
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

        self.header = G3d_NameList_Header(self.raw_data[self.ofs_header :], self.num_elmnts, origin is not None)

        if origin is not None:
            # if the user is hosting offsets
            for offset in self.header.offsets:
                self.entries.append(cls(origin[offset:]))
        else:
            # if the user is hosting the data
            for i in range(self.num_elmnts):
                offset = self.ofs_header + 0x04 + i * 0x04
                self.entries.append(cls(self.raw_data[offset : offset + 0x04]))


class G3d_UnkStructBoneList:
    fmt = "<I"

    def __init__(self, raw_data: bytes):
        self.raw_data = raw_data


class G3d_Material:
    fmt = "<HHIIIIIIHHHHII"

    def __init__(self, raw_data: bytes):
        self.raw_data = raw_data

        (
            raw_unk_00,
            raw_unk_02,
            raw_dif_amb,
            raw_spe_emi,
            raw_polygon_attr,
            raw_unk_10,
            raw_teximage_params,
            raw_unk_18,
            raw_pltt_base,
            raw_flag,
            raw_width,
            raw_height,
            raw_unk_24_1,
            raw_unk_24_2,
        ) = struct.unpack(G3d_Material.fmt, self.raw_data[0x00:0x2C])

        self.unk_00: int = raw_unk_00
        self.unk_02: int = raw_unk_02
        self.dif_amb: int = raw_dif_amb
        self.spe_emi: int = raw_spe_emi
        self.polygon_attr: int = raw_polygon_attr
        self.unk_10: int = raw_unk_10
        self.teximage_params: int = raw_teximage_params
        self.unk_18: int = raw_unk_18
        self.pltt_base: int = raw_pltt_base
        self.flag: int = raw_flag
        self.width: int = raw_width
        self.height: int = raw_height
        self.unk_24: list[int] = [raw_unk_24_1, raw_unk_24_2]  # TODO: placeholder

        # additional data based on the enabled flags
        offset = 0x2C
        self.flag0x02_unk_00 = None
        self.flag0x02_unk_04 = None
        if not (self.flag & 0x02):
            self.flag0x02_unk_00, self.flag0x02_unk_04 = struct.unpack("<II", self.raw_data[offset : offset + 0x08])
            offset += 0x08

        self.flag0x04_unk_00 = None
        self.flag0x04_unk_02 = None
        if not (self.flag & 0x04):
            self.flag0x04_unk_00, self.flag0x04_unk_02 = struct.unpack("<HH", self.raw_data[offset : offset + 0x04])
            offset += 0x04

        self.flag0x08_unk_00 = None
        self.flag0x08_unk_04 = None
        if not (self.flag & 0x08):
            self.flag0x08_unk_00, self.flag0x08_unk_04 = struct.unpack("<II", self.raw_data[offset : offset + 0x08])
            offset += 0x08

        self.flag0x2000_unk_00: list[float] = []
        if self.flag & 0x2000:
            values = list(struct.unpack("<IIIIIIIIIIIIIIII", self.raw_data[offset : offset + 0x40]))

            for value in values:
                self.flag0x2000_unk_00.append(fx32_to_float(value))


class G3d_TexturePairing:
    fmt = "<HH"

    def __init__(self, raw_data: bytes):
        self.raw_data = raw_data

        raw_offset, raw_num_mat = struct.unpack(G3d_TexturePairing.fmt, self.raw_data[0x00:0x04])

        self.offset = raw_offset
        self.num_mat = raw_num_mat


class G3d_PalettePairing:
    fmt = "<HH"

    def __init__(self, raw_data: bytes):
        self.raw_data = raw_data

        raw_offset, raw_num_mat = struct.unpack(G3d_TexturePairing.fmt, self.raw_data[0x00:0x04])

        self.offset = raw_offset
        self.num_mat = raw_num_mat


class G3d_Material_List:
    fmt = "<HH"

    def __init__(self, raw_data: bytes):
        self.raw_data = raw_data

        raw_texture_pairings_off, raw_palette_pairings_off = struct.unpack(G3d_Material_List.fmt, self.raw_data[0x00:0x04])

        self.texture_pairings_off: int = raw_texture_pairings_off
        self.palette_pairings_off: int = raw_palette_pairings_off
        self.materials = G3d_NameList(self.raw_data[0x04:], self.raw_data, G3d_Material)
        self.texture_pairings = G3d_NameList(self.raw_data[self.texture_pairings_off :], None, G3d_TexturePairing)
        self.palette_pairings = G3d_NameList(self.raw_data[self.palette_pairings_off :], None, G3d_PalettePairing)


class G3d_VertexMesh:
    fmt = "<HHIII"

    def __init__(self, raw_data: bytes):
        self.raw_data = raw_data

        (
            raw_unk_00,
            raw_unk_02,
            raw_unk_04,
            raw_unk_08,
            raw_unk_0C,
        ) = struct.unpack(G3d_VertexMesh.fmt, self.raw_data[0x00:0x10])

        self.unk_00: int = raw_unk_00
        self.unk_02: int = raw_unk_02  # size of header?
        self.unk_04: int = raw_unk_04
        self.unk_08: int = raw_unk_08  # offset to command list?
        self.unk_0C: int = raw_unk_0C  # size of command list?

        offset = 0x00
        data = self.raw_data[0x10:]
        self.commands: list[GPUCommand] = []

        # the command list in the binary is a set of 4 command bytes followed by the data correspond to the 4 commands
        # the number of bytes may vary based on the kind of command (see `GPUCommandType.get_cmd_size`)
        while offset < self.unk_0C:
            # read the 4 command bytes
            raw_cmds = list(struct.unpack("<BBBB", data[offset : offset + 0x04]))

            # move to the beginning of the data
            offset += 0x04

            # process the commands
            for cmd in raw_cmds:
                # fetch the size
                size = GPUCommandType.get_cmd_size(cmd)

                # determine the count (it doesn't matter if there's u8s or u16s thanks to padding)
                count = int(size / 4)

                # add the command to the list
                self.commands.append(
                    GPUCommand(
                        GPUCommandType(cmd), count, list(struct.unpack("<" + "I" * count, data[offset : offset + size]))
                    )
                )

                # go to the next command data, or the next command bytes if it's the 4th command
                offset += size


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
        self.bone_list = G3d_NameList(self.raw_data[0x40:], self.raw_data[0x40:], G3d_UnkStructBoneList)

        # technically not part of the C struct but hosting here because it makes sense
        self.mat_list = G3d_Material_List(self.raw_data[self.off_mat :])
        self.poly_list = G3d_NameList(self.raw_data[self.off_mesh :], self.raw_data[self.off_mesh :], G3d_VertexMesh)

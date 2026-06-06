#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# AFOP_dds_io - GIMP 3.x import plug-in for Avatar: Frontiers of Pandora (Snowdrop)
# "STF" container .dds textures. It strips the STF wrapper and hands the inner BCn
# data to GIMP's own DDS loader, so STF textures open natively from File > Open.
# (Export isn't handled here - GIMP's built-in DDS exporter does that.)
import sys
import gi
import os
import struct
import tempfile

gi.require_version('Gimp', '3.0')
from gi.repository import Gimp, GLib, GObject, Gio


# STF .dds = Snowdrop container, NOT a Microsoft DDS. Layout:
#   [76-byte header][mip chain SMALLEST-first, mip0 LAST][trailer]
#   header u16@6 = width/64, u16@8 = height/128; trailer = streaming metadata.
STF_MAGIC = b"STF\x02"
STF_HEADER = 76


def _block_chain_size(w, h, bpb):
    total = 0
    while True:
        total += max(1, (w + 3) // 4) * max(1, (h + 3) // 4) * bpb
        if w <= 1 and h <= 1:
            break
        w = max(1, w // 2)
        h = max(1, h // 2)
    return total


def parse_stf_template(data):
    # -> (width, height, bpb, header_bytes, trailer_bytes)
    if data[:4] != STF_MAGIC:
        raise ValueError("Not an AFOP/Snowdrop STF .dds (missing STF\\x02 magic).")
    width = struct.unpack_from("<H", data, 6)[0] * 64
    height = struct.unpack_from("<H", data, 8)[0] * 128
    if not (0 < width <= 16384 and 0 < height <= 16384):
        raise ValueError("Could not read texture dimensions from STF header.")
    bpb = None
    for cand in (16, 8):
        extra = len(data) - _block_chain_size(width, height, cand)
        if STF_HEADER <= extra <= STF_HEADER + 4096:
            bpb = cand
            break
    if bpb is None:
        raise ValueError("Could not determine the texture's block format.")
    chain = _block_chain_size(width, height, bpb)
    header = data[:STF_HEADER]
    trailer = data[STF_HEADER + chain:]
    return width, height, bpb, header, trailer


def stf_decode_dxgi(header, bpb):
    # header[14] picks the 16-byte-block codec: 0x00 = BC7, else BC3 (heuristic).
    if bpb == 8:
        return 71            # BC1_UNORM
    return 77 if header[14] != 0 else 98   # BC3_UNORM : BC7_UNORM


def stf_extract_mip0(data):
    # -> (w, h, bpb, header, mip0_bytes)
    w, h, bpb, header, trailer = parse_stf_template(data)
    end = len(data) - len(trailer)
    mip0 = max(1, (w + 3) // 4) * max(1, (h + 3) // 4) * bpb
    return w, h, bpb, header, data[end - mip0:end]


def build_standard_dds(w, h, bpb, dxgi, mip0):
    # Wrap one BCn mip as a standard DX10 DDS that GIMP's loader can read.
    hdr = bytearray(128)
    hdr[0:4] = b"DDS "
    struct.pack_into("<I", hdr, 4, 124)
    struct.pack_into("<I", hdr, 8, 0x1 | 0x2 | 0x4 | 0x1000 | 0x80000)  # caps|h|w|pf|linearsize
    struct.pack_into("<I", hdr, 12, h)
    struct.pack_into("<I", hdr, 16, w)
    struct.pack_into("<I", hdr, 20, len(mip0))
    struct.pack_into("<I", hdr, 28, 1)
    struct.pack_into("<I", hdr, 76, 32)
    struct.pack_into("<I", hdr, 80, 0x4)      # DDPF_FOURCC
    hdr[84:88] = b"DX10"
    struct.pack_into("<I", hdr, 108, 0x1000)  # DDSCAPS_TEXTURE
    dx10 = struct.pack("<IIIII", dxgi, 3, 0, 1, 0)  # format, dim=TEXTURE2D, misc, arraySize, misc2
    return bytes(hdr) + dx10 + mip0


class AfopDdsIo(Gimp.PlugIn):
    def do_query_procedures(self):
        return ["jb-dds-stf-load"]

    def do_set_i18n(self, name):
        return False

    def do_create_procedure(self, name):
        procedure = Gimp.LoadProcedure.new(
            self, name, Gimp.PDBProcType.PLUGIN, self.load_stf, None)
        procedure.set_menu_label("AFOP Snowdrop texture")
        procedure.set_documentation(
            "Load an AFOP/Snowdrop STF .dds",
            "Decodes a Snowdrop 'STF' container .dds into an editable image using GIMP's own DDS loader",
            name)
        procedure.set_extensions("dds")
        procedure.set_magics("0,string,STF")   # claim only STF files; plain DDS stays with GIMP
        procedure.set_attribution("Tenir", "Tenir", "2025")
        return procedure

    def load_stf(self, procedure, run_mode, file, metadata, flags, config, run_data):
        try:
            path = file.peek_path()
            with open(path, "rb") as f:
                data = f.read()
            if data[:4] != STF_MAGIC:
                raise Exception("Not an AFOP/Snowdrop STF .dds (missing STF\\x02 magic).")
            w, h, bpb, header, mip0 = stf_extract_mip0(data)
            dxgi = stf_decode_dxgi(header, bpb)
            std = build_standard_dds(w, h, bpb, dxgi, mip0)
            with tempfile.TemporaryDirectory() as tmp:
                std_path = os.path.join(tmp, "stf_decode.dds")
                with open(std_path, "wb") as f:
                    f.write(std)
                # "DDS " magic routes this temp file to GIMP's own loader (decodes BC7), not back to us.
                image = Gimp.file_load(Gimp.RunMode.NONINTERACTIVE,
                                       Gio.File.new_for_path(std_path))
                if image is None:
                    raise Exception("GIMP's built-in DDS loader returned no image "
                                    "(is file-dds installed and BC7 import supported?).")
            return Gimp.ValueArray.new_from_values([
                GObject.Value(Gimp.PDBStatusType, Gimp.PDBStatusType.SUCCESS),
                GObject.Value(Gimp.Image, image),
            ]), flags
        except Exception as e:
            error = GLib.Error.new_literal(GLib.quark_from_string("STF-Load"), str(e), 0)
            retval = procedure.new_return_values(Gimp.PDBStatusType.EXECUTION_ERROR, error)
            return retval, flags


Gimp.main(AfopDdsIo.__gtype__, sys.argv)

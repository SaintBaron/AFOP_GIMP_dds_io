# AFOP DDS IO — GIMP plug-in

Open **Avatar: Frontiers of Pandora** (and other Snowdrop-engine) `STF` container
`.dds` textures directly in GIMP 3.

Snowdrop doesn't ship standard Microsoft DDS files — its textures are wrapped in a
custom container that begins with the magic bytes `STF\x02`, which GIMP's built-in
DDS importer rejects. This plug-in adds support for opening them; once a texture is
open you edit and save it with GIMP as normal.

## Features

- **Open `STF` `.dds` files** straight from *File ▸ Open* — decoded natively by
  GIMP's own DDS loader (BC7 / BC3 / BC1).
- **No external tools and no dependencies** — it's a single Python file.
- Plain Microsoft DDS files still open with GIMP's built-in loader as usual.

## Requirements

- **GIMP 3.0 or newer** (tested on 3.2).

That's it — nothing else to install.

## Install

The plug-in is a single file, but GIMP 3 requires it to live **inside a subfolder of
the same name**, and on Linux the file must be **executable**.

First, find your GIMP version's plug-in folder — in GIMP, open
*Edit ▸ Preferences ▸ Folders ▸ Plug-ins*; the top entry is your user folder. The
examples below assume GIMP **3.2** — change `3.2` to match your version.

### Windows

1. Open your plug-ins folder (paste into Explorer's address bar):
   ```
   %APPDATA%\GIMP\3.2\plug-ins
   ```
2. Create a folder named `AFOP_dds_io` inside it.
3. Copy `AFOP_dds_io.py` into that folder, so you have:
   ```
   %APPDATA%\GIMP\3.2\plug-ins\AFOP_dds_io\AFOP_dds_io.py
   ```
4. Restart GIMP.

### Linux

```bash
mkdir -p ~/.config/GIMP/3.2/plug-ins/AFOP_dds_io
cp AFOP_dds_io.py ~/.config/GIMP/3.2/plug-ins/AFOP_dds_io/
chmod +x ~/.config/GIMP/3.2/plug-ins/AFOP_dds_io/AFOP_dds_io.py
```

Then restart GIMP. The `chmod +x` is required — GIMP silently ignores
non-executable Python plug-ins on Linux, and you must re-run it any time you
replace the file with a new copy.

### Verify it loaded

Open *Filters ▸ Python-Fu ▸ Console* and run:

```python
print(Gimp.get_pdb().lookup_procedure("jb-dds-stf-load"))
```

A `<Gimp.Procedure …>` line means it's installed. `None` means GIMP didn't load it
(see [Troubleshooting](#troubleshooting)).

## Usage

*File ▸ Open* and pick an `STF` `.dds`. It opens as a normal editable image. Edit it,
then save or export it however you normally would in GIMP.

## Troubleshooting

- **"Invalid DDS format magic number" when opening** — GIMP's built-in loader got
  the file, meaning the plug-in isn't loaded. On Linux this is usually the missing
  `chmod +x`; also confirm the plug-in is in the folder for your *actual* GIMP
  version, and fully restart GIMP.
- **Plug-in doesn't appear at all** — launch GIMP from a terminal (`gimp-3.2`) and
  watch for a Python traceback mentioning `AFOP_dds_io.py`; that names the problem.
  Make sure the file sits inside its own `AFOP_dds_io/` subfolder, not loose in
  `plug-ins/`.
- **A texture opens as colour noise** — that texture's block codec was guessed wrong
  (the plug-in distinguishes BC7 from BC3 by a header byte). Open an issue with the
  file name and it can be adjusted.

## How it works

The plug-in claims only `.dds` files whose contents start with `STF`. For those it
reads the container's dimensions and block format, extracts the full-resolution mip,
rebuilds a standard DX10 DDS around it, and hands that to GIMP's own DDS loader to
decode. Standard DDS files don't match the `STF` magic, so they keep going to GIMP's
built-in loader untouched.

## Credits

Built on an existing texconv-based GIMP DDS plug-in, with Snowdrop `STF` container
import added. Attribution: Tenir.

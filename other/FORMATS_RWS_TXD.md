<!-- markdownlint-disable MD010 MD013 -->

# Madagascar (2005) — RWS Wave Dictionary & TXD Texture Dictionary

A self-contained reference for the two RenderWare container formats used by *Madagascar* (Toys for Bob / Activision, 2005, PC build). Everything below was derived from the parsers in this repo, from `Game.exe` disassembly (addresses noted inline), and verified against the 19 shipped `.rws` files (1741 waves) and 57 shipped `.txd` files (5323 textures) under [Levels/](../Levels/).

- **RWS** = a RenderWare **Audio** wave dictionary (`rwaID_WAVEDICT`, chunk `0x809`). One file = one named dictionary holding N sound effect / music streams. Shipped as e.g. `Levels/beach/4_WavDictXBOX.rws`.
- **TXD** = a RenderWare **Texture Dictionary** (`rwID_TEXDICTIONARY`, chunk `0x16`). One file = N platform-native rasters. Shipped as e.g. `Levels/beach/2_TD_LEVEL FOLDER.txd`.

Both are ordinary RenderWare chunk trees, so section 1 (the common container rules) applies to both.

---

## 1. The RenderWare chunk container (common to both formats)

Everything is little-endian. A file is a tree of chunks; every chunk starts with the same 12-byte header:

| Offset | Type  | Field            | Meaning                                                     |
| -----: | ----- | ---------------- | ----------------------------------------------------------- |
|   0x00 | `u32` | `type`           | chunk id (see below)                                          |
|   0x04 | `u32` | `size`           | **payload** size in bytes, *excluding* these 12 header bytes  |
|   0x08 | `u32` | `libraryIdStamp` | packed RenderWare version + build                             |

To walk a container: read the header, then either recurse into the payload (container chunk) or consume `size` bytes (leaf chunk); the next sibling starts at `offset + 12 + size`. **`size` is authoritative** — never re-derive a chunk's end from the fields you parsed, because several chunks carry trailing garbage or padding.

Chunks are packed back to back with **no inter-chunk alignment padding** (verified: 453 of 1741 `rwaID_WAVEDATA` chunks have a size that is only 2-byte aligned, and the next chunk still starts immediately after).

### Chunk ids

`chunkId = (vendorId << 8) | sectionId` — `MAKECHUNKID` in [madagascar/lib/rwConstants.py](../madagascar/lib/rwConstants.py).

| Vendor id  | Name                      | Ids relevant here |
| ---------- | ------------------------- | ----------------- |
| `0x000000` | RenderWare core           | `0x01` struct, `0x02` string, `0x03` extension, `0x15` texture native, `0x16` texture dictionary |
| `0x000008` | `CRITERIONRWA` (RW Audio) | `0x802`–`0x80E` — the wave chunks |
| `0x800000` | `TFB` (Toys for Bob)      | `0x800000DD` texture extension, plus other private plugin chunks |

### Library ID stamp

`library_id_unpack()` in [madagascar/lib/rw_basics.py](../madagascar/lib/rw_basics.py):

```python
if libid & 0xFFFF0000:
    version = ((libid >> 14) & 0x3FF00) + 0x30000 | ((libid >> 16) & 0x3F)   # 0xVJNBB
    build   = libid & 0xFFFF
else:
    version, build = libid << 8, 0
```

Retail Madagascar values:

| Stamp        | Version  | Build | Used by              |
| ------------ | -------- | ----- | -------------------- |
| `0x1C020024` | 3.7.0.02 | 36    | every shipped `.rws` |
| `0x1C02000F` | 3.7.0.02 | 15    | every shipped `.txd` |

The version matters: `RW_TextureDictionary_Struct` switches layout on `version > 0x3600`, and 3.7.0.2 is above it.

### RenderWare GUIDs

16-byte GUIDs in these formats store `Data1` / `Data2` / `Data3` **little-endian**. In Python that is `uuid.UUID(bytes_le=raw)`, *not* `uuid.UUID(bytes=raw)`. Getting this wrong silently produces a plausible-looking but wrong GUID, so codec lookups fail.

### Where these files come from

Retail levels ship as a single `.stream` container. Each asset inside is one `sf_LoadEmbeddedAsset` record ([madagascar/streamfuncs/stringfuncs/sf_LoadEmbeddedAsset.py](../madagascar/streamfuncs/stringfuncs/sf_LoadEmbeddedAsset.py)) holding `name`, `guid`, a `type` string, `filePath`, `deps` and the raw asset bytes. The `type` string decides the extension when unpacking ([cli/utils.py](../cli/utils.py)):

| `type` string        | Extension |
| -------------------- | --------- |
| `rwID_TEXDICTIONARY` | `.txd`    |
| `rwaID_WAVEDICT`     | `.rws`    |
| `rwID_WORLD`         | `.bsp`    |
| `rwID_CLUMP`         | `.dff`    |
| `TextStringDict`     | `.txl`    |

So the `.txd` / `.rws` files in `Levels/<name>/` are byte-identical extracts of the embedded blobs; re-packing means writing the bytes back into that record and fixing `dataSize`.

---

## 2. RWS — RenderWare Audio wave dictionary

Also called the "rwaudio dict" or "RWS stream 2057". Implemented in [madagascar/sections/RWA/](../madagascar/sections/RWA/); a complete standalone reader **and writer** (older, self-contained, no repo imports) lives in [other/legacy/rwaRWS.py](legacy/rwaRWS.py).

### 2.1 Chunk tree

```text
0x809  rwaID_WAVEDICT                     (container — the whole file)
├── 0x80A  rwaID_WAVEDICT_DICT            (dictionary object: guid + name + flags)
└── 0x80C  rwaID_WAVEDICT_WAVE            (container)
    ├── u32 waveCount                     <- plain u32, not a chunk
    ├── 0x802  rwaID_WAVE                 (container, x waveCount)
    │   ├── 0x803  rwaID_WAVESTRUCT       (format descriptor + name + codec GUIDs)
    │   └── 0x804  rwaID_WAVEDATA         (raw sample bytes)
    ├── 0x802  rwaID_WAVE
    │   └── ...
    └── ...
```

Ids `0x80B`, `0x80D`, `0x80E` (`..._WAVE_HDR`, `..._WAVEDATA_HDR`, `..._WAVEDATA`) exist in the enum but do not occur in Madagascar's files.

Real example — `Levels/beach/4_WavDictXBOX.rws`, 4,956,076 bytes:

```text
0x0809 rwaID_WAVEDICT        size=4956064  stamp=0x1C020024 @0x0
  0x080A rwaID_WAVEDICT_DICT   size=84       @0xC    name='beachLevelWaveDictXbox'
  0x080C rwaID_WAVEDICT_WAVE   size=4955956  @0x6C   count=175
    0x0802 rwaID_WAVE            size=4656   @0x7C
      0x0803 rwaID_WAVESTRUCT      size=176  @0x88   name='minigame_ticktick' 44100Hz/16bit/mono
      0x0804 rwaID_WAVEDATA        size=4456 @0x144
    ...
```

### 2.2 `0x80A` — `rwaID_WAVEDICT_DICT`

This is the **raw memory image of the runtime `RtWaveDictionary` object**, written verbatim. Reverse-engineered from `RtWaveDict_ReadBody @ 0x0050d3d0` and `RtWaveDict_InitFromStruct @ 0x0050d750` in `Game.exe`. Most fields are stale runtime pointers the loader immediately recomputes; only `info`, `guid` and `name` carry information.

| Offset | Type     | Field           | Meaning |
| -----: | -------- | --------------- | ------- |
|   0x00 | `void*`  | `guid_ptr`      | presence flag for the GUID — the loader only tests `!= 0` |
|   0x04 | `void*`  | `name_ptr`      | presence flag for the name — the loader only tests `!= 0` |
|   0x08 | `u32`    | `ownership`     | bit0 = owns guid memory, bit1 = owns name memory (0 = embedded) |
|   0x0C | `void*`  | `entries.next`  | wave-entry list head; reset to self on load |
|   0x10 | `void*`  | `entries.prev`  | reset to self on load |
|   0x14 | `u32`    | `entries.end`   | list terminator / count; reset to 0 on load |
|   0x18 | `u8[4]`  | `info`          | byte `+0x1B` bit3 (`0x08`) => sample data is **big-endian** (GameCube/Wii builds) |
|   0x1C | `void*`  | `registry.next` | link into the global dictionary list; recomputed |
|   0x20 | `void*`  | `registry.prev` | recomputed |
|   0x24 | `GUID`   | `guid`          | dictionary identity |
|   0x34 | `char[]` | `name`          | null-terminated ASCII |
|      … | `u8[]`   | trailing        | leftover buffer bytes — keep verbatim for an exact round-trip |

Retail: `size` is 84 bytes, i.e. 0x34 + name + ~9 bytes of trailing garbage. Observed `info` words (read as `u32`) are `0x02080101` (13 dicts), `0x02080102` (3), `0x02080100` (2), `0x02015D6F` (1) — the big-endian bit is clear in all of them, as expected for a PC/Xbox build.

When writing a fresh dictionary, any non-zero value works for `guid_ptr` / `name_ptr` (the repo writes `0xFFFFFFFF`); the pointer / list fields can be left at 0.

### 2.3 `0x80C` — `rwaID_WAVEDICT_WAVE`

Payload = `u32 waveCount`, then `waveCount` consecutive `0x802` chunks. Nothing else.

### 2.4 `0x802` / `0x803` / `0x804` — one wave

`0x802` is a pure container holding exactly one `0x803` followed by one `0x804`.

**`0x803` `rwaID_WAVESTRUCT`** — parsed by `RtWave_StreamRead @ 0x00508b80` -> `RtWave_CreateFromStruct @ 0x00508df0`:

```text
u32          flags               presence bitmask
RtWaveFormat source_format       how the samples are stored on disk
RtWaveFormat dest_format         what they decode to (== source when uncompressed)
u32          loop_stream_flag    0 = one-shot, 1 = looping
[flags & 0x1] GUID   identifier   this wave's instance GUID
[flags & 0x2] char[] name         null-terminated, then padded to a 16-byte boundary
[flags & 0x4] GUID   decoder      codec / decoder class GUID
[flags & 0x8] GUID   aux          auxiliary class GUID
```

The optional blocks appear **in ascending bit order** after the two format descriptors. Every shipped wave has `flags == 0xF` (all four present).

The name padding is *not* zero-filled in retail files — it holds allocator garbage (e.g. `00 00 7B 63 02 00 F0 6F 99 00 6E 6F 74 65`). Preserve it byte-for-byte for an identical round-trip; the padding length is `(-(len(name)+1)) % 16`. The alignment of 16 comes from `DAT_006322c0` (runtime-initialised, so it reads as 0 statically) — the value is confirmed empirically: struct sizes are exactly `144 + 16 * ceil((len(name)+1)/16)`, observed as 160 / 176 / 192.

**`RtWaveFormat`** (28-byte base; sizing logic at `FUN_0050a290`):

| Offset | Type    | Field         | Notes |
| -----: | ------- | ------------- | ----- |
|   0x00 | `u32`   | `sample_rate` | Hz |
|   0x04 | `u32`   | `_format_ref` | runtime pointer on disk; **!= 0 => a 16-byte codec GUID follows the base** |
|   0x08 | `u32`   | `data_size`   | size of the sample data in bytes |
|   0x0C | `u8`    | `bit_depth`   | bits per sample |
|   0x0D | `u8`    | `channels`    | |
|   0x0E | `u16`   | `_pad0`       | not really padding — retail has 18 or 0 in `source`, 70 in `dest`; meaning unknown |
|   0x10 | `u32`   | `_aux_ref`    | runtime pointer; **!= 0 => `aux_size` bytes of codec tables follow the GUID** |
|   0x14 | `u32`   | `aux_size`    | size of that aux block (0 in all retail files) |
|   0x18 | `u8[4]` | `_tail`       | kept verbatim; retail is `00 00 43 00` in `source`, `00 00 00 00` in `dest` |
|   0x1C | `GUID`  | `codec_uuid`  | present iff `_format_ref != 0` |
|      … | `u8[]`  | `aux_data`    | present iff `_aux_ref != 0` |

So a retail format descriptor is 28 + 16 = 44 bytes.

**`0x804` `rwaID_WAVEDATA`** — the payload is the raw sample bytes and nothing else. Its `size` equals `source_format.data_size`. No padding.

### 2.5 Codec GUIDs

| Codec      | GUID |
| ---------- | ---- |
| `PCM16`    | `D01BD217-3587-4EED-B9D9-B8E86EA9B995` (PCM signed 16-bit) |
| `PSXADPCM` | `D9EA9798-BBBC-447B-96B2-654759102E16` |
| `DSPADPCM` | `F86215B0-31D5-4C29-BD37-CDBF9BD10C53` (GameCube/Wii) |
| `XBOXIMA`  | `632FA22B-11DD-458F-AA27-A5C346E9790E` |
| `IMAADPCM` | `EF386593-B611-432D-957F-A71ADE44227A` (PC) |
| `FLOAT`    | `DA1E4382-2C99-4C61-AD99-7F364B211537` |
| `WMA`      | `3F1D8147-B7C4-41E6-A69B-3CC0025B33C7` |
| `MP3`      | `BACFB36E-529D-4692-BF53-324256B0734F` |
| `MP2`      | `34D09A54-57D3-409E-A6AD-2BC845AEC339` |
| `MP1`      | `04C15BA7-F907-40AB-A49F-EEFEF8C4D296` |
| `AC3`      | `A30DB390-58A9-43C4-B9D2-55D84D3AE754` |

The **decoder** and **aux** GUIDs are separate values and are constant across every retail wave: decoder `CA5E5BE6-B366-4739-8FA5-F3C8BBD5E529`, aux `55AD338C-145E-457E-A75B-1F55DD97B7EF`.

### 2.6 What the retail data actually looks like

Measured over all 19 `.rws` files / 1741 waves:

- **Codec is PCM16 for every single wave**, with `source_format` and `dest_format` identical (same rate, size, depth, channels). Despite the `WavDictXBOX` filenames, nothing is Xbox-IMA compressed — so exporting to WAV is a straight copy of the `0x804` payload. ([madagascar/lib/ima_adpcm.py](../madagascar/lib/ima_adpcm.py) exists for the ADPCM case but is unused by these files.)
- Bit depth is 16 everywhere; 1735 waves are mono, 6 are stereo.
- Sample rates: 22050 (981), 11025 (502), 44100 (252), plus a handful at 22255 / 16000 / 8000.
- `loop_stream_flag`: 0 for 1429, 1 for 312.
- `flags` is `0xF` for all of them.

Duration = `data_size / (sample_rate * channels * bit_depth/8)`.

Export to `.wav` is therefore: `nchannels = channels`, `sampwidth = bit_depth // 8`, `framerate = sample_rate`, `writeframes(wave_data.data)`.

### 2.7 Code map and gotchas (RWS)

| File | Role |
| ---- | ---- |
| [madagascar/sections/RWA/WAVEDICT_0809.py](../madagascar/sections/RWA/WAVEDICT_0809.py) | top-level `RW_WaveDict` |
| [madagascar/sections/RWA/WAVEDICT_DICT_080A.py](../madagascar/sections/RWA/WAVEDICT_DICT_080A.py) | `0x80A`, documented field by field |
| [madagascar/sections/RWA/WAVEDICT_WAVE_080C.py](../madagascar/sections/RWA/WAVEDICT_WAVE_080C.py) | `0x80C` count + wave list |
| [madagascar/sections/RWA/WAVE_0802.py](../madagascar/sections/RWA/WAVE_0802.py) | `0x802` wave pair |
| [madagascar/sections/RWA/WAVESTRUCT_0803.py](../madagascar/sections/RWA/WAVESTRUCT_0803.py) | `0x803` + `RWA_WaveFormat` + codec enum |
| [madagascar/sections/RWA/WAVEDATA_0804.py](../madagascar/sections/RWA/WAVEDATA_0804.py) | `0x804` sample bytes |
| [other/legacy/rwaRWS.py](legacy/rwaRWS.py) | older standalone reader **plus a working writer**, `import_wav()` / `export_wav()` / Tk stream browser |

Gotchas:

1. **Only `0x80A` and `0x803` have real `write()` implementations** in `madagascar/sections/RWA/`. `WAVEDICT_0809`, `WAVEDICT_WAVE_080C`, `WAVE_0802` and `WAVEDATA_0804` have stub writers that emit an empty payload — they will silently produce a truncated file. Use [other/legacy/rwaRWS.py](legacy/rwaRWS.py) (`load_2057` / `AudioStream_2057.save`) for round-tripping until those are filled in.
2. The legacy module describes the same bytes with less precision: its `_unk1` is `flags`, `_unk2` is `_format_ref`, `_pad1` is `_pad0`, `_unk_misc_offset` is `_aux_ref`, and its 0x40-byte `format_info` block is really the tail of `dest_format` plus the identifier GUID. Prefer the `sections/RWA` naming.
3. GUIDs are `bytes_le` (see section 1).
4. `RW_WaveDict.read()` currently raises `TypeError` on Python 3.14, because several of these dataclasses use `field(default_factory=uuid.UUID)` and `uuid.UUID()` with no arguments is an error. `default_factory=lambda: uuid.UUID(int=0)` fixes it.

---

## 3. TXD — RenderWare texture dictionary

Implemented in [madagascar/sections/TEXDICTIONARY_0016.py](../madagascar/sections/TEXDICTIONARY_0016.py) and [madagascar/sections/TEXTURENATIVE_0015.py](../madagascar/sections/TEXTURENATIVE_0015.py); loaded via `madagascar.txd.load_txd(path)` / `loads_txd(bytes)`.

### 3.1 Chunk tree

```text
0x16  rwID_TEXDICTIONARY                  (container — the whole file)
├── 0x01  rwID_STRUCT                     u16 textureCount + u16 deviceId
├── 0x15  rwID_TEXTURENATIVE   x textureCount
│   ├── 0x01  rwID_STRUCT                 platform id + header fields + palette + texels
│   └── 0x03  rwID_EXTENSION
│       └── 0x800000DD  rwID_tfb_Texture  12 bytes, TFB-private
└── 0x03  rwID_EXTENSION                  usually empty (size 0)
```

### 3.2 Dictionary struct (`0x01` under `0x16`)

For `version > 0x3600`, which includes Madagascar's 3.7.0.2:

| Type  | Field          | Notes |
| ----- | -------------- | ----- |
| `u16` | `textureCount` | number of `0x15` chunks that follow |
| `u16` | `deviceId`     | 1 = D3D8, 2 = D3D9, 6 = PS2, 8 = XBOX, 10 = PS3 — **8 in every shipped file** |

For older versions it is a single `u32 textureCount` with no device id.

An empty dictionary is legal and common: the `*_LANG_English.txd` files are 40 bytes total — a struct with count 0 plus an empty extension.

### 3.3 `0x15` `rwID_TEXTURENATIVE` -> `0x01` struct

The struct payload always begins with `u32 platform_id`, and everything after it is **platform-specific**:

| `platform_id` | Platform |
| ------------- | -------- |
| 2 | OpenGL |
| 4 or `0x00325350` (`"PS2\0"`) | PlayStation 2 |
| **5** | **Xbox — what every shipped Madagascar texture uses** |
| 8 | D3D8 |
| 9 | D3D9 |

#### Xbox layout (`platform_id == 5`)

A 92-byte fixed header, then the palette, then the mip chain:

| Offset | Type       | Field             | Notes |
| -----: | ---------- | ----------------- | ----- |
|   0x00 | `u32`      | `platform_id`     | 5 |
|   0x04 | `u8`       | `filter_mode`     | 0 none, 1 nearest, 2 linear, 3 mip-nearest, 4 mip-linear, 5 linear-mip-nearest, 6 linear-mip-linear |
|   0x05 | `u8`       | `addressing`      | low nibble = U mode, high nibble = V mode; 0 none, 1 wrap, 2 mirror, 3 clamp |
|   0x06 | `u16`      | padding           | 0 |
|   0x08 | `char[32]` | `name`            | fixed field, null-padded |
|   0x28 | `char[32]` | `mask_name`       | fixed field, usually empty |
|   0x48 | `u32`      | `raster_format`   | bitfield, see below |
|   0x4C | `u32`      | `has_alpha`       | 0 / 1 |
|   0x50 | `u16`      | `width`           | of mip level 0 |
|   0x52 | `u16`      | `height`          | |
|   0x54 | `u8`       | `bit_depth`       | bits per *stored texel* (8 for palettised) |
|   0x55 | `u8`       | `mipmap_count`    | 1 = no mipmaps |
|   0x56 | `u8`       | `tex_code_type`   | 4 in all retail textures |
|   0x57 | `u8`       | `dxt_compression` | 0 = none, 1 or 0x0C = DXT1, 3 = DXT3, 5 = DXT5 |
|   0x58 | `u32`      | `texel_data_size` | total mip-chain bytes, **rounded up to 4** |
|   0x5C | `BGRA[]`   | palette           | 256 entries if `pal8`, 32 if `pal4`, else absent — 4 bytes each, stored **B, G, R, A** |
|      … | `u8[]`     | mip chain         | level 0 first (largest), then halving; the whole block padded to 4 bytes |

Verified across all 5323 retail textures: `struct.size == 92 + paletteEntries * 4 + align4(sum of mipBytes)`, where `mipBytes(level) = w * h * (bit_depth / 8)` with `w, h` halved (min 1) per level. `texel_data_size` is that **padded** sum — it differs from the raw sum for 1704 of the 5323 textures, so trust the padded form.

If the struct chunk ends right after `texel_data_size`, the file was written by a tool that dropped the pixel data; the repo flags this as `has_texel_data = False` rather than reading on into the next chunk. No retail texture is like this.

#### `raster_format` bitfield

The low byte selects the pixel / palette-entry format, the high nibble carries flags:

| Value    | Format |
| -------- | ------ |
| `0x0000` | default |
| `0x0100` | 1555 (1-bit alpha, RGB555) |
| `0x0200` | 565 |
| `0x0300` | 4444 |
| `0x0400` | LUM8 (grayscale) |
| `0x0500` | 8888 (RGBA) |
| `0x0600` | 888 (RGB) |
| `0x0A00` | 555 |

| Flag     | Meaning |
| -------- | ------- |
| `0x1000` | auto-mipmap (RW generates them) |
| `0x2000` | `pal8` — **256**-entry palette present |
| `0x4000` | `pal4` — **32**-entry palette present |
| `0x8000` | mipmaps included |

Note the `pal4` entry count: 32, not 16. Unusual, but empirically confirmed — with 32 the size equation above holds for all 5323 textures, and every one of them still stores **8-bit** indices (`bit_depth == 8`).

#### Swizzling

Xbox texel data (palette indices *and* raw 16/32-bit pixels) is stored **Morton / Z-order swizzled** and must be unswizzled before use — `unswizzle(data, w, h, bpp)` / `swizzle(...)` in `TEXTURENATIVE_0015.py`, where `bpp` is *bytes* per texel: 1 for palette indices, 2 for 16-bit, 4 for 32-bit. DXT blocks are **not** swizzled.

#### Decode rules (`RW_TextureNative.decode(mip) -> RGBA bytes`)

- **palettised, no DXT** — unswizzle indices (1 byte each), then look up the palette (stored BGRA, exposed as RGBA).
- **32-bit, no palette** — unswizzle with `bpp = 4`, then swap B and R (stored BGRA).
- **16-bit, no palette** — unswizzle with `bpp = 2`, then expand per `raster_format` (1555 / 565 / 4444).
- **DXT1 (`1` or `0x0C`) / DXT3 (`3`) / DXT5 (`5`)** — block decode, no swizzle.

#### PS2 layout (`platform_id == 4` or `"PS2\0"`) — read-only in this repo

Structurally different, worth knowing so the two are not confused. `name` and `mask_name` are separate `0x02 rwID_STRING` chunks rather than fixed 32-byte fields. Then an outer `0x01` struct wraps a nested `0x01` struct of 64 bytes holding `width` / `height` / `bit_depth` / `raster_format` plus the GS registers `TEX0`, `TEX1`, `MIPTBP1`, `MIPTBP2` (see the PS2 *GS Users Manual*), followed by `texel_data_size`, `palette_data_size`, `gpuDataAlignedSize` and `skyMipmapValue`. Texels come **before** the palette, each as a sequence of GS transfer blocks, and the pixel region opens with a 12-byte pointer preamble that `texel_data_size` does not account for. Mip count comes from `TEX1.mxl + 1`; bits per pixel from `TEX0.psm` (PSMCT32 = 32, PSMCT16 / 16S = 16, PSMT8 = 8, PSMT4 = 4). The palette (CLUT) and the indices need PS2-specific unswizzling, and the 5-bit-ish alpha is doubled toward 0–255 on decode. Writing PS2 textures is not implemented.

### 3.4 The `0x800000DD` TFB texture extension

Every retail `rwID_TEXTURENATIVE` carries exactly one extension child: chunk `0x800000DD` (`rwID_tfb_Texture`), payload **12 bytes**. It is not parsed by this repo, and the repo's notes record that the PC `Game.exe` has **no reader for it** — it is skipped at load. Observed payloads are `04 00 0F 0F 00 00 00 00` followed by a `u32` that is `0x00000000` (3738 times), `0xFFFFFFFF` (1324), `0x00000001` (239) or `0x00000002` (19). The same chunk id also appears on `rwID_TEXTURE` chunks inside models.

### 3.5 What the retail data actually looks like

Measured over all 57 `.txd` files / 5323 textures:

- `deviceId` is 8 (Xbox) and `platform_id` is 5 (Xbox) for **every** file and texture.
- `dxt_compression` is 0 and `bit_depth` is 8 for **every** texture — everything is 8-bit palettised, nothing is DXT compressed.
- `raster_format`: `0x4600` (1738), `0x4500` (1234), `0xD600` (698), `0xD500` (515), `0x2600` (397), `0xB500` (286), `0x2500` (250), `0xB600` (202), `0xA500` (3) — i.e. pal4 / pal8 crossed with 888 / 8888, with or without the mipmap and auto-mipmap flags.
- `mipmap_count`: 1 (3619), then 8 (663), 7 (461), 9 (241), 6 (208), and so on.
- `filter_mode`: linear (3562), mip-linear (1373), linear-mip-linear (328), nearest (57).
- Addressing: wrap/wrap (4676), clamp/clamp (522), wrap/clamp (101), clamp/wrap (21).
- `has_alpha`: 1 for 2285, 0 for 3038.
- Common sizes: 32x32 (1282), 64x64 (1037), 128x128 (975), 256x256 (352), 64x128 (280).

The only 3 outliers in the whole set — `alex_body`, `alex_arms_new` and `mango` in `Levels/beach_alex/2_TD_LEVEL FOLDER.txd` — are textures written by **this toolkit**, not by the retail pipeline: `filter_mode = 0`, `tex_code_type = 0`, and an **empty** `0x03` extension with no `0x800000DD` child. That is a useful signature for spotting tool-written rasters, and a hint that `create_texture()` should probably copy those fields from a retail texture.

### 3.6 Code map and gotchas (TXD)

| File | Role |
| ---- | ---- |
| [madagascar/txd.py](../madagascar/txd.py) | `load_txd(path)` / `loads_txd(bytes)` |
| [madagascar/sections/TEXDICTIONARY_0016.py](../madagascar/sections/TEXDICTIONARY_0016.py) | `RW_TextureDictionary` — `export_all()`, `add_texture()`, `find_texture_by_name()`; reads **and** writes |
| [madagascar/sections/TEXTURENATIVE_0015.py](../madagascar/sections/TEXTURENATIVE_0015.py) | raster struct, swizzle, DXT codecs, `decode()`, `export_png()`, `from_png()`, `create_texture()` |
| [cli/commands/txd_unpack.py](../cli/commands/txd_unpack.py) | `txd-unpack <file> <dir>` — dumps PNGs |
| [cli/commands/txd_add_texture.py](../cli/commands/txd_add_texture.py) | adds a PNG to an existing dictionary |
| [tools/txd/app.py](../tools/txd/app.py) | GUI viewer |

Gotchas:

1. **Writing only supports Xbox** (`RW_TextureNative_Struct.write` raises for any other platform), and reading raises `NotImplementedError` for D3D8 / D3D9.
2. Use `add_texture()` rather than `textures.append()` — it also updates `struct.textureCount`, and a mismatch makes the dictionary unreadable.
3. Texture names are capped at 31 characters plus terminator by the fixed 32-byte field.
4. Palette entries are BGRA on disk and RGBA in the `PaletteEntry` dataclass; the swap happens in both the reader and the writer.
5. Per this repo's notes, every raster shipped in the retail streams has texel data (4536 rasters across 17 streams, none empty) — an empty raster means a damaged file, not a "metadata-only folder dictionary".

// First 4 bytes of each codec GUID
enum CodecUUID : u32 {
    PCM16    = 0xD01BD217,  // {D01BD217-3587-4EED-B9D9-B8E86EA9B995} PCM Signed 16-bit
    PSXADPCM = 0xD9EA9798,  // {D9EA9798-BBBC-447B-96B2-654759102E16} PSX-ADPCM
    DSPADPCM = 0xF86215B0,  // {F86215B0-31D5-4C29-BD37-CDBF9BD10C53} DSP-ADPCM (GCN only)
};

// Common 12-byte header prefixing every chunk
struct ChunkHeader {
    u32 id;
    u32     payload_size;
    u32     version;
};

// ── File Header chunk (0x80A) ──────────────────────────────────────────────

struct FileHeaderPayload {
    u8   unk[0x34];
    char name[];  // null-terminated file/archive name; rest of payload is padding
    u8   _pad[parent.hdr.payload_size - 0x34 - sizeof(name)];
};

struct FileHeaderChunk {
    ChunkHeader       hdr;      // id = FileHeader (0x80A), payload_size usually 0x44
    FileHeaderPayload payload;
};

// ── Stream Header chunk (0x803) ────────────────────────────────────────────
//
// Layout relative to chunk start:
//   +0x00  ChunkHeader (id, payload_size, version)
//   +0x0C  payload begins
//   +0x10  sample_rate
//   +0x18  stream_size
//   +0x1C  bit_depth
//   +0x1D  channels        (always 1 in known files)
//   +0x20  unk_misc_off    (unreliable; actual offset computed as +0x3C)
//   +0x24  misc_data_size  (0x60 for DSP-ADPCM, 0 otherwise)
//   +0x2C  codec_uuid      (first 4 bytes of GUID)
//   +0x3C  input_misc_data[misc_data_size]
//   +0x3C+misc_data_size  output_misc_data[misc_data_size]
//   +0x3C+misc_data_size*2  format_info[0x40]
//   +0x7C+misc_data_size*2  stream_name (null-terminated, rest of payload)
//
// DSP-ADPCM: coefs at input_misc_data+0x1C, hist at input_misc_data+0x40 (big-endian s16)

struct StreamHdrPayload {
    u32       unk0;
    u32       sample_rate;          // +0x10 from chunk start
    u32       unk1;
    u32       stream_size;          // +0x18
    u8        bit_depth;            // +0x1C
    u8        channels;             // +0x1D
    u16       pad;
    u32       unk_misc_off;         // +0x20 (stored offset; per source "wrong?")
    u32       misc_data_size;       // +0x24 (0x60 = DSP coef/hist tables present)
    u32       unk2;
    CodecUUID codec_uuid;           // +0x2C (first 4 bytes of GUID)
    u8        codec_uuid_rest[12];  // +0x30 (remaining 12 bytes of GUID)
    u8        input_misc_data[misc_data_size];   // +0x3C (DSP: coefs@+0x1C, hist@+0x40)
    u8        output_misc_data[misc_data_size];  // +0x3C+misc_data_size
    u8        format_info[0x40];                 // +0x3C+misc_data_size*2 (target fmt)
    char      stream_name[];  // null-terminated; rest of payload is padding
    u8        _pad[parent.hdr.payload_size - 0x70 - misc_data_size * 2 - sizeof(stream_name)];
};

struct StreamHdrChunk {
    ChunkHeader      hdr;     // id = StreamHdr (0x803)
    StreamHdrPayload payload;
};

// ── Stream Data chunk (0x804) ──────────────────────────────────────────────

struct StreamDataChunk {
    ChunkHeader hdr;                    // id = StreamData (0x804)
    u8          data[hdr.payload_size]; // raw audio samples
};

// ── Stream chunk (0x802) ───────────────────────────────────────────────────

struct StreamChunk {
    ChunkHeader     hdr;           // id = Stream (0x802)
    StreamHdrChunk  stream_header;
    StreamDataChunk stream_data;
};

// ── File Data chunk (0x80C) ────────────────────────────────────────────────

struct FileDataPayload {
    u32         total_subsongs;
    StreamChunk streams[total_subsongs];
};

struct FileDataChunk {
    ChunkHeader     hdr;     // id = FileData (0x80C)
    FileDataPayload payload;
};

// ── Top-level file ─────────────────────────────────────────────────────────

struct RWSFile {
    ChunkHeader     hdr;          // id = File (0x809)
    FileHeaderChunk file_header;
    FileDataChunk   file_data;
};

RWSFile rws @ 0x00;

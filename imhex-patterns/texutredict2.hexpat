struct RWHeader {
    u32 type;
    u32 size;
    u32 libraryIdStamp;
};

bitfield  FilterMode {
    filterMode : 8;
    uAddressing : 4;
    vAddressing : 4;
    pad : 16;
};

struct TextureFormat {
    u32 platformId;
    FilterMode filterMode;
    char name[32];
    char maskName[32];
};

struct RasterFormatXbox {
    u32 rasterFormat;
    u32 hasAlpha;
    u16 width;
    u16 height;
    u8  depth;
    u8  mipmapCount;
    u8  texCodeType;
    u8  dxtCompression;
    u32 texelDataSize;              // Xbox has 4 extra bytes here
};

struct RasterHeader {
    TextureFormat textureFormat;
    RasterFormatXbox rasterFormat;
};

struct PaletteEntry {
    u8 r;
    u8 g;
    u8 b;
    u8 a;
};

struct Extension {
    RWHeader header;
    u8 data[header.size];
};

struct Raster {
    RWHeader nativeHeader;
    RWHeader structHeader;
    u128 structStart = $;
    RasterHeader rasterHeader;

    // Xbox palette: PAL8=256, PAL4=32, else 0
    if (rasterHeader.rasterFormat.rasterFormat & 0x2000)
        PaletteEntry palette[256];
    else if (rasterHeader.rasterFormat.rasterFormat & 0x4000)
        PaletteEntry palette[32];

    // Xbox mipmaps have no dataSize field — consume remaining struct data
    u8 texelData[structStart + structHeader.size - $];
    Extension extension;
};

struct TextureDictionary {
    RWHeader dictHeader;
    RWHeader structHeader;
    u16 textureCount;
    u16 deviceId;
    Raster textures[textureCount];
    Extension extension;
};

TextureDictionary my_pattern @ 0x00;
using CHAR = s8;

enum UserDataType : u32 {
    Integer = 0x01,
    Float = 0x02,
    String = 0x03
};

struct RWString {
    u32 length;
    char signature[length];
};

struct Entry {
    RWString label;
    UserDataType dataType;
    u32 numberOfObjects;
    
    if (dataType == UserDataType::Integer) {
        u32 values[numberOfObjects];
    } else if (dataType == UserDataType::Float) {
        float values[numberOfObjects];
    } else if (dataType == UserDataType::String) {
        RWString values[numberOfObjects];
    }
};


struct Pattern {
    u32 entryCount;
    Entry entries[entryCount];
};
 
Pattern my_pattern @ 0x00;
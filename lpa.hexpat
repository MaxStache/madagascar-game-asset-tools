struct Keyframe {
    u32 keyframeType;
    u32 boneID;
    float value;
};

struct Pattern {
    u32 int; // Version !?
    Keyframe keyframaes[58];
};

Pattern my_pattern @ 0x00;
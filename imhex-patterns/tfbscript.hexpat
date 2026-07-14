#pragma endian little
#pragma description Madagascar "TFB Script" (.ai) - SCRIPT asset from .stream

// On-disc format of a SCRIPT asset (asset type name "TFB Script").
// Verified byte-exact against all 330 .ai files in Levels/*/ (parses to EOF).
//
// Numbers are little-endian. Strings are length-prefixed (u8 length, no NUL).
// The instruction list is a pre-order-serialised tree: every node declares how
// many following instructions belong to its primary ("then"/body) child group
// and its secondary ("else") child group.

struct PString {
    u8   len;
    char str[len];
};

// One row of a symbol table.
struct TableEntry {
    u8   len;
    char name[len];      // e.g. "set value::op-code", "Melman Actor::actor",
                         //      "camera::user::camera", "health_off_01::sprite"
    u32  metadata;       // always 0 in observed script assets
};

struct StringTable {
    u32 count;
    TableEntry entries[count];
};

struct Instruction {
    u8 opcode;           // index into opcodes[]. 0xFF = script SECTION marker (no handler,
                         // no payload); named by order of appearance in FUN_004349e0:
                         // 1st=PRESCRIPT, 2nd=STARTUP, 3rd=SHUTDOWN, 4th=main body, 5th+=further.
    u8 a;                // flags byte: bit0=1 (set), bit3(0x08)=block/branch head,
                         // bit6(0x40)=no handler bound (disabled/placeholder; loader skips lookup)
    u8 b;                // primary  child span: (b >> 3) instructions follow as body
    u8 c;                // secondary child span: (c >> 3) instructions form the else-branch
    u8 d;                // reserved, always 0
    u8 payload_size;
    u8 payload[payload_size];   // opcode-specific operands (see disassembler)
};

struct TFBScript {
    PString     magic;        // "TFB Script"
    u32         unk;          // loader work-pool size in 4-byte words. Game.exe FUN_004349e0
                              // does DAT_0061f890 = malloc(unk * 4) and bump-allocates the
                              // script's section/instruction objects (4 words each) out of it.
                              // Editor-precomputed allocation upper bound.
    StringTable opcodes;      // action names, all suffixed "::op-code"
    StringTable symbolsA;     // named refs (globals / user vars, actors, sprites, cameras)
    StringTable symbolsB;     // named refs (locals); addressed together with symbolsA
    u32         instr_count;
    Instruction instructions[instr_count];
};

TFBScript script @ 0x00;

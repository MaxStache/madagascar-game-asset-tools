# .AI File format (TFBScript)

A `.ai` file is **little-endian** and laid out as:

```c
struct TFBScriptFile {
    uint8_t      magic_length;        // 0x0A (10)
    char         magic[magic_length]; // TFB Script

    uint32_t     unknown;

    StringTable  opcode_table;

    StringTable  global_references;
    StringTable  local_references;

    uint32_t     instruction_count; // Flattened instruction count

    Instruction  instructions[instruction_count];
};

struct StringTable {
    uint32_t    entry_count;

    struct {
        uint8_t   content_length;
        char      content;
        uint32_t  unused; // Always 0x000000
    } entries[entry_count];

    /*
     Entry strings are `::`-separated
     paths like `myactor::actor`, `score::user::value` or `move to::op-code`
     (name / optional category / type).
    */
};

struct Instruction {
    uint8_t opcode_index;
    DWORD   flags;

    uint8_t payload_size;
    byte    payload[payload_size];
};
  

```

## Instructions: opcode_index

The index into *opcode_table* to get the actual opcode

Example:

```text
opcode_table:
    0x01 - print::op-code

instruction 0:
        opcode_index: 0x01 -> print::op-code
...
```

## Instructions: flags

A 32-bit, bit-packed field controlling flow and nesting:

| Bits  | Field             | Meaning                                                        |
|-------|-------------------|----------------------------------------------------------------|
| 0–2   | `flow_control`    | `0` = end/return, `1` = continue, `2+` = break (N-1) levels up |
| 3–5   | *reserved*        | unused/unknown                                                 |
| 6     | `no_handler`      | opcode has no handler bound; loader skips construction         |
| 7     | `runtime_scratch` | runtime-only scratch bit, always `0` on disk                   |
| 11–31 | `descendant_span` | number of following instructions nested as this one's children |

See [tfbscript/opcodes/base.py](tfbscript/opcodes/base.py) (`InstructionFlags`).

## Instructions: payload

The payload (params) of the opcode.

Opcode specific, often uses building blocks such as:

### Reference

Size: 4 bytes, bit-packed

resolves to a global table entry, a local table entry, or an engine builtin (`self`, `[~each]`, ...), plus optional member/sub/scope selectors.

See [tfbscript/reference.py](tfbscript/reference.py).

### RHS

Size: 5-11 bytes

A tag byte followed by an int32, float, RGBA color, int16 pair, or a reference — optionally extended by an operator byte and a second RHS, forming an expression like `(x + 1)`.

See [tfbscript/rhs.py](tfbscript/rhs.py).

from enum import IntEnum
from typing import Optional

from lib.parser import Parser

class RelOp(IntEnum):
    """Relational operator for OpAbstractCheckValue / OpCheckValue."""
    LessOrEq  = 0
    Eq        = 1
    GreatOrEq = 2
    Less      = 3
    Great     = 4
    NotEq     = 5

    def symbol(self) -> str:
        return ("<=", "==", ">=", "<", ">", "!=")[self.value]

class CombineMode(IntEnum):
    """Displacement combine mode for OpDisplace."""
    relative = 0
    absolute = 1
    local    = 2
class ArithOp(IntEnum):
    """Arithmetic operator for ValueRHSVariant."""
    dotdotdot = -1
    plus      = 0
    minus     = 1
    times     = 2
    divide    = 3

    def symbol(self) -> str:
        return ("...", "+", "-", "*", "/")[self.value + 1]

class RHSType(IntEnum):
    Int  = 0 # GUESS
    Unknown1 = 2 # Maybe Reference?
    Color32 = 32 # GUESS
    Unknown2 = 48
    Unknown3 = 1
    Unknown4 = 16


def readStringTable(buf: Parser):
    tableEntries = buf.readUint32()
    table = []
    for _ in range(tableEntries):
        string_length = buf.readUint8()
        entry = {
            "len": string_length,
            "string": buf.readString(string_length),
            "metadata": buf.readUint32(),
        }
        table.append(entry)
    return table


def safe_name(table, idx):
    if 0 <= idx < len(table):
        return table[idx]["string"]
    return None


def opcode_name(op, op_table):
    if 0 <= op < len(op_table):
        return op_table[op]["string"]
    return f"OP_0x{op:02X}"


def fmt_idx(idx, table):
    return str(idx)

debug_variable_counter = 0
debug_variables = {
}

def _table_ref(value: int, table) -> Optional[str]:
    if 0 <= value < len(table):
        return table[value]["string"]
    return None

def _resolve(idx: int, st1, st2, st3) -> str:
    """Resolve a table index to a human-readable name.

    0xFF = self (the actor executing the script)
    0xFE = ~found (result register written by find variable::op-code)
    Everything else: look up in st2 then st3; if not found treat as literal integer.
    st1 (opcode names) is intentionally excluded — those never appear as value refs.
    """
    if idx == 0xFF:
        return "self"
    if idx == 0xFE:
        return "~found"
    for tbl in (st2, st3):
        ref = _table_ref(idx, tbl)
        if ref is not None:
            return ref
    return str(idx)

# 556_RW_Balloon.ai
# 967_ME_Sound_Ambient.ai
# 702_ME_Hint.ai
with open("Levels/KingOfNY/1046_Alex_RunAsPlayer.ai", "rb") as f:
    buf = Parser(f.read())

    scriptNameLength = buf.readUint8()
    scriptName = buf.readString(scriptNameLength)

    unk_count = buf.readUint32()

    table1 = readStringTable(buf)  # opcode names
    table2 = readStringTable(buf)  
    table3 = readStringTable(buf)  

    combined_table = table2 + table3 

    def resolve_ref(ref_bytes):
        addr = ref_bytes[2] * 256 + ref_bytes[1]
        slot = addr // 0x40
        sub = addr % 0x40
        if slot < len(combined_table):
            name = combined_table[slot]["string"]
            return f"{name}+{sub:#x}" if sub else name
        return f"global:{ref_bytes.hex()}"  # cross-script; need level-wide slot map
    
    def sref(parser: Parser) -> str:
        _   = parser.readUint8()  # byte 0 (unused)
        b1  = parser.readUint8()
        idx = parser.readUint8()
        b3  = parser.readUint8()
        name = _resolve(idx, table1, table2, table3)
        if idx == 0xFF and b1 not in (0xFF, 0x00):
            # self with a non-null field-type qualifier
            return f"{name}<{b1:#04x}>"
        if idx not in (0xFF, 0xFE) and b3 == 0xFF:
            # local variable slot (ref_kind=0xFF distinguishes from global refs)
            slot = b1 >> 6
            if slot:
                return f"{name}[{slot}]"
        return name
    
    def parse_rhs(parser: Parser) -> str:
        return parser.readBytes(5).hex() 
        b0 = parser.readUint8()
        b1 = parser.readUint8()
        _ = parser.readUint8()  # unused
        b3 = parser.readUint8()
        b4 = parser.readUint8()

        if b0 == 0 and b4 == 0xFF:
            return "0" if b3 == 0 else _resolve(b3, table1, table2, table3)

        if b0 == 0 and b1 == 0:
            return str(b3)

        idx = b0 if b0 != 0 else b1
        if idx == 0:
            return "0"

        return _resolve(idx, table1, table2, table3)
    
    def rhs5(parser: Parser) -> str:
        return parse_rhs(parser)



    print(f"Script Name: {scriptName}")
    print(f"Unknown Count: {unk_count}")
    print(f"OP     -    T1 (Opcodes): {len(table1)} entries")
    for i, entry in enumerate(table1):
        print(f"  {i}: {entry['string']} (metadata: {entry['metadata']})")
    print()
    print(f"GLOBAL - T2 (Global Variables): {len(table2)} entries")
    for i, entry in enumerate(table2):
        print(f"  {i}: {entry['string']} (metadata: {entry['metadata']})")
    print()
    print(f"LOCAL  -  T3 (Local Variables): {len(table3)} entries")
    for i, entry in enumerate(table3):
        print(f"  {i}: {entry['string']} (metadata: {entry['metadata']})")

    instruction_count = buf.readUint32()
    instructions = []
    for _ in range(instruction_count):
        instruction = {
            "opcode": buf.readUint8(),
            "a": buf.readUint8(),
            "b": buf.readUint8(),
            "c": buf.readUint8(),
            "d": buf.readUint8(),
            "payload_size": buf.readUint8(),
        }
        instruction["payload"] = buf.readBytes(instruction["payload_size"])
        instructions.append(instruction)

    print("----- INSTRUCTIONS -----")
    indent = 0
    stack = []  # remaining transitive-instruction count per open block

    for instr in instructions:
        op = instr["opcode"]
        op_name = opcode_name(op, table1)

        a = instr["a"]
        b = instr["b"]
        c = instr["c"]
        d = instr["d"]
        payload_hex = instr["payload"].hex()

        pl = instr["payload"]
        pl_size = len(pl)

        prefix = "   " * indent

        if op_name == "comment:::op-code":
            payload_buf = Parser(instr["payload"])
            comment_length = payload_buf.readUint8()
            comment_string = payload_buf.readString(comment_length)
            line = f"{prefix}// {comment_string}"
        elif op_name == "print::op-code":
            payload_buf = Parser(instr["payload"])
            unknown = payload_buf.readBytes(4)
            print_length = payload_buf.readUint8()
            comment_string = payload_buf.readString(print_length)
            line = f'{prefix}PRINT "{comment_string}", unknown: {unknown.hex()}'
        elif op_name == "play animation::op-code":
            payload_buf = Parser(instr["payload"])
            animation_idx = payload_buf.readUint8()
            line = f"{prefix}PLAY ANIMATION, IDX: {animation_idx}"
        elif op_name == "create variable::op-code": 
            payload_buf = Parser(instr["payload"])
            resolve_ref_str = sref(payload_buf)
            line = f"{prefix}CREATE VARIABLE {resolve_ref_str}"

        elif op_name == "check value::op-code": # 00c004ff010002000000
            pb = Parser(pl)

            ref = sref(pb)

            rel_op = RelOp(pb.readUint8())

            value_type = RHSType(pb.readUint8())
            value = pb.readUint32()

            line = f"{prefix}CHECK VALUE {ref} {rel_op.symbol()} {value_type.name}: {value} {pb.readRemaining().hex()}"

        elif op_name == "set value::op-code":
            pb = Parser(instr["payload"])
            #value = pb.readBytes(4)
                  
            resolve_ref_str = sref(pb)

            value_type = RHSType(pb.readUint8())
            value = pb.readUint32()


            #rhs_string = parse_rhs(pb)
            #rhs_string = "_RHS HERE_"
      
            line = f"{prefix}SET VALUE {resolve_ref_str} to {value_type.name}: {value} {pb.readRemaining().hex()}"

        elif op_name == "displace::op-code":
            payload_buf = Parser(instr["payload"])
            
            # NP(4) + CombineMode(1) + lenNP(5) + headNP(5) + pitchNP(5)
            np = sref(payload_buf)
            
            cm = CombineMode(payload_buf.readUint8())

            len_np   = rhs5(payload_buf)
            head_np  = rhs5(payload_buf)
            pitch_np = rhs5(payload_buf)
      
            line = f"{prefix}DISPLACE vector {np} with combine mode: {cm.name}, len: {len_np}, head: {head_np}, pitch: {pitch_np}"

        elif op_name == "inc value::op-code":
            payload_buf = Parser(instr["payload"])
                  
            resolve_ref_str = sref(payload_buf)

      
            line = f"{prefix}INCREASE VALUE {resolve_ref_str}"

        elif op_name == "find variable::op-code":
            payload_buf = Parser(instr["payload"])
            #value = payload_buf.readBytes(4)
                  
            var_type = sref(payload_buf)
            owner = sref(payload_buf)

            line = f"{prefix}FIND VARIABLE with type '{var_type}' and owner '{owner}'"

        elif op_name == "slide value::op-code":
            payload_buf = Parser(instr["payload"])
            #print(payload_buf.remaining())
                  
            lhs = sref(payload_buf)
            target = parse_rhs(payload_buf)
            seconds = parse_rhs(payload_buf)
            ease_out = sref(payload_buf)
            ease_in = sref(payload_buf)

            #target = "_RHS HERE_" 
            #seconds = "_RHS HERE_" 

            line = f"{prefix}SLIDE VALUE {lhs} to {target} over {seconds} seconds, ease_out: {ease_out}, ease_in: {ease_in}"


        elif op_name == "set reference::op-code":
            payload_buf = Parser(instr["payload"])
            resolve_ref_str = sref(payload_buf)
            resolve_ref_str2 = sref(payload_buf)

            line = f"{prefix}SET REFERENCE, {resolve_ref_str} to {resolve_ref_str2}, payloadLength{len(payload_buf.data)}"

        elif op_name == "remove::op-code":
            payload_buf = Parser(instr["payload"])
            np = sref(payload_buf)
            line = f"{prefix}REMOVE {np}"

        elif op_name == "set behavior::op-code":
            payload_buf = Parser(instr["payload"])
            behav = sref(payload_buf)
            line = f"{prefix}SET BEHAVIOUR {behav}"

        else:
            line = (
                f"{prefix}{op_name:<26} "
                f"A: {fmt_idx(a, table2):<3} "
                f"B: {fmt_idx(b, table2):<3} "   #figured out so far
                f"C: {fmt_idx(c, table3):<3} " # always 0 in tested scirpts
                f"D: {d:<3} " # always 0 in tested scirpts
                f"Payload: {payload_hex}"
            )
        if c > 0:
            print(f"Unhandle instruction prop C: {c} in opcode {op_name}")
        if d > 0:
            print(f"Unhandle instruction prop D: {d} in opcode {op_name}")
        print(line)

        # This instruction occupies one transitive slot in every currently-open block.
        for j in range(len(stack)):
            stack[j] -= 1

        # Close any blocks whose body has been fully consumed.
        while stack and stack[-1] <= 0:
            stack.pop()
            indent -= 1

        # If this instruction opens a block, push its body size (in instructions).
        if b > 0:
            stack.append(b // 8)
            indent += 1
        #if a > 0:
        #    stack.append(a // 8)
        #    indent += 1

    if stack:
        print(f"// WARNING: {len(stack)} block(s) did not close cleanly; remaining: {stack}")
from enum import IntEnum

from formats.lib.parser import Parser
from formats.lib.sytax_hilighting import Color, color_text
from formats.lib.tfb_reference import Reference, parse_reference
from formats.lib.tfb_rhs import read_rhs, rhs_to_string

import glob
import sys

sys.stdout.reconfigure(encoding="utf-8")

TABLE1 = []
TABLE2 = []
TABLE3 = []
UNIMPLEMENTED_OPCODES = set()

class OpParser(Parser):
    def readRef(self):
        ref_bytes = self.readBytes(4)
        return parse_reference(ref_bytes, offset=0, table2=TABLE2, table3=TABLE3)

    def readRHS(self):
        return read_rhs(self, table2=TABLE2, table3=TABLE3)


class RelOp(IntEnum):
    """Relational operator for OpAbstractCheckValue / OpCheckValue."""

    LessOrEq = 0
    Eq = 1
    GreatOrEq = 2
    Less = 3
    Great = 4
    NotEq = 5

    def symbol(self) -> str:
        return ("<=", "==", ">=", "<", ">", "!=")[self.value]

class CombineMode(IntEnum):
    """Displacement combine mode for OpDisplace."""

    relative = 0
    absolute = 1
    local = 2

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


def opcode_name(op, op_table):
    if 0 <= op < len(op_table):
        return op_table[op]["string"]
    return f"OP_0x{op:02X}"


def BUILD_LINE(
    prefix: str,
    op_name: str,
    content: str,
):
    colored_name = color_text(op_name, Color.METHOD)
    line = f"{prefix}{colored_name} {content}"

    return line


def CRef(
    ref: Reference,
):
    return color_text(ref, Color.REFERENCE)


def CRelOp(
    rel_op: RelOp,
):
    return color_text(rel_op.symbol(), Color.OPERATOR)


def CRHS(
    rhs,
):
    return rhs_to_string(rhs)


def CNum(
    num,
):
    return color_text(str(num), Color.NUMBER)


def CStr(
    string,
):
    return color_text(str(f'"{string}"'), Color.STRING)

def CEnum(
    enumValue,
):
    return color_text(enumValue.name, Color.ENUM_VALUE)


def render_line(instructions, op_names, i, prefix):
    """Render instruction `i` to a single display line.

    `prefix` is the indentation to put before the line; pass "" to get just
    the colored op-name + content with no leading whitespace (used when a
    line is being embedded inside another line, e.g. if/else's condition).
    """
    instr = instructions[i]
    op_name = op_names[i]

    a = instr["a"]
    b = instr["b"]
    c = instr["c"]
    d = instr["d"]
    pl = instr["payload"]
    payload_hex = pl.hex()

    if op_name == "comment:::op-code":
        payload_buf = Parser(instr["payload"])
        comment_length = payload_buf.readUint8()
        comment_string = payload_buf.readString(comment_length)
        line = color_text(f"{prefix}// {comment_string}", Color.COMMENT)

    elif op_name == "print::op-code":
        p = OpParser(instr["payload"])

        ref = p.readRef()

        print_length = p.readUint8()
        text = p.readString(print_length)

        line = BUILD_LINE(
            prefix,
            "PRINT",
            f"{CStr(text)} on {CRef(ref)}",
        )

    elif op_name == "if/else::op-code":
        # If/else carries no payload of its own -- at runtime the engine
        # evaluates the FIRST instruction of the then-branch as the condition
        # (Game.exe FUN_00431790) and picks the then/else span based on its
        # result. Fold that condition instruction's own rendered line into
        # the IF/ELSE line, and keep it out of the then-children (the caller
        # is expected to skip `i + 1` when iterating, via hidden_indices).
        cond_idx = i + 1
        cond_line = render_line(instructions, op_names, cond_idx, "")

        line = BUILD_LINE(
            prefix,
            "IF/ELSE",
            f"({cond_line})",
        )

    elif op_name == "displace::op-code":
        p = OpParser(instr["payload"])

        ref = p.readRef() # the object being displaced
        combine_mode = CombineMode(p.readUint8())

        length = p.readRHS() # magnitude of displacement
        heading = p.readRHS() # yaw/heading
        pitch = p.readRHS() # pitch


        line = BUILD_LINE(
            prefix,
            "DISPLACE",
            f"{CRef(ref)} {CEnum(combine_mode)} by length: {CRHS(length)}, heading: {CRHS(heading)}, pitch: {CRHS(pitch)}",
        )

    elif op_name == "check message::op-code":
        p = OpParser(instr["payload"])

        message_ref = p.readRef() # the message being checked for

        if p.remaining() == 0:
            line = BUILD_LINE(
                prefix,
                "CHECK MESSAGE",
                f"{CRef(message_ref)}",
            )

        else:
            sender_ref = p.readRef() # who must have sent it (context to match)
            extra = p.readUint8()
            value = p.readRHS() # comparison Value

            line = BUILD_LINE(
                prefix,
                "CHECK MESSAGE",
                f"{CRef(message_ref)} from {CRef(sender_ref)}, extra {CNum(extra)} with value {CRHS(value)}",
            )

    elif op_name == "send message::op-code":
        p = OpParser(instr["payload"])

        message_ref = p.readRef() # which message to send
        recipient_ref = p.readRef() # who to send it to
        extra = p.readUint8() # unknown
        value = p.readRHS() # the message's argument Value

        line = BUILD_LINE(
            prefix,
            "SEND MESSAGE",
            f"{CRef(message_ref)} to {CRef(recipient_ref)}, extra {CNum(extra)} that has value {CRHS(value)}",
        )


    elif op_name == "create variable::op-code":
        p = OpParser(instr["payload"])
        ref = p.readRef()

        line = BUILD_LINE(
            prefix,
            "CREATE VARIABLE",
            f"{CRef(ref)}",
        )

    #elif op_name == "use camera::op-code":
    #    p = OpParser(instr["payload"])

    #    camera_ref = p.readRef()

    #    line = BUILD_LINE(
    #        prefix,
    #        "USE CAMERA",
    #        f"{CRef(camera_ref)}",
    #    )

    elif op_name == "inc value::op-code":
        p = OpParser(instr["payload"])
        ref = p.readRef()

        line = BUILD_LINE(
            prefix,
            "INCREMENT VALUE",
            f"{CRef(ref)}",
        )

    elif op_name == "dec value::op-code":
        p = OpParser(instr["payload"])
        ref = p.readRef()

        line = BUILD_LINE(
            prefix,
            "DECREMENT VALUE",
            f"{CRef(ref)}",
        )

    elif op_name == "find variable::op-code":
        p = OpParser(instr["payload"])
        type_ref = p.readRef()
        owner_ref = p.readRef()

        line = BUILD_LINE(
            prefix,
            "FIND VARIABLE",
            f"with type {CRef(type_ref)} and owner {CRef(owner_ref)}",
        )

    elif op_name == "set behavior::op-code":
        p = OpParser(instr["payload"])
        ref = p.readRef()  # the behavior to set

        line = BUILD_LINE(
            prefix,
            "SET BEHAVIOR",
            f"{CRef(ref)}",
        )

    elif op_name == "set reference::op-code":
        p = OpParser(instr["payload"])
        dest_ref = p.readRef()  # dest
        src_ref = p.readRef()  # src

        line = BUILD_LINE(
            prefix,
            "SET REFERENCE",
            f"{CRef(dest_ref)} to {CRef(src_ref)}",
        )

    elif op_name == "spawn actor::op-code":
        # TODO
        # THIS IS A STUB AND MAY NEEDS REVISION!

        p = OpParser(instr["payload"])
        actor_ref = p.readRef()  # actor / prototype to spawn
        context_ref = p.readRef()  # spawn owner/location context
        param_rhs = p.readRHS()  # spawn owner/location context

        line = BUILD_LINE(
            prefix,
            "SPAWN ACTOR",
            f"{CRef(actor_ref)}, owner: {CRef(context_ref)}, param: {CRHS(param_rhs)}",
        )

    elif op_name == "teleport to::op-code":
        p = OpParser(instr["payload"])
        target_ref = (
            p.readRef()
        )  # reference: teleport destination (e.g. an actor/placement)
        node_point = p.readUint8()  # named-node-point/socket index on the target (e.g. a specific attachment point)
        offset = p.readRHS()  # positional offset
        seconds_rhs = p.readRHS()  # transition time in seconds

        line = BUILD_LINE(
            prefix,
            "TELEPORT TO",
            f"{CRef(target_ref)} at node {CNum(node_point)} offset by {CRHS(offset)} over {CRHS(seconds_rhs)} seconds",
        )

    elif op_name == "play sound::op-code":
        p = OpParser(instr["payload"])
        ref = p.readRef()

        line = BUILD_LINE(
            prefix,
            "PLAY SOUND",
            f"{CRef(ref)}",
        )

    elif op_name == "stop sound::op-code":
        p = OpParser(instr["payload"])
        ref = p.readRef()

        line = BUILD_LINE(
            prefix,
            "STOP SOUND",
            f"{CRef(ref)}",
        )

    elif op_name == "play animation::op-code":
        p = OpParser(instr["payload"])
        anim_idx = p.readUint8()

        line = BUILD_LINE(
            prefix,
            "PLAY ANIMATION",
            f"{CNum(anim_idx)}",
        )

    elif op_name == "check value::op-code":
        p = OpParser(pl)

        ref = p.readRef()
        rel_op = RelOp(p.readUint8())
        rhs = p.readRHS()

        line = BUILD_LINE(
            prefix,
            "CHECK VALUE",
            f"{CRef(ref)} {CRelOp(rel_op)} {CRHS(rhs)}",  # example: var == rhs
        )

    elif op_name == "set value::op-code":
        p = OpParser(instr["payload"])

        ref = p.readRef()
        rhs = p.readRHS()
        line = BUILD_LINE(
            prefix,
            "SET VALUE",
            f"{CRef(ref)} to {CRHS(rhs)}",
        )

    elif op_name == "check reference::op-code":
        p = OpParser(instr["payload"])

        ref1 = p.readRef()
        ref2 = p.readRef()

        line = BUILD_LINE(
            prefix,
            "CHECK REFERENCE",
            f"{CRef(ref1)} is reference to {CRef(ref2)}",
        )

    elif op_name == "turn to::op-code":
        p = OpParser(instr["payload"])

        target = p.readRHS()
        extra = p.readBytes(1)

        line = BUILD_LINE(
            prefix,
            "TURN TO",
            f"{CRHS(target)} , extra: {extra}",
        )

    elif op_name == "run as player::op-code":
        p = OpParser(instr["payload"])

        actor_ref = p.readRef() #  reference to the actor that becomes player-controlled

        line = BUILD_LINE(
            prefix,
            "RUN AS PLAYER",
            f"{CRef(actor_ref)}",
        )

    elif op_name == "move to::op-code":
        p = OpParser(instr["payload"])

        ref = p.readRef() #  reference: object/node-point to move
        node_point = p.readUint8() # always present (one byte read either way, via different readers depending on ref's resolved type)
        extra = p.readBytes(1)
        value = p.readRHS() #  movement target/speed

        line = BUILD_LINE(
            prefix,
            "MOVE TO",
            f"{CRef(ref)}, node point: {CNum(node_point)}, extra: {extra}, value: {CRHS(value)}",
        )

    elif op_name == "move from::op-code":
        p = OpParser(instr["payload"])

        ref = p.readRef()
        extra = p.readBytes(1)
        value = p.readRHS()

        line = BUILD_LINE(
            prefix,
            "MOVE FROM",
            f"{CRef(ref)}, extra: {extra}, value: {CRHS(value)}",
        )


    elif op_name == "for each::op-code":
        p = OpParser(instr["payload"])

        collection_ref = p.readRef()
        node_point = p.readUint8()

        line = BUILD_LINE(
            prefix,
            "FOR EACH",
            f"in {CRef(collection_ref)}, node point {CNum(node_point)}",
        )

    elif op_name == "control::op-code":
        p = OpParser(instr["payload"])
        
        ref = p.readRef()

        note = ", There were extra (leftover) bytes when reading this op!" if p.remaining() > 0 else ""
        line = BUILD_LINE(
            prefix,
            "CONTROL",
            f"{CRef(ref)} {note}",  # example: var == rhs
        )

    elif op_name == "slide value::op-code":
        p = OpParser(instr["payload"])

        ref = p.readRef()
        target = p.readRHS()
        seconds = p.readRHS()
        ease_out = p.readRef()
        ease_in = p.readRef()

        line = BUILD_LINE(
            prefix,
            "SLIDE VALUE",
            f"{CRef(ref)} to {CRHS(target)} over {CRHS(seconds)} seconds, ease_out: {CRef(ease_out)}, ease_in: {CRef(ease_in)}",
        )
    elif op_name == "remove::op-code":
        p = OpParser(instr["payload"])
        ref = p.readRef()

        line = BUILD_LINE(
            prefix,
            "REMOVE",
            f"{CRef(ref)}",
        )

    else:
        UNIMPLEMENTED_OPCODES.add(op_name)
        line = (
            f"{prefix}{op_name:<26} "
            f"A: {a:<3} "
            f"B: {b:<3} "  # figured out so far
            f"C: {c:<3} "  # always 0 in tested scirpts
            f"D: {d:<3} "  # always 0 in tested scirpts
            f"Payload: {payload_hex}"
        )

    return line


# 556_RW_Balloon.ai
# 967_ME_Sound_Ambient.ai
# 702_ME_Hint.ai
#1069_RW_Haybale_Shed.ai
def parse_tfbscirpt_file(filename):
    global TABLE1, TABLE2, TABLE3

    with open(filename, "rb") as f:
        buf = Parser(f.read())

        scriptNameLength = buf.readUint8()
        scriptName = buf.readString(scriptNameLength)

        unk_count = buf.readUint32()

        table1 = readStringTable(buf)  # opcode names
        table2 = readStringTable(buf)
        table3 = readStringTable(buf)

        TABLE1, TABLE2, TABLE3 = table1, table2, table3

        combined_table = table2 + table3

        def resolve_ref(ref_bytes):
            addr = ref_bytes[2] * 256 + ref_bytes[1]
            slot = addr // 0x40
            sub = addr % 0x40
            if slot < len(combined_table):
                name = combined_table[slot]["string"]
                return f"{name}+{sub:#x}" if sub else name
            return f"global:{ref_bytes.hex()}"  # cross-script; need level-wide slot map

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

        def compute_layout(instrs):
            """Rebuild the pre-order instruction tree.

            Every instruction declares two consecutive child groups that follow it:
              (b >> 3) instructions form the primary ("then"/body) branch, and
              (c >> 3) instructions form the secondary ("else") branch.
            Children nest recursively. Returns per-index indent depth and the set of
            indices that begin an else-branch (verified to tile exactly on every
            shipped .ai file).
            """
            n = len(instrs)
            depth = [0] * n
            else_start = set()

            def consume(i, d):
                depth[i] = d
                then_n = instrs[i]["b"] >> 3
                else_n = instrs[i]["c"] >> 3
                j = i + 1
                end_then = j + then_n
                while j < end_then:
                    j = consume(j, d + 1)
                if else_n:
                    else_start.add(j)
                    end_else = j + else_n
                    while j < end_else:
                        j = consume(j, d + 1)
                return j

            idx = 0
            while idx < n:
                idx = consume(idx, 0)
            return depth, else_start

        depth, else_start = compute_layout(instructions)

        # Opcode 0xFF is a script SECTION marker (no handler, no payload). The engine
        # (Game.exe FUN_004349e0) names each by order of appearance: 1st=PRESCRIPT,
        # 2nd=STARTUP, 3rd=SHUTDOWN, 4th=main body, 5th+=further sections.
        # Resolved up front (rather than mutated inline during printing) so that
        # if/else's condition-child can be looked up and rendered out of order.
        SECTION_NAMES = {0: "PRESCRIPT", 1: "STARTUP", 2: "SHUTDOWN", 3: "MAIN"}
        op_names = []
        section_index = 0
        for instr in instructions:
            if instr["opcode"] == 0xFF:
                op_names.append(
                    "[%s]" % SECTION_NAMES.get(section_index, "SECTION %d" % section_index)
                )
                section_index += 1
            else:
                op_names.append(opcode_name(instr["opcode"], table1))

        # if/else has no payload of its own; its condition is the first instruction
        # of its then-branch (see render_line). Hide that instruction from the
        # normal then-children so it isn't also printed as its own line.
        hidden_indices = set()
        for i, instr in enumerate(instructions):
            if op_names[i] == "if/else::op-code" and (instr["b"] >> 3) >= 1:
                hidden_indices.add(i + 1)

        print("----- INSTRUCTIONS -----")

        for i, instr in enumerate(instructions):
            if i in hidden_indices:
                continue

            indent = depth[i]
            if i in else_start:
                # else-branch sibling of the enclosing branch node (one level out)
                print("   " * (indent - 1) + "ELSE:")

            prefix = "   " * indent
            line = render_line(instructions, op_names, i, prefix)
            print(line)

            if instr["d"] > 0:
                print(f"Unhandle instruction prop D: {instr['d']} in opcode {op_names[i]}")


for filename in glob.glob("Levels/KingOfNY/*.ai")[:5]:
    print(filename)
    parse_tfbscirpt_file(filename)

print("----- UNIMPLEMENTED OPCODES -----")
for op in sorted(UNIMPLEMENTED_OPCODES):
    print(op)